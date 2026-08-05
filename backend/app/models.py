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


class InspectorTrace(BaseModel):
    conversation_id: UUID
    recalled_memories: list[MemoryHit]
    world_state_used: dict
    prompt_sent: str
