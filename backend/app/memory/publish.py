"""Write shared events and their matching searchable memories."""

import json
from uuid import UUID

from app.db import get_pool
from app.memory.extraction import store_memory
from app.roles import roles_for


async def publish_shared_event(
    branch_id: UUID,
    player_id: UUID,
    event_type: str,
    summary: str,
    session_id: UUID | None = None,
    event_key: str | None = None,
) -> UUID:
    """Publish an event using the server-owned audience for its event type."""
    visible_to_roles = roles_for(event_type)
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO shared_branch_events (branch_id, summary, visible_to_roles, event_key)
        VALUES ($1, $2, $3::JSONB, $4)
        ON CONFLICT (event_key) DO NOTHING
        RETURNING id
        """,
        branch_id,
        summary,
        json.dumps(visible_to_roles),
        event_key,
    )
    if row is None:
        row = await pool.fetchrow(
            "SELECT id FROM shared_branch_events WHERE event_key = $1", event_key
        )
        return row["id"]

    # Shared memories have no NPC owner but still require a player for recall.
    event_id = row["id"]
    await store_memory("shared_event", event_id, summary, None, player_id, session_id)
    return event_id
