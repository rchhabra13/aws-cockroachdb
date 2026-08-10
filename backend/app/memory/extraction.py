import asyncio
from uuid import UUID

from app.embeddings import embed_text
from app.db import get_pool
from app.memory.vector import to_vector_literal


async def store_memory(
    source_type: str,
    source_id: UUID,
    content: str,
    npc_id: UUID | None,
    player_id: UUID | None,
    session_id: UUID | None = None,
) -> None:
    """Persist one memorable event as a vector-searchable row.

    npc_id=None marks the memory as branch-shared (see shared_branch_events).
    session_id tags the row to a play session; None leaves it session-agnostic (used by
    fixtures and the verify suite, which read across sessions).
    """
    embedding = to_vector_literal(await asyncio.to_thread(embed_text, content))
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO memory_embeddings (source_type, source_id, npc_id, player_id, session_id, content, embedding)
        VALUES ($1, $2, $3, $4, $5, $6, $7::VECTOR)
        """,
        source_type,
        source_id,
        npc_id,
        player_id,
        session_id,
        content,
        embedding,
    )
