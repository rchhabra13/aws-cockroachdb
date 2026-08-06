from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()  # so AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY in backend/.env reach boto3's default credential chain

from app.db import close_pool
from app.models import DialogueRequest
from app.routers import auditor, dialogue, inspector, npcs, world
from app.routers.dialogue import dialogue as run_dialogue

app = FastAPI(title="OmniNPC")

# The demo UI is served from a different port, so the browser treats it as cross origin.
# Open here because this is a local demo; narrow it before exposing the API publicly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dialogue.router)
app.include_router(inspector.router)
app.include_router(auditor.router)
app.include_router(npcs.router)
app.include_router(world.router)


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


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
