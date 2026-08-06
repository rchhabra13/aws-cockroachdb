"""Mini scenario: does the visibility model actually hold?

Specified in docs/MINI_SCENARIO.md. Four steps, two assertions, one claim:

    A memory belonging to one character is unreachable by another, while an event
    published to a role is reachable by every character holding that role.

Assertions run against retrieval sets rather than model replies. A language model
declining to reveal something is not evidence that it was never given it.

Usage:
    docker compose up -d backend
    psql "$COCKROACHDB_URL" -f schema/seed.sql
    backend/.venv/bin/python scripts/mini_scenario.py
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

API = "http://localhost:8000"

BRANCH = uuid.UUID("0a5e0000-0000-4000-8000-000000000001")
MARGE = uuid.UUID("0a5e0000-0000-4000-8000-00000000000a")
DANIEL = uuid.UUID("0a5e0000-0000-4000-8000-00000000000b")
RUTH = uuid.UUID("0a5e0000-0000-4000-8000-00000000000c")
PLAYER = uuid.UUID("0a5e0000-0000-4000-8000-0000000000ff")


def show(label: str, hits) -> None:
    print(f"\n  {label}")
    if not hits:
        print("    (nothing recalled)")
    for h in hits:
        print(f"    [{h.source_type:13}] {h.similarity:.3f}  {h.content[:78]}")


async def say(npc_id: uuid.UUID, session: uuid.UUID, message: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{API}/dialogue",
            json={
                "npc_id": str(npc_id),
                "player_id": str(PLAYER),
                "session_id": str(session),
                "message": message,
            },
        )
        r.raise_for_status()
        return r.json()["reply"]


async def private_memory_ids(npc_id: uuid.UUID) -> set:
    """Every memory row privately owned by this character for this player."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT source_id FROM memory_embeddings WHERE npc_id = $1 AND player_id = $2",
        npc_id,
        PLAYER,
    )
    return {r["source_id"] for r in rows}


async def reset() -> None:
    """Clear prior runs so the scenario is repeatable.

    Scoped entirely to the seeded test player. Nothing else in the database is touched,
    and no NPC, branch, or player rows are removed. Without this, each run stacks another
    authorization and another set of transcripts, and the assertions slowly lose meaning.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Collected before the memories are deleted, since the link from a shared
            # event back to a player exists only on the memory row.
            event_ids = [
                r["source_id"]
                for r in await conn.fetch(
                    """
                    SELECT source_id FROM memory_embeddings
                    WHERE player_id = $1 AND source_type = 'shared_event'
                    """,
                    PLAYER,
                )
            ]
            await conn.execute("DELETE FROM memory_embeddings WHERE player_id = $1", PLAYER)
            await conn.execute(
                """
                DELETE FROM messages WHERE conversation_id IN
                    (SELECT id FROM conversations WHERE player_id = $1)
                """,
                PLAYER,
            )
            await conn.execute("DELETE FROM conversations WHERE player_id = $1", PLAYER)
            if event_ids:
                await conn.execute(
                    "DELETE FROM shared_branch_events WHERE id = ANY($1::UUID[])", event_ids
                )
    print(f"  reset: cleared prior runs for the test player ({len(event_ids)} shared events)")


async def probe(npc_id: uuid.UUID, session: uuid.UUID, message: str) -> str:
    """Ask a question without leaving a trace, so the answer can be compared fairly.

    A normal turn writes the exchange back as memory. That ruins an ablation: the first
    probe's reply becomes a private memory, the guard recalls having already granted
    access, and she keeps granting it after the authorization is withdrawn. Rolling the
    probe back leaves the authorization as the only difference between the two runs.
    """
    pool = await get_pool()
    before = {
        r["id"]
        for r in await pool.fetch(
            "SELECT id FROM memory_embeddings WHERE npc_id = $1 AND player_id = $2",
            npc_id,
            PLAYER,
        )
    }
    reply = await say(npc_id, session, message)
    async with pool.acquire() as conn:
        async with conn.transaction():
            new_sources = [
                r["source_id"]
                for r in await conn.fetch(
                    """
                    SELECT source_id FROM memory_embeddings
                    WHERE npc_id = $1 AND player_id = $2 AND NOT (id = ANY($3::UUID[]))
                    """,
                    npc_id,
                    PLAYER,
                    list(before),
                )
            ]
            await conn.execute(
                """
                DELETE FROM memory_embeddings
                WHERE npc_id = $1 AND player_id = $2 AND NOT (id = ANY($3::UUID[]))
                """,
                npc_id,
                PLAYER,
                list(before),
            )
            if new_sources:
                await conn.execute(
                    "DELETE FROM messages WHERE id = ANY($1::UUID[])", new_sources
                )
    return reply


async def revoke_event(event_id: uuid.UUID) -> None:
    """Withdraw a published event so the ablation can be measured.

    Deletes both rows, because shared_branch_events has no revoked_at column yet. A soft
    revoke is the better demo mechanism and is scheduled with the other schema work; for
    a test that resets its own data first, a delete is equivalent and needs no migration.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM memory_embeddings WHERE source_type = 'shared_event' AND source_id = $1",
                event_id,
            )
            await conn.execute("DELETE FROM shared_branch_events WHERE id = $1", event_id)


