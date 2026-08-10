import asyncio
from uuid import UUID

from app.embeddings import embed_text
from app.db import get_pool
from app.memory.vector import to_vector_literal
from app.models import MemoryHit

TOP_K = 8

# Below this, a private memory is noise rather than recall.
#
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
# 0.25 sits in the gap between 0.193 and 0.319. Titan compresses the range compared with
# all-MiniLM-L6-v2 (which scored the same related queries 0.399 and 0.476) but separates
# signal from noise more cleanly, so the same floor holds with a wider margin.
#
# The queries clustered at 0.04 to 0.19 are references back to the conversation rather
# than statements of its topic. No floor recovers them, because there is no topic in them
# to embed; they need short-term conversation memory instead. See docs/SCENARIO.md.
#
# Re-measure if the embedding model changes. These numbers do not transfer.
PRIVATE_SIMILARITY_FLOOR = 0.25


async def recall(
    npc_id: UUID, player_id: UUID, query: str, session_id: UUID | None = None
) -> list[MemoryHit]:
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

    session_id, when given, scopes recall to a single play session: two sessions of the
    same player never see each other's memories. When None the filter is skipped, so
    server-side callers that are not session-bound (verify.py) read across all sessions.
    The predicate is written `($6::UUID IS NULL OR m.session_id = $6)` so one query serves
    both modes without string-building.
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
