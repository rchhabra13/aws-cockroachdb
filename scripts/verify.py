"""Verify cross-character and cross-player memory isolation.

Assertions inspect retrieval results rather than generated dialogue. The script clears
interaction data for the seeded demo players before running.

Usage:
    docker compose up -d backend
    ./scripts/bootstrap.sh              # or apply schema/seed.sql
    backend/.venv/bin/python scripts/verify.py

Exits 0 when every check passes and 1 otherwise.
"""

import asyncio
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND / ".env")

import httpx  # noqa: E402

from app.db import close_pool, get_pool  # noqa: E402
from app.memory.publish import publish_shared_event  # noqa: E402
from app.memory.retrieval import recall  # noqa: E402
from app.policies import STRUCTURING_SUMMARY  # noqa: E402

API = "http://localhost:8000"

BRANCH = uuid.UUID("0a5e0000-0000-4000-8000-000000000001")
MARGE = uuid.UUID("0a5e0000-0000-4000-8000-00000000000a")
DANIEL = uuid.UUID("0a5e0000-0000-4000-8000-00000000000b")
RUTH = uuid.UUID("0a5e0000-0000-4000-8000-00000000000c")
GRACE = uuid.UUID("0a5e0000-0000-4000-8000-00000000000f")
PLAYER = uuid.UUID("0a5e0000-0000-4000-8000-0000000000ff")


def _p(suffix: str) -> uuid.UUID:
    return uuid.UUID(f"0a5e0000-0000-4000-8000-0000000001{suffix}")


# Each row includes an errand, recall query, and customer-specific detail.
CUSTOMERS = [
    (_p("01"), "Alice Reyes", "I need a mortgage pre-approval for a house at 410000 dollars.", "mortgage pre-approval", "410000"),
    (_p("02"), "Ben Osei", "I am disputing a card charge of 89 dollars at a hardware store.", "disputing a card charge", "89"),
    (_p("03"), "Carla Nunes", "I want to open a savings account for my daughter Nadia with 500 dollars.", "savings account for my daughter", "Nadia"),
    (_p("04"), "Dmitri Volkov", "I need to send a wire transfer to Lisbon before Friday.", "wire transfer abroad", "Lisbon"),
    (_p("05"), "Emeka Bright", "I lost my debit card at the airport and need a replacement.", "replacing a lost debit card", "airport"),
    (_p("06"), "Fatima Haddad", "I am applying for a small business loan for my bakery on 4th Street.", "small business loan", "bakery"),
    (_p("07"), "Grace Lin", "I want to open a savings account for my daughter Priya with 2000 dollars.", "savings account for my daughter", "Priya"),
    (_p("08"), "Hugo Marchetti", "I need to close a joint account after a divorce.", "closing a joint account", "divorce"),
    (_p("09"), "Ingrid Sol", "I want to refinance my mortgage, currently at 6.8 percent.", "refinancing a mortgage", "6.8"),
    (_p("0a"), "Jamal Farouk", "I need a power of attorney document notarized.", "notarizing a document", "power of attorney"),
]

# Similar errands make player scoping, rather than text similarity, decisive.
COLLISIONS = [(2, 6), (0, 8)]  # Carla/Grace and Alice/Ingrid

failures: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not ok:
        failures.append(f"{label} {detail}".strip())
    return ok


async def say(npc: uuid.UUID, player: uuid.UUID, session: uuid.UUID, message: str) -> str:
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            f"{API}/dialogue",
            json={
                "npc_id": str(npc),
                "player_id": str(player),
                "session_id": str(session),
                "message": message,
            },
        )
        r.raise_for_status()
        return r.json()["reply"]


async def own_memory_ids(npc: uuid.UUID, player: uuid.UUID) -> set:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT source_id FROM memory_embeddings WHERE npc_id = $1 AND player_id = $2",
        npc,
        player,
    )
    return {r["source_id"] for r in rows}


