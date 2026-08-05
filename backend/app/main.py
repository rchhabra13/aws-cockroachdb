from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

load_dotenv()  # so AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY in backend/.env reach boto3's default credential chain

from app.db import close_pool
from app.models import DialogueRequest
from app.routers import auditor, dialogue, inspector
from app.routers.dialogue import dialogue as run_dialogue

app = FastAPI(title="OmniNPC")

app.include_router(dialogue.router)
app.include_router(inspector.router)
app.include_router(auditor.router)


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_pool()


@app.websocket("/ws/dialogue")
async def ws_dialogue(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            req = DialogueRequest(
                npc_id=UUID(payload["npc_id"]),
                player_id=UUID(payload["player_id"]),
                session_id=UUID(payload["session_id"]),
                message=payload["message"],
            )
            response = await run_dialogue(req)
            await websocket.send_json(response.model_dump(mode="json"))
    except WebSocketDisconnect:
        pass
