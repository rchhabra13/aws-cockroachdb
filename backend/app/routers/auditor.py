from uuid import UUID

from fastapi import APIRouter

from app.db import get_pool

router = APIRouter(prefix="/auditor", tags=["auditor"])


@router.get("/incidents/{player_id}")
async def why_stopped(player_id: UUID) -> dict:
    """Read-only MCP-style auditor: reconstructs why an NPC acted, from incidents +
    shared_branch_events + the authorizing conversation, in one place — e.g.
    "Why did the security guard stop this player?"
    """
    pool = await get_pool()
    incidents = await pool.fetch(
        """
        SELECT i.id, i.type, i.description, i.severity, i.visibility, i.created_at,
               n.name AS npc_name, n.role AS npc_role
        FROM incidents i
        LEFT JOIN npcs n ON n.id = i.npc_id
        WHERE i.player_id = $1
        ORDER BY i.created_at
        """,
        player_id,
    )
    shared_events = await pool.fetch(
        """
        SELECT sbe.id, sbe.summary, sbe.visible_to_roles, sbe.created_at
        FROM shared_branch_events sbe
        JOIN incidents i ON i.id = sbe.incident_id
        WHERE i.player_id = $1
        ORDER BY sbe.created_at
        """,
        player_id,
    )
    return {
        "player_id": str(player_id),
        "incidents": [dict(r) for r in incidents],
        "shared_branch_events": [dict(r) for r in shared_events],
    }
