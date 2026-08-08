"""World actions: things the player does, rather than says.

Also exposes the authorization lifecycle the demo needs. Withdrawal deletes the event and
its memory row, because shared_branch_events has no revoked_at column yet. That is fine
for a demo control but is not how a real system should retire an event, since it destroys
the audit trail the auditor is supposed to read.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import get_pool
from app.memory.publish import publish_shared_event

router = APIRouter(prefix="/world", tags=["world"])

AUTHORIZATION_SUMMARY = "The branch manager authorized a security test by this player."

# Interaction/memory tables cleared by /world/reset, in child-before-parent order (DELETE
# has no CASCADE keyword, unlike TRUNCATE). branches, npcs, players are fixtures and stay,
# so the demo world remains playable immediately after a reset.
#
# Deliberately DELETE FROM rather than TRUNCATE: CockroachDB implements TRUNCATE as a
# schema change (drop + recreate the table), which spawns a background "SCHEMA CHANGE GC"
# job per table. Clicking the reset button a few times in a row during testing queued up
# enough of these that a later TRUNCATE failed with "cannot perform TRUNCATE on ... which
# has indexes being dropped" — a live schema change colliding with a new one. DELETE FROM
# is a plain MVCC write, no schema change, no job, safe to call repeatedly.
RESET_TABLES = [
    "messages",
    "memory_embeddings",
    "agent_checkpoints",
    "relationships",
    "promises",
    "shared_branch_events",
    "conversations",
    "incidents",
]


class AuthorizeRequest(BaseModel):
    branch_id: UUID
    player_id: UUID
    summary: str = AUTHORIZATION_SUMMARY


@router.post("/authorize")
async def authorize(req: AuthorizeRequest) -> dict:
    """Publish a manager authorization, visible to guards and managers."""
    event_id = await publish_shared_event(
        req.branch_id, req.player_id, "authorization", req.summary
    )
    return {"event_id": str(event_id), "summary": req.summary}


@router.get("/events/{player_id}")
async def list_events(player_id: UUID) -> list[dict]:
    """Branch events currently in effect for this player."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT sbe.id, sbe.summary, sbe.visible_to_roles, sbe.created_at
        FROM shared_branch_events sbe
        JOIN memory_embeddings m
          ON m.source_type = 'shared_event' AND m.source_id = sbe.id
        WHERE m.player_id = $1
        ORDER BY sbe.created_at
        """,
        player_id,
    )
    return [
        {
            "id": str(r["id"]),
            "summary": r["summary"],
            "visible_to_roles": r["visible_to_roles"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


@router.delete("/events/{event_id}")
async def withdraw_event(event_id: UUID) -> dict:
    """Withdraw an event so its effect on behaviour can be demonstrated by its absence."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                DELETE FROM memory_embeddings
                WHERE source_type = 'shared_event' AND source_id = $1
                """,
                event_id,
            )
            deleted = await conn.execute(
                "DELETE FROM shared_branch_events WHERE id = $1", event_id
            )
    if deleted.split()[-1] == "0":
        raise HTTPException(status_code=404, detail="event not found")
    return {"withdrawn": str(event_id)}


@router.delete("/reset")
async def reset_world() -> dict:
    """Wipe every character's memory and every branch event. Fixtures (branches, npcs,
    players) are kept so the demo stays playable with a clean slate."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            for table in RESET_TABLES:
                await conn.execute(f"DELETE FROM {table} WHERE true")
    return {"cleared": RESET_TABLES}
