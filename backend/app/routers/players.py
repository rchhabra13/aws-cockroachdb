from uuid import UUID

from fastapi import APIRouter

from app.db import get_pool
from app.models import PlayerRegistration

router = APIRouter(prefix="/players", tags=["players"])


@router.put("/{player_id}")
async def register_player(player_id: UUID, req: PlayerRegistration) -> dict:
    """Create a browser-owned player identity if it does not exist."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO players (id, name)
        VALUES ($1, $2)
        ON CONFLICT (id) DO UPDATE SET name = players.name
        RETURNING id, name
        """,
        player_id,
        req.name,
    )
    return {"id": str(row["id"]), "name": row["name"]}
