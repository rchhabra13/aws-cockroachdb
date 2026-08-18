import asyncio
from uuid import UUID

from app.embeddings import embed_text
from app.db import get_pool
from app.memory.vector import to_vector_literal
from app.models import MemoryHit

TOP_K = 8

# Measured against Titan Text Embeddings V2 at 1024 dimensions, scoring queries against
# the stored message "Morning. I would like to check my account balance.":
#
#   how much money is in my account?          0.359   related, must be recalled
#   can you help me with my balance?          0.319   related, must be recalled
#   remind me what I came in for              0.193   refers back, carries no topic
#   Sorry, what was I asking you about?       0.076   refers back, carries no topic
#   did the manager say anything about me?    0.054   unrelated
#   what did we just talk about?              0.041   refers back, carries no topic
#   what is the weather like on Jupiter       0.020   nonsense control
#
# The 0.25 floor separates the measured topical queries from indirect references. The
# dialogue history handles indirect references. Re-measure when changing embedding models.
PRIVATE_SIMILARITY_FLOOR = 0.25


async def recall(
    npc_id: UUID, player_id: UUID, query: str, session_id: UUID | None = None
) -> list[MemoryHit]:
    """Return private semantic matches and role-visible shared events.

    Shared events do not use the private similarity floor because role entitlement, not
    phrasing similarity, determines whether an active event belongs in the prompt. A null
    session_id disables session filtering for server-side verification.
    """
    embedding = to_vector_literal(await asyncio.to_thread(embed_text, query))
    pool = await get_pool()

    private = await pool.fetch(
        """
        SELECT m.source_type, m.source_id, m.content,
               1 - (m.embedding <=> $1::VECTOR) AS similarity
        FROM memory_embeddings m
        WHERE m.player_id = $3
          AND m.npc_id = $2
          AND ($6::UUID IS NULL OR m.session_id = $6)
          AND 1 - (m.embedding <=> $1::VECTOR) >= $5
        ORDER BY m.embedding <=> $1::VECTOR
        LIMIT $4
        """,
        embedding,
        npc_id,
        player_id,
        TOP_K,
        PRIVATE_SIMILARITY_FLOOR,
        session_id,
    )

    shared = await pool.fetch(
        """
        SELECT m.source_type, m.source_id, m.content,
               1 - (m.embedding <=> $1::VECTOR) AS similarity
        FROM memory_embeddings m
        JOIN shared_branch_events sbe
          ON m.source_type = 'shared_event' AND m.source_id = sbe.id
        JOIN npcs n ON n.id = $2
        WHERE m.player_id = $3
          AND m.npc_id IS NULL
          AND ($5::UUID IS NULL OR m.session_id = $5)
          AND sbe.visible_to_roles ? n.role
        ORDER BY m.embedding <=> $1::VECTOR
        LIMIT $4
        """,
        embedding,
        npc_id,
        player_id,
        TOP_K,
        session_id,
    )

    hits = [
        MemoryHit(
            source_type=row["source_type"],
            source_id=row["source_id"],
            content=row["content"],
            similarity=row["similarity"],
        )
        for row in list(private) + list(shared)
    ]
    hits.sort(key=lambda h: h.similarity, reverse=True)
    return hits
