import asyncio
from uuid import UUID

from app.embeddings import embed_text
from app.db import get_pool
from app.memory.vector import to_vector_literal
from app.models import MemoryHit

TOP_K = 8

# Below this, a private memory is noise rather than recall. Chosen from measured scores
# with all-MiniLM-L6-v2: a genuinely related question scores 0.40 to 0.65 against the
# conversation it refers to, while an unrelated one scores below 0.10. Re-measure if the
# embedding model changes, since these numbers do not transfer between models.
PRIVATE_SIMILARITY_FLOOR = 0.25


async def recall(npc_id: UUID, player_id: UUID, query: str) -> list[MemoryHit]:
    """Semantic recall scoped to what this NPC is allowed to know.

    Two separate queries rather than one. Private memories are this character's own and
    are filtered by relevance. Shared branch events are those whose visible_to_roles
    includes this character's role, and they are deliberately not filtered or rank
    limited against private chatter.

    The asymmetry is intentional. A manager issued authorization measures only about 0.29
    against "I need to check the vault", which is close enough to ordinary small talk that
    any floor strict enough to remove noise would also discard the authorization, and any
    floor loose enough to keep it would keep everything. An entitled character should
    always be told about a standing branch event, so entitlement rather than similarity
    decides whether it appears.

    Private memories belonging to another character are never returned by either query.
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
          AND 1 - (m.embedding <=> $1::VECTOR) >= $5
        ORDER BY m.embedding <=> $1::VECTOR
        LIMIT $4
        """,
        embedding,
        npc_id,
        player_id,
        TOP_K,
        PRIVATE_SIMILARITY_FLOOR,
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
          AND sbe.visible_to_roles ? n.role
        ORDER BY m.embedding <=> $1::VECTOR
        LIMIT $4
        """,
        embedding,
        npc_id,
        player_id,
        TOP_K,
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
