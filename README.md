# OmniNPC

OmniNPC is a bank-branch game where AI characters recall private conversations and role-scoped events from CockroachDB.

## Features

- Semantic recall scoped by NPC, player, and browser session
- Shared branch events restricted by server-defined role audiences
- Browser-specific player identity stored across visits
- Optional session retention across reloads and browser restarts
- Automatic teller-to-compliance structuring events based on conversation history
- Six-message conversation history for short-term context
- Amazon Bedrock dialogue and embeddings, with an optional Gemini dialogue fallback
- Phaser game with seven seeded characters and six scripted scenarios
- Memory inspector showing recalled records and the generated system prompt
- HTTP and WebSocket dialogue routes
- Verification script for cross-character and cross-player memory isolation

## Tech Stack

- **Client:** JavaScript, Phaser 3, Webpack 5
- **API:** Python, FastAPI, Pydantic, asyncpg
- **Database:** CockroachDB with `VECTOR(1024)` and a vector index
- **Models:** Amazon Nova Pro, Amazon Titan Text Embeddings V2, optional Gemini fallback
- **Local runtime:** Docker Compose or Python 3.12 from the backend Dockerfile

## Getting Started

Prerequisites:

- A CockroachDB cluster
- The CockroachDB Cloud CLI (`ccloud`) and PostgreSQL client (`psql`)
- AWS credentials with access to the configured Bedrock dialogue and embedding models
- Node.js and npm for the game client; no Node.js version is pinned in this repository

Provision and seed the database:

```bash
export CLUSTER='<cockroachdb-cluster-name>'
export SQL_USER='<cockroachdb-sql-user>'
export CRDB_SQL_PASSWORD='<cockroachdb-sql-password>'
ccloud auth login
./scripts/bootstrap.sh
```

Create the backend environment file and set the connection string printed by the bootstrap script:

```bash
cp backend/.env.example backend/.env
```

Run the backend with Docker:

```bash
docker compose up --build backend
```

Or run it with a local Python environment:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In a second terminal, run the game:

```bash
cd game
npm install
npm run dev
```

Open `http://localhost:3001`. Use the arrow keys or WASD to move, press E near a character to talk, and press Esc to close a conversation. The client registers a browser-specific player ID on first load. Enable **Remember me** to reuse the current session identifier across reloads and browser restarts.

With the backend running, execute the isolation checks from the repository root:

```bash
backend/.venv/bin/python scripts/verify.py
```

The verification script deletes interaction data for the seeded demo players before running. It checks cross-character isolation, cross-player isolation, and automatic teller-to-compliance event publication. See [INSTALL.md](INSTALL.md) for Bedrock access and TLS setup details.

## Environment Variables

Copy [`backend/.env.example`](backend/.env.example) to `backend/.env`.

| Variable | Required | Default | Purpose |
|---|---:|---|---|
| `COCKROACHDB_URL` | No | `postgresql://root@localhost:26257/omninpc?sslmode=disable` | asyncpg connection string |
| `LLM_PROVIDER` | No | `bedrock` | Dialogue provider: `bedrock` or `gemini` |
| `LLM_FALLBACK_ENABLED` | No | `true` | Enables dialogue fallback after a provider error |
| `LLM_FALLBACK_PROVIDER` | No | `gemini` | Fallback dialogue provider |
| `GEMINI_API_KEY` | For Gemini | Empty | Gemini API key |
| `GEMINI_MODEL_ID` | No | `gemini-2.5-flash` | Gemini dialogue model |
| `EMBEDDING_PROVIDER` | No | `bedrock` | Embedding provider: `bedrock` or `local` |
| `AWS_REGION` | No | `us-east-1` | Bedrock region |
| `AWS_ACCESS_KEY_ID` | For explicit AWS credentials | Empty | AWS access key used by boto3 |
| `AWS_SECRET_ACCESS_KEY` | For explicit AWS credentials | Empty | AWS secret key used by boto3 |
| `BEDROCK_DIALOGUE_MODEL_ID` | No | `us.amazon.nova-pro-v1:0` | Bedrock dialogue model |
| `BEDROCK_EMBEDDING_MODEL_ID` | No | `amazon.titan-embed-text-v2:0` | Bedrock embedding model |
| `BEDROCK_EMBEDDING_DIMENSIONS` | No | `1024` | Titan embedding width; must match the schema |
| `ADMIN_API_KEY` | No | Empty | Requires `X-Admin-Key` on operator routes when set |

The local embedding provider uses `all-MiniLM-L6-v2` at 384 dimensions. Its dependency is not present in `backend/requirements.txt`, and the current schema is fixed at 1024 dimensions. It is not a drop-in replacement for the default Bedrock embedding provider.

## Project Structure

```text
backend/              FastAPI application, providers, and memory queries
backend/app/policies.py  Deterministic conversation-to-event policies
backend/tests/        Policy unit tests
game/                 Phaser client and Webpack configuration
schema/               CockroachDB schema and seed data
scripts/bootstrap.sh  Database provisioning and seeding
scripts/verify.py     Live isolation checks
docs/SCENARIO.md      Demo flow and implementation status
CONTRIBUTING.md       Development checks and contribution guidelines
iam/                  AWS IAM policy documents
docker-compose.yml    Local backend container
```

## How it Works

For each dialogue turn, the API embeds the player's message, retrieves private memories for the same NPC, player, and session, and retrieves shared events visible to the NPC's role. It adds the six most recent conversation messages, sends the resulting context to the configured dialogue provider, then stores both sides of the exchange as vector-searchable memories.

Shared-event audiences come from `backend/app/roles.py`. Callers provide an event type, not an arbitrary list of roles.

The structuring policy examines a teller's current-session player messages. When it finds repeated cash deposits below $10,000 together with reporting-avoidance language, it publishes one deduplicated `structuring` event for that player and session. Compliance officers, managers, and guards can retrieve the event; tellers cannot.

The client stores a generated player ID in browser storage and registers it in CockroachDB. By default, each page load creates an ephemeral session and deletes its interaction data on teardown. **Remember me** stores the session identifier and skips teardown, allowing the same memories to be recalled on later visits.

## License

[MIT](LICENSE)