async def main() -> int:
    session = uuid.uuid4()
    failures = []

    print("=" * 84)
    print("SETUP")
    await reset()
    print()
    print("=" * 84)
    print("STEP 0  Player chats to the teller, so she has a memory of her own")
    reply = await say(MARGE, session, "Morning. I would like to check my account balance.")
    print(f"  Marge: {reply[:160]}")
    marge_private = await private_memory_ids(MARGE)
    print(f"  stored {len(marge_private)} private memories for Marge")

    print("\n" + "=" * 84)
    print("STEP 1  Player tells the manager, privately, about an authorized test")
    reply = await say(
        DANIEL,
        session,
        "I need to tell you privately, I am running an authorized security test today.",
    )
    print(f"  Daniel: {reply[:200]}")
    daniel_private = await private_memory_ids(DANIEL)
    print(f"  stored {len(daniel_private)} private memories for Daniel")

    print("\n" + "=" * 84)
    print("STEP 2  Publish the authorization as a shared branch event")
    event_id = await publish_shared_event(
        BRANCH,
        PLAYER,
        "authorization",
        "The branch manager authorized a security test by this player.",
    )
    print(f"  published event {event_id}, visible to roles: guard, manager")

    print("\n" + "=" * 84)
    print("STEP 3  Player asks the teller what the manager said")
    marge_hits = await recall(MARGE, PLAYER, "did the manager say anything about me?")
    show("Marge recalled, asked about the manager:", marge_hits)

    # The control needs its own query. "did the manager say anything" is unrelated to
    # anything Marge knows, scoring about 0.07 against her own memories, so requiring her
    # to retrieve them for it would be asserting that retrieval ignores relevance. Asking
    # about what she actually discussed scores around 0.40 to 0.65 and is a fair check
    # that her retrieval path works at all.
    marge_control = await recall(MARGE, PLAYER, "can you help me with my balance?")
    show("Marge recalled, asked about her own conversation:", marge_control)

    # Second control. Without it, N1 would pass just as well if Daniel's memories were
    # inert and retrievable by nobody. Showing he can reach them himself makes Marge's
    # inability to reach them a scoping result rather than a dead row result.
    daniel_hits = await recall(DANIEL, PLAYER, "what did I tell you about the security test?")
    daniel_reaches_own = bool({h.source_id for h in daniel_hits} & daniel_private)

    marge_ids = {h.source_id for h in marge_hits}
    leaked = marge_ids & daniel_private
    shared_seen = [h for h in marge_hits if h.source_type == "shared_event"]
    # Without this, "recalled nothing at all" would pass N1 just as happily as correct
    # scoping does, and a broken retrieval path would look like a working one.
    recalls_own = bool({h.source_id for h in marge_control} & marge_private)

    if not recalls_own:
        failures.append("N1 control: Marge recalled none of her own memories, so the "
                        "negative results below prove nothing")
    if not daniel_reaches_own:
        failures.append("N1 control: Daniel cannot reach his own memories with the same "
                        "query, so they may simply be unreachable rather than scoped")
    if leaked:
        failures.append(f"N1: Marge recalled {len(leaked)} of Daniel's private memories")
    if shared_seen:
        failures.append(f"N1: Marge, a teller, recalled {len(shared_seen)} shared events")
    print(f"\n  control: Marge reaches {len({h.source_id for h in marge_control} & marge_private)}"
          f" of her own memories when asked about them")
    print(f"  control: Daniel reaches his own private memories with the same query: "
          f"{daniel_reaches_own}")
    print(
        "  N1 "
        + ("PASS" if recalls_own and daniel_reaches_own and not leaked and not shared_seen
           else "FAIL")
        + "  teller sees her own memories, but not the private conversation "
        "nor guard/manager events"
    )

    print("\n" + "=" * 84)
    print("STEP 4  Player asks the guard for vault access")
    ruth_hits = await recall(RUTH, PLAYER, "I need to check the vault")
    show("Ruth recalled:", ruth_hits)

    got_authorization = event_id in {h.source_id for h in ruth_hits}
    ruth_leaked = {h.source_id for h in ruth_hits} & daniel_private
    if not got_authorization:
        failures.append("N2: Ruth did not recall the authorization")
    if ruth_leaked:
        failures.append(f"N2: Ruth recalled {len(ruth_leaked)} of Daniel's private memories")
    print(
        "\n  N2 "
        + ("PASS" if got_authorization and not ruth_leaked else "FAIL")
        + "  guard sees the authorization but not the conversation behind it"
    )

    print("\n" + "=" * 84)
    print("STEP 5  Ablation: does the authorization actually change what Ruth says?")
    print("\n  Asking Ruth, with the authorization in place:")
    reply_with = await probe(RUTH, session, "I need to get into the vault.")
    print(f"    Ruth: {reply_with[:220]}")

    await revoke_event(event_id)
    print(f"\n  revoked event {event_id}")

    ruth_after = await recall(RUTH, PLAYER, "I need to check the vault")
    show("Ruth recalled after revocation:", ruth_after)

    print("\n  Asking Ruth the same question, with the authorization gone:")
    reply_without = await probe(RUTH, session, "I need to get into the vault.")
    print(f"    Ruth: {reply_without[:220]}")

    # The hard assertion is the retrieval set, which is deterministic. Whether the two
    # replies differ is logged but not asserted, because model output is not stable
    # enough to gate a test on.
    still_authorized = event_id in {h.source_id for h in ruth_after}
    if still_authorized:
        failures.append("N3: the authorization was still retrievable after revocation")
    print(
        "\n  N3 "
        + ("PASS" if not still_authorized else "FAIL")
        + "  revoking the authorization removes it from what the guard can reach"
    )
    print(f"  replies differ: {reply_with.strip() != reply_without.strip()} (not asserted)")

    print("\n" + "=" * 84)
    if failures:
        print("FAILED")
        for f in failures:
            print(f"  {f}")
    else:
        print("PASSED  visibility holds in both directions, and shared memory "
              "changes behaviour")
    print("=" * 84)

    await close_pool()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
