# Installing OmniNPC

Three pieces: a CockroachDB cluster, a FastAPI backend, and a Phaser game client.

## 1. Prerequisites

- Python 3.11+
- Node 18+
- A CockroachDB Cloud cluster (or any CockroachDB-compatible instance)
- AWS account with Bedrock access (Nova Pro + Titan Embeddings V2, `us-east-1`)
- Optional: a Gemini API key, used only as the dialogue fallback

## 2. Provision the database

```bash
brew install cockroachdb/tap/ccloud libpq
ccloud auth login
export CRDB_SQL_PASSWORD='your-sql-password'
./scripts/bootstrap.sh
```

This creates the `omninpc` database on the cluster, applies `schema/init.sql` and
`schema/seed.sql`, and prints a `COCKROACHDB_URL` to use in the next step. It's
idempotent — safe to re-run.

## 3. Configure the backend

```bash
cp backend/.env.example backend/.env
```

Fill in `backend/.env`:

| Variable | Value |
|---|---|
| `COCKROACHDB_URL` | printed by `bootstrap.sh` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | credentials with Bedrock access |
| `AWS_REGION` | `us-east-1` |
| `GEMINI_API_KEY` | optional, only needed for fallback |

`LLM_PROVIDER` defaults to `bedrock`, `LLM_FALLBACK_PROVIDER` to `gemini` — leave as is
unless you want to flip primary/fallback.

## 4. Run the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Or via Docker:

```bash
docker compose up --build backend
```

Verify it's up: `curl http://localhost:8000/npcs` should return the 5 seeded characters.

## 5. Run the game

```bash
cd game
npm install
npm run dev
```

Opens at `http://localhost:3001`, talking to the backend
at `http://localhost:8000`. Walk with arrows/WASD, press **E** near a character to talk,
**Esc** to leave a conversation.

## 6. Verify end-to-end

```bash
python scripts/verify.py
```

Runs the isolation test suite against the live backend — private memories don't cross
characters, shared events reach only the roles in their audience.
