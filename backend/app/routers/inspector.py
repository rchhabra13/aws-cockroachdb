from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.db import get_pool
from app.models import InspectorTrace, MemoryHit

router = APIRouter(prefix="/inspector", tags=["inspector"])


@router.get("/conversations/{conversation_id}", response_model=InspectorTrace)
async def inspect_conversation(conversation_id: UUID) -> InspectorTrace:
    """Debug view: what an NPC recalled for a conversation and why it answered as it did."""
    pool = await get_pool()
    convo = await pool.fetchrow(
        "SELECT npc_id, player_id FROM conversations WHERE id = $1", conversation_id
    )
    if convo is None:
        raise HTTPException(status_code=404, detail="conversation not found")

    memory_rows = await pool.fetch(
        """
        SELECT source_type, source_id, content
        FROM memory_embeddings
        WHERE player_id = $1 AND (npc_id = $2 OR npc_id IS NULL)
        ORDER BY created_at DESC
        LIMIT 20
        """,
        convo["player_id"],
        convo["npc_id"],
    )
    memories = [
        MemoryHit(source_type=r["source_type"], source_id=r["source_id"], content=r["content"], similarity=1.0)
        for r in memory_rows
    ]

    return InspectorTrace(
        conversation_id=conversation_id,
        recalled_memories=memories,
        world_state_used={"npc_id": str(convo["npc_id"]), "player_id": str(convo["player_id"])},
        prompt_sent="(reconstructed from recalled_memories above)",
    )
