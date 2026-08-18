from uuid import UUID

from pydantic import BaseModel, Field


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


class PlayerRegistration(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class DialogueResponse(BaseModel):
    npc_id: UUID
    reply: str
    recalled_memories: list[MemoryHit]
    # Returned for the client-side memory inspector.
    prompt_sent: str = ""
