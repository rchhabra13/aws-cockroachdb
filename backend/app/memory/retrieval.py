import asyncio
from uuid import UUID

from app.embeddings import embed_text
from app.db import get_pool
from app.memory.vector import to_vector_literal
from app.models import MemoryHit

TOP_K = 8


async def recall(npc_id: UUID, player_id: UUID, query: str) -> list[MemoryHit]:
    """Semantic recall scoped to what this NPC is allowed to know.

    Visible rows are: this NPC's own memories of this player, plus branch-shared
    memories (npc_id IS NULL) whose source event's visible_to_roles includes the
    NPC's role. Private memories belonging to a different NPC are never returned.
    """
    embedding = to_vector_literal(await asyncio.to_thread(embed_text, query))
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT m.source_type, m.source_id, m.content,
               1 - (m.embedding <=> $1::VECTOR) AS similarity
        FROM memory_embeddings m
        JOIN npcs n ON n.id = $2
        LEFT JOIN shared_branch_events sbe
               ON m.source_type = 'shared_event' AND m.source_id = sbe.id
        WHERE m.player_id = $3
          AND (
                m.npc_id = $2
                OR (m.npc_id IS NULL AND sbe.visible_to_roles ? n.role)
              )
        ORDER BY m.embedding <=> $1::VECTOR
        LIMIT $4
        """,
        embedding,
        npc_id,
        player_id,
        TOP_K,
    )
    return [
        MemoryHit(
            source_type=row["source_type"],
            source_id=row["source_id"],
            content=row["content"],
            similarity=row["similarity"],
        )
        for row in rows
    ]