async def reset(players: list[uuid.UUID]) -> None:
    """Clear prior runs, scoped to the seeded demo players only."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            event_ids = [
                r["source_id"]
                for r in await conn.fetch(
                    """
                    SELECT source_id FROM memory_embeddings
                    WHERE player_id = ANY($1::UUID[]) AND source_type = 'shared_event'
                    """,
                    players,
                )
            ]
            await conn.execute(
                "DELETE FROM memory_embeddings WHERE player_id = ANY($1::UUID[])", players
            )
            await conn.execute(
                """
                DELETE FROM messages WHERE conversation_id IN
                    (SELECT id FROM conversations WHERE player_id = ANY($1::UUID[]))
                """,
                players,
            )
            await conn.execute(
                "DELETE FROM conversations WHERE player_id = ANY($1::UUID[])", players
            )
            if event_ids:
                await conn.execute(
                    "DELETE FROM shared_branch_events WHERE id = ANY($1::UUID[])", event_ids
                )
    print(f"  cleared {len(players)} demo players ({len(event_ids)} published events)")


async def probe(npc: uuid.UUID, player: uuid.UUID, session: uuid.UUID, message: str) -> str:
    """Remove probe writes so the authorization remains the only A/B difference."""
    pool = await get_pool()
    before = {
        r["id"]
        for r in await pool.fetch(
            "SELECT id FROM memory_embeddings WHERE npc_id = $1 AND player_id = $2", npc, player
        )
    }
    reply = await say(npc, player, session, message)
    async with pool.acquire() as conn:
        async with conn.transaction():
            new_sources = [
                r["source_id"]
                for r in await conn.fetch(
                    """
                    SELECT source_id FROM memory_embeddings
                    WHERE npc_id = $1 AND player_id = $2 AND NOT (id = ANY($3::UUID[]))
                    """,
                    npc,
                    player,
                    list(before),
                )
            ]
            await conn.execute(
                """
                DELETE FROM memory_embeddings
                WHERE npc_id = $1 AND player_id = $2 AND NOT (id = ANY($3::UUID[]))
                """,
                npc,
                player,
                list(before),
            )
            if new_sources:
                await conn.execute("DELETE FROM messages WHERE id = ANY($1::UUID[])", new_sources)
    return reply


async def suite_a() -> None:
    """Cross-character visibility: the teller, the manager, and the guard."""
    print("\n" + "=" * 78)
    print("SUITE A  one player, three characters")
    session = uuid.uuid4()

    await say(MARGE, PLAYER, session, "Morning. I would like to check my account balance.")
    await say(
        DANIEL,
        PLAYER,
        session,
        "I need to tell you privately, I am running an authorized security test today.",
    )
    marge_own = await own_memory_ids(MARGE, PLAYER)
    daniel_own = await own_memory_ids(DANIEL, PLAYER)
    print(f"  stored {len(marge_own)} memories for Marge, {len(daniel_own)} for Daniel")

    event_id = await publish_shared_event(
        BRANCH, PLAYER, "authorization",
        "The branch manager authorized a security test by this player.",
    )
    print(f"  published authorization {event_id} to roles: guard, manager\n")

    # Positive controls distinguish isolation from a broken retrieval path.
    asked_about_manager = await recall(MARGE, PLAYER, "did the manager say anything about me?")
    asked_about_own = await recall(MARGE, PLAYER, "can you help me with my balance?")
    daniel_hits = await recall(DANIEL, PLAYER, "what did I tell you about the security test?")

    check(bool({h.source_id for h in asked_about_own} & marge_own),
          "A1 control: Marge reaches her own memories")
    check(bool({h.source_id for h in daniel_hits} & daniel_own),
          "A1 control: Daniel reaches his own memories")
    leaked = {h.source_id for h in asked_about_manager} & daniel_own
    shared_seen = [h for h in asked_about_manager if h.source_type == "shared_event"]
    check(not leaked, "A1: teller cannot reach the manager's private conversation",
          f"({len(leaked)} leaked)" if leaked else "")
    check(not shared_seen, "A1: teller cannot reach a guard/manager announcement",
          f"({len(shared_seen)} seen)" if shared_seen else "")

    # The guard receives the decision, not the private conversation behind it.
    ruth_hits = await recall(RUTH, PLAYER, "I need to check the vault")
    got = event_id in {h.source_id for h in ruth_hits}
    ruth_leaked = {h.source_id for h in ruth_hits} & daniel_own
    check(got, "A2: guard reaches the authorization")
    check(not ruth_leaked, "A2: guard cannot reach the conversation behind it",
          f"({len(ruth_leaked)} leaked)" if ruth_leaked else "")
    for h in ruth_hits:
        print(f"        Ruth recalled [{h.source_type}] {h.similarity:.3f} {h.content[:56]}")

    # Ask the same question before and after removing the authorization.
    with_auth = await probe(RUTH, PLAYER, session, "I need to get into the vault.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM memory_embeddings WHERE source_type='shared_event' AND source_id=$1",
                event_id,
            )
            await conn.execute("DELETE FROM shared_branch_events WHERE id = $1", event_id)
    after = await recall(RUTH, PLAYER, "I need to check the vault")
    without_auth = await probe(RUTH, PLAYER, session, "I need to get into the vault.")
    check(event_id not in {h.source_id for h in after},
          "A3: withdrawing the authorization removes it from the guard's reach")
    print(f"        with authorization:    {with_auth[:88].strip()}")
    print(f"        without authorization: {without_auth[:88].strip()}")
    print(f"        replies differ: {with_auth.strip() != without_auth.strip()} (logged, not asserted)")


async def suite_b() -> None:
    """Cross-player isolation: one teller, ten customers."""
    print("\n" + "=" * 78)
    print("SUITE B  one character, ten players")
    session = uuid.uuid4()

    for pid, name, errand, _, _ in CUSTOMERS:
        await say(MARGE, pid, session, errand)
    print(f"  {len(CUSTOMERS)} customers each spoke to Marge once")

    owned = {pid: await own_memory_ids(MARGE, pid) for pid, *_ in CUSTOMERS}

    # Every customer should reach their own memories and nobody else's.
    reached_own = 0
    cross = 0
    for pid, name, _, query, _ in CUSTOMERS:
        hits = {h.source_id for h in await recall(MARGE, pid, query)}
        if hits & owned[pid]:
            reached_own += 1
        for other, *_ in CUSTOMERS:
            if other != pid and hits & owned[other]:
                cross += 1
    check(reached_own == len(CUSTOMERS),
          "B1 control: every customer reaches their own memories",
          f"({reached_own}/{len(CUSTOMERS)})")
    check(cross == 0, "B2: no customer reaches another's memories",
          f"({cross} cross-player hits across {len(CUSTOMERS)**2} cells)")

    # Score confusable rows without player scope to confirm the isolation predicate matters.
    from app.embeddings import embed_text
    from app.memory.retrieval import PRIVATE_SIMILARITY_FLOOR
    from app.memory.vector import to_vector_literal

    pool = await get_pool()
    confusable = 0
    for i, j in COLLISIONS:
        pid_i, name_i, _, query_i, _ = CUSTOMERS[i]
        pid_j, name_j, *_ = CUSTOMERS[j]
        emb = to_vector_literal(await asyncio.to_thread(embed_text, query_i))
        unscoped = await pool.fetchval(
            """
            SELECT max(1 - (embedding <=> $1::VECTOR)) FROM memory_embeddings
            WHERE npc_id = $2 AND player_id = $3
            """,
            emb, MARGE, pid_j,
        )
        scoped = {h.source_id for h in await recall(MARGE, pid_i, query_i)}
        bled = bool(scoped & owned[pid_j])
        above = unscoped is not None and unscoped >= PRIVATE_SIMILARITY_FLOOR
        if above:
            confusable += 1
        print(f"        {name_i} asks \"{query_i}\": {name_j}'s row scores "
              f"{unscoped:.3f} unscoped (floor {PRIVATE_SIMILARITY_FLOOR}), "
              f"{'ABOVE' if above else 'below'}; scoped leak: {bled}")
        check(not bled, f"B3: {name_i} does not reach {name_j}'s memories")
    check(confusable > 0,
          "B3 control: at least one collision clears the floor unscoped",
          f"({confusable}/{len(COLLISIONS)}) — otherwise B2 proves nothing about confusable data")


async def suite_c() -> None:
    """Automatic teller observation becomes a compliance-visible event."""
    print("\n" + "=" * 78)
    print("SUITE C  automatic cross-agent event")
    session = uuid.uuid4()

    await say(MARGE, PLAYER, session, "I would like to deposit $9,500 in cash.")
    await say(MARGE, PLAYER, session, "Make it $9,000 at the other window tomorrow.")
    await say(MARGE, PLAYER, session, "I do not want any reporting paperwork.")

    grace_hits = await recall(GRACE, PLAYER, "Was anything flagged?", session)
    marge_hits = await recall(MARGE, PLAYER, "Was anything flagged?", session)
    grace_events = [
        hit for hit in grace_hits
        if hit.source_type == "shared_event" and hit.content == STRUCTURING_SUMMARY
    ]
    marge_events = [
        hit for hit in marge_hits
        if hit.source_type == "shared_event" and hit.content == STRUCTURING_SUMMARY
    ]

    check(len(grace_events) == 1, "C1: compliance receives one automatic structuring event")
    check(not marge_events, "C2: the teller does not receive the compliance event")


async def main() -> int:
    players = [PLAYER] + [c[0] for c in CUSTOMERS]
    print("=" * 78)
    print("SETUP")
    await reset(players)

    await suite_a()
    await suite_b()
    await suite_c()

    print("\n" + "=" * 78)
    if failures:
        print(f"FAILED  {len(failures)} check(s)")
        for f in failures:
            print(f"  {f}")
    else:
        print("PASSED  memory isolation and automatic event checks")
    print("=" * 78)

    await close_pool()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
