"""Authorization, reset, and session lifecycle routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.db import get_pool
from app.memory.publish import publish_shared_event

router = APIRouter(prefix="/world", tags=["world"])

AUTHORIZATION_SUMMARY = "The branch manager authorized a security test by this player."


async def require_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    """Require the configured shared secret; an empty setting disables the check."""
    expected = get_settings().admin_api_key
    if not expected:
        return
    if x_admin_key != expected:
        raise HTTPException(status_code=401, detail="missing or invalid admin key")

# Child-before-parent order avoids foreign-key failures. DELETE avoids the schema-change
# jobs CockroachDB creates for TRUNCATE; fixture tables are intentionally retained.
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
    session_id: UUID | None = None


@router.post("/authorize", dependencies=[Depends(require_admin_key)])
async def authorize(req: AuthorizeRequest) -> dict:
    """Publish the fixed manager authorization to guards and managers."""
    event_id = await publish_shared_event(
        req.branch_id, req.player_id, "authorization", AUTHORIZATION_SUMMARY, req.session_id
    )
    return {"event_id": str(event_id), "summary": AUTHORIZATION_SUMMARY}


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


@router.delete("/events/{event_id}", dependencies=[Depends(require_admin_key)])
async def withdraw_event(event_id: UUID) -> dict:
    """Delete an event and its searchable memory row."""
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


@router.delete("/reset", dependencies=[Depends(require_admin_key)])
async def reset_world() -> dict:
    """Delete interaction data while retaining branch, NPC, and player fixtures."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            for table in RESET_TABLES:
                await conn.execute(f"DELETE FROM {table} WHERE true")
    return {"cleared": RESET_TABLES}


async def _delete_session(conn, session_id: UUID) -> int:
    """Delete one session; find shared events through their session-tagged memories."""
    event_ids = [
        r["id"]
        for r in await conn.fetch(
            """
            SELECT source_id AS id FROM memory_embeddings
            WHERE session_id = $1 AND source_type = 'shared_event'
            """,
            session_id,
        )
    ]
    removed = await conn.fetch(
        "DELETE FROM memory_embeddings WHERE session_id = $1 RETURNING id", session_id
    )
    await conn.execute(
        """
        DELETE FROM messages WHERE conversation_id IN
            (SELECT id FROM conversations WHERE session_id = $1)
        """,
        session_id,
    )
    await conn.execute("DELETE FROM conversations WHERE session_id = $1", session_id)
    await conn.execute("DELETE FROM agent_checkpoints WHERE session_id = $1", session_id)
    if event_ids:
        await conn.execute("DELETE FROM shared_branch_events WHERE id = ANY($1::UUID[])", event_ids)
    return len(removed)


@router.delete("/session/{session_id}")
async def end_session(session_id: UUID) -> dict:
    """Delete one play session and return the number of removed memories."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            removed = await _delete_session(conn, session_id)
    return {"ended": str(session_id), "memories_removed": removed}


@router.post("/session/sweep", dependencies=[Depends(require_admin_key)])
async def sweep_sessions() -> dict:
    """Delete conversation rows that never received a message."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            swept = await conn.fetch(
                """
                DELETE FROM conversations c
                WHERE NOT EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id = c.id)
                RETURNING c.id
                """
            )
    return {"swept_empty_conversations": len(swept)}
