"""The only place shared branch events are written.

Routing every shared write through here is what keeps them retrievable. recall() joins
shared_branch_events with `m.source_type = 'shared_event' AND m.source_id = sbe.id`, so a
shared memory stored under any other source_type produces a null join and is unreachable
forever. Incident derived events must therefore also point at a shared_branch_events row
rather than at the incident.
"""

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
) -> UUID:
    """Publish a branch event and make it semantically retrievable by entitled roles.

    Visibility is derived from event_type, never taken from the caller. session_id scopes
    the event to one play session so a guard in another session does not recall it; None
    leaves it session-agnostic (verify.py).
    """
    visible_to_roles = roles_for(event_type)
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO shared_branch_events (branch_id, summary, visible_to_roles)
        VALUES ($1, $2, $3::JSONB)
        RETURNING id
        """,
        branch_id,
        summary,
        json.dumps(visible_to_roles),
    )
    event_id = row["id"]

    # npc_id is None so no single character owns it; player_id is required because
    # recall() filters on it, and a shared memory without one is unreachable.
    await store_memory("shared_event", event_id, summary, None, player_id, session_id)
    return event_id
