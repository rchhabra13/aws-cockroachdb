import asyncio

from fastapi import APIRouter

from app.db import get_pool
from app.gemini import generate_dialogue
from app.memory.extraction import store_memory
from app.memory.retrieval import recall
from app.models import DialogueRequest, DialogueResponse

router = APIRouter(prefix="/dialogue", tags=["dialogue"])


@router.post("", response_model=DialogueResponse)
async def dialogue(req: DialogueRequest) -> DialogueResponse:
    pool = await get_pool()
    npc = await pool.fetchrow("SELECT name, role, personality FROM npcs WHERE id = $1", req.npc_id)

    memories = await recall(req.npc_id, req.player_id, req.message)
    memory_context = "\n".join(f"- {m.content}" for m in memories) or "No relevant memories."

    system_prompt = (
        f"You are {npc['name']}, the {npc['role']} at this bank branch. "
        f"Personality: {npc['personality']}. "
        f"Relevant memories of this player:\n{memory_context}"
    )
    reply = await asyncio.to_thread(generate_dialogue, system_prompt, req.message)

    conversation = await pool.fetchrow(
        """
        INSERT INTO conversations (npc_id, player_id, session_id)
        VALUES ($1, $2, $3)
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        req.npc_id,
        req.player_id,
        req.session_id,
    )
    conversation_id = conversation["id"] if conversation else req.session_id

    player_msg = await pool.fetchrow(
        "INSERT INTO messages (conversation_id, speaker, content) VALUES ($1, 'player', $2) RETURNING id",
        conversation_id,
        req.message,
    )
    await store_memory("message", player_msg["id"], req.message, req.npc_id, req.player_id)

    npc_msg = await pool.fetchrow(
        "INSERT INTO messages (conversation_id, speaker, content) VALUES ($1, 'npc', $2) RETURNING id",
        conversation_id,
        reply,
    )
    await store_memory("message", npc_msg["id"], reply, req.npc_id, req.player_id)

    return DialogueResponse(npc_id=req.npc_id, reply=reply, recalled_memories=memories)
