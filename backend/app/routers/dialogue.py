import asyncio

from fastapi import APIRouter

from app.db import get_pool
from app.providers import generate_dialogue
from app.memory.extraction import store_memory
from app.memory.retrieval import recall
from app.models import DialogueRequest, DialogueResponse
from app.prompts import compose_system_prompt

router = APIRouter(prefix="/dialogue", tags=["dialogue"])


@router.post("", response_model=DialogueResponse)
async def dialogue(req: DialogueRequest) -> DialogueResponse:
    pool = await get_pool()
    npc = await pool.fetchrow("SELECT name, role, personality FROM npcs WHERE id = $1", req.npc_id)

    memories = await recall(req.npc_id, req.player_id, req.message, req.session_id)
    system_prompt = compose_system_prompt(
        npc["name"], npc["role"], npc["personality"], memories
    )
    reply = await asyncio.to_thread(generate_dialogue, system_prompt, req.message)

    # One conversation per (character, player, session). DO UPDATE rather than DO NOTHING
    # because only an updated row is returned, and this turn's messages need its id.
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

    player_msg = await pool.fetchrow(
        "INSERT INTO messages (conversation_id, speaker, content) VALUES ($1, 'player', $2) RETURNING id",
        conversation_id,
        req.message,
    )
    await store_memory("message", player_msg["id"], req.message, req.npc_id, req.player_id, req.session_id)

    npc_msg = await pool.fetchrow(
        "INSERT INTO messages (conversation_id, speaker, content) VALUES ($1, 'npc', $2) RETURNING id",
        conversation_id,
        reply,
    )
    await store_memory("message", npc_msg["id"], reply, req.npc_id, req.player_id, req.session_id)

    return DialogueResponse(
        npc_id=req.npc_id,
        reply=reply,
        recalled_memories=memories,
        prompt_sent=system_prompt,
    )
