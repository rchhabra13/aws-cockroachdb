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

Verify it's up: `curl http://localhost:8000/npcs` should return the 7 seeded characters
(two tellers, a manager, a loan officer, a compliance officer, a wealth advisor, and a guard).

## 5. Run the game

```bash
cd game
npm install
npm run dev
```

Opens at `http://localhost:3001`, talking to the backend
at `http://localhost:8000`. Walk with arrows/WASD, press **E** near a character to talk,
**Esc** to leave a conversation. The buttons along the top run scripted scenarios — each
opens an explainer of what it demonstrates before it plays. **Clear DB** wipes all memory
and events but keeps the branch, staff, and customers.

Each browser session is its own isolated collection: memory is tagged with a per-load
session id, so a reload or a second tab starts every character's memory from empty, and
closing the tab tears that session's rows down.

## 6. Verify end-to-end

```bash
python scripts/verify.py
```

Runs the isolation test suite against the live backend — private memories don't cross
characters, shared events reach only the roles in their audience.

## Troubleshooting

**`IsADirectoryError: [Errno 21] Is a directory` on backend startup.** `docker-compose.yml`
bind-mounts `~/.postgresql/root.crt` (the CockroachDB Cloud CA cert) into the container. If
that path doesn't exist on your host, Docker silently creates an empty *directory* there
instead of failing, so the container sees a directory where a cert file should be. Fix:

```bash
rm -rf ~/.postgresql/root.crt   # remove the phantom directory, if present
mkdir -p ~/.postgresql
curl -o ~/.postgresql/root.crt 'https://cockroachlabs.cloud/clusters/<cluster-id>/cert'
docker compose down && docker compose up --build backend   # re-resolve the mount
```

`root.crt` is just the cluster's public CA certificate — not a secret — so it's fine to
copy it from a teammate instead of downloading your own.

To skip the cert entirely, drop `sslmode=verify-full` to `sslmode=require` in
`COCKROACHDB_URL` — still encrypted, just no server-identity check. Fine for local dev.

**`Connection refused` / `Cannot assign requested address`.** `COCKROACHDB_URL` is still
the `.env.example` placeholder (`postgresql://root@localhost:26257/...`). Replace it with
the real cluster URL from `bootstrap.sh`'s output.
