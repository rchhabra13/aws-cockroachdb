from contextlib import asynccontextmanager
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# boto3 reads AWS credentials loaded from backend/.env.
load_dotenv()

from app.db import close_pool
from app.models import DialogueRequest
from app.routers import dialogue, npcs, players, world
from app.routers.dialogue import dialogue as run_dialogue


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_pool()


app = FastAPI(title="OmniNPC", lifespan=lifespan)

# The local game and API use different ports. Restrict this for deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dialogue.router)
app.include_router(npcs.router)
app.include_router(players.router)
app.include_router(world.router)


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


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
