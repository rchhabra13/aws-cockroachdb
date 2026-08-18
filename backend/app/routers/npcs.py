from fastapi import APIRouter

from app.db import get_pool

router = APIRouter(prefix="/npcs", tags=["npcs"])


@router.get("")
async def list_npcs() -> list[dict]:
    """Return the available characters from seed or application data."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT n.id, n.name, n.role, n.branch_id
        FROM npcs n
        JOIN branches b ON b.id = n.branch_id
        ORDER BY n.role
        """
    )
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "role": r["role"],
            "branch_id": str(r["branch_id"]),
        }
        for r in rows
    ]


@router.get("/players")
async def list_players() -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch("SELECT id, name FROM players ORDER BY created_at")
    return [{"id": str(r["id"]), "name": r["name"]} for r in rows]
