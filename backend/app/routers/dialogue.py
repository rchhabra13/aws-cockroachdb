import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.db import get_pool
from app.memory.extraction import store_memory
from app.memory.publish import publish_shared_event
from app.memory.retrieval import recall
from app.models import DialogueRequest, DialogueResponse
from app.policies import STRUCTURING_SUMMARY, detect_structuring
from app.prompts import compose_system_prompt
from app.providers import generate_dialogue

router = APIRouter(prefix="/dialogue", tags=["dialogue"])

# Three prior exchanges provide bounded short-term context alongside semantic recall.
SHORT_TERM_TURNS = 6
POLICY_HISTORY_MESSAGES = 20


@router.post("", response_model=DialogueResponse)
async def dialogue(req: DialogueRequest) -> DialogueResponse:
    pool = await get_pool()
    npc = await pool.fetchrow(
        "SELECT name, role, personality, branch_id FROM npcs WHERE id = $1", req.npc_id
    )

    memories = await recall(req.npc_id, req.player_id, req.message, req.session_id)
    system_prompt = compose_system_prompt(
        npc["name"], npc["role"], npc["personality"], memories
    )

    # History uses the same NPC, player, and session boundary as semantic recall.
    recent = await pool.fetch(
        """
        SELECT m.speaker, m.content
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.id
        WHERE c.npc_id = $1 AND c.player_id = $2 AND c.session_id = $3
        ORDER BY m.created_at DESC, m.id DESC
        LIMIT $4
        """,
        req.npc_id,
        req.player_id,
        req.session_id,
        POLICY_HISTORY_MESSAGES,
    )
    history = list(reversed(recent[:SHORT_TERM_TURNS]))

    reply = await asyncio.to_thread(generate_dialogue, system_prompt, req.message, history)

    # DO UPDATE makes the existing conversation id available through RETURNING.
    conversation = await pool.fetchrow(
        """
        INSERT INTO conversations (npc_id, player_id, session_id)
        VALUES ($1, $2, $3)
        ON CONFLICT (npc_id, player_id, session_id)
        DO UPDATE SET session_id = excluded.session_id
        RETURNING id
        """,
        req.npc_id,
        req.player_id,
        req.session_id,
    )
    conversation_id = conversation["id"]

    # One statement prevents concurrent turns from interleaving their speaker order. Explicit
    # timestamps break the tie created by CockroachDB's statement-level now().
    now = datetime.now(timezone.utc)
    rows = await pool.fetch(
        """
        INSERT INTO messages (conversation_id, speaker, content, created_at)
        VALUES ($1, 'player', $2, $4), ($1, 'npc', $3, $5)
        RETURNING id, speaker
        """,
        conversation_id,
        req.message,
        reply,
        now,
        now + timedelta(microseconds=1),
    )
    msg_id = {r["speaker"]: r["id"] for r in rows}

    await store_memory("message", msg_id["player"], req.message, req.npc_id, req.player_id, req.session_id)
    await store_memory("message", msg_id["npc"], reply, req.npc_id, req.player_id, req.session_id)

    player_history = [
        turn["content"] for turn in reversed(recent) if turn["speaker"] == "player"
    ]
    player_history.append(req.message)
    if npc["role"] == "teller" and detect_structuring(player_history):
        await publish_shared_event(
            npc["branch_id"],
            req.player_id,
            "structuring",
            STRUCTURING_SUMMARY,
            req.session_id,
            event_key=(
                f"structuring:{npc['branch_id']}:{req.player_id}:{req.session_id}"
            ),
        )

    return DialogueResponse(
        npc_id=req.npc_id,
        reply=reply,
        recalled_memories=memories,
        prompt_sent=system_prompt,
    )
