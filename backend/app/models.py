from uuid import UUID

from pydantic import BaseModel


class MemoryHit(BaseModel):
    source_type: str
    source_id: UUID
    content: str
    similarity: float


class DialogueRequest(BaseModel):
    npc_id: UUID
    player_id: UUID
    session_id: UUID
    message: str


class DialogueResponse(BaseModel):
    npc_id: UUID
    reply: str
    recalled_memories: list[MemoryHit]
    # The exact prompt this turn was generated from, so the memory inspector renders what
    # the character was actually given rather than a reconstruction of it.
    prompt_sent: str = ""
