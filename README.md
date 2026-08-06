# OmniNPC

Role-aware semantic memory for AI characters.

![CockroachDB](https://img.shields.io/badge/CockroachDB-Vector%20Search-6933FF)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![License](https://img.shields.io/badge/License-MIT-green)

OmniNPC is an experimental backend for AI characters that should remember a player
without automatically sharing every conversation with every other character. It stores
private character memories separately and publishes selected facts as role-scoped
events.

The demonstration takes place in a bank branch. A conversation with the manager remains
private, while an authorization created from that conversation can be made available to
the manager and security guard. The teller cannot retrieve either the private exchange
or a security-only announcement.

## Why OmniNPC

Many character systems either forget earlier interactions or place all history into one
shared context. A shared context makes it easy for a character to reveal information it
should never have received.

OmniNPC applies the visibility rule during database retrieval:

- Private memories are stored with an NPC identifier and can only be recalled by that
  NPC for the same player.
- Shared branch events have no NPC owner. Their audience is derived from an event type
  and matched against the requesting NPC's role.
- Prompts separate personal memories from official branch announcements so the model can
  distinguish conversation history from operational facts.

This design prevents another NPC's private rows from entering the recall context. It
does not attempt to treat model instructions as an access-control boundary.

## Features and roadmap

| Capability | Availability |
|---|---|
| HTTP and WebSocket dialogue | Available |
| Private semantic memory per NPC and player | Available |
| Role-scoped shared events | Available |
| Repeatable visibility verification | Available in `scripts/mini_scenario.py` |
| Automatic event extraction from dialogue | Planned; the demo publishes events explicitly |
| World actions and incident creation | Planned; database tables are defined |
| Conversation checkpoint recovery | Planned; the checkpoint table is defined |
| Memory inspector | Limited; it does not preserve the exact context used for a turn |
| Auditor | Limited; it does not include standalone authorization events |
| Web application | Planned; the repository contains a Next.js scaffold |
| EKS deployment | Planned |

LM Studio is the default dialogue provider. Gemini and Amazon Bedrock dialogue adapters
are also selectable through configuration. Embeddings currently use the local
`all-MiniLM-L6-v2` model in every configuration; the Bedrock embedding implementation is
not connected to the storage and retrieval path.

## Scenario guides

- [Comprehensive bank branch scenario](docs/SCENARIO.md) describes the intended
  end-to-end experience and marks the implementation status of every stage.
- [Mini verification scenario](docs/MINI_SCENARIO.md) documents the smallest repeatable
  test of private and role-scoped memory.

## Architecture

A dialogue request follows this path:

1. Embed the player's message locally.
2. Retrieve relevant private memories for the selected NPC and player.
3. Retrieve shared events visible to the NPC's role.
4. Compose a prompt that labels private memories and official announcements separately.
5. Generate the reply with the configured dialogue provider.
6. Store both sides of the exchange as private semantic memories for that NPC.

CockroachDB stores the application records and 384-dimensional memory vectors. FastAPI
provides the dialogue, inspector, and auditor endpoints.

## Prerequisites

- Python 3.12
- Docker with Docker Compose
- `psql`
- A CockroachDB database with vector indexing enabled
- One configured dialogue provider: LM Studio, Gemini, or Amazon Bedrock

For CockroachDB Cloud, download the cluster CA certificate to the location mounted by
`docker-compose.yml`:

```bash
curl --create-dirs -o "$HOME/.postgresql/root.crt" \
  "https://cockroachlabs.cloud/clusters/<cluster-id>/cert"
```

## Run the API

1. Create the backend configuration:

   ```bash
   cp backend/.env.example backend/.env
   ```

2. Set `COCKROACHDB_URL` and the variables for your selected dialogue provider in
   `backend/.env`.

3. Initialize and seed the database. Set the same database URL in your shell before
   running these commands:

   ```bash
   export COCKROACHDB_URL='postgresql://<user>:<password>@<host>:26257/<database>?sslmode=verify-full'
   psql "$COCKROACHDB_URL" -f schema/init.sql
   psql "$COCKROACHDB_URL" -f schema/seed.sql
   ```

4. Build and start the backend:

   ```bash
   docker compose up --build backend
   ```

The API is available at [http://localhost:8000](http://localhost:8000), and the
interactive OpenAPI documentation is available at
[http://localhost:8000/docs](http://localhost:8000/docs).

## Run the mini verification

The verification script runs on the host and calls the backend on port `8000`. Install
the backend dependencies in a local virtual environment once:

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/python scripts/mini_scenario.py
```

The script resets data associated with the fixed demo player, creates a private manager
conversation and a role-scoped authorization, and checks three invariants:

1. The teller can recall her own conversation but cannot retrieve the manager's private
   conversation or the security announcement.
2. The guard can retrieve the authorization but not the manager's private conversation.
3. Removing the authorization removes it from the guard's recall set.

See [the mini scenario guide](docs/MINI_SCENARIO.md) for the test boundaries and data
cleanup behavior.

## Configuration

All runtime settings are read from `backend/.env`.

| Variable | Default | Description |
|---|---|---|
| `COCKROACHDB_URL` | Local insecure URL | CockroachDB connection string |
| `LLM_PROVIDER` | `lmstudio` | Dialogue provider: `lmstudio`, `gemini`, or `bedrock` |
| `LM_STUDIO_BASE_URL` | `http://host.docker.internal:1234` | LM Studio server URL from the backend container |
| `LM_STUDIO_API_KEY` | Empty | LM Studio API key |
| `LM_STUDIO_MODEL_ID` | `google/gemma-4-12b` | LM Studio model identifier |
| `GEMINI_API_KEY` | Empty | Gemini API key |
| `GEMINI_MODEL_ID` | `gemini-2.5-flash` | Gemini model identifier |
| `AWS_REGION` | `us-east-1` | AWS region used by the Bedrock adapter |
| `BEDROCK_DIALOGUE_MODEL_ID` | Claude inference profile | Bedrock dialogue model identifier |

Changing the embedding model requires updating the database vector dimension and
re-embedding existing memory rows.

## API summary

| Endpoint | Purpose | Availability |
|---|---|---|
| `POST /dialogue` | Recall memories, generate a reply, and store the exchange | Available |
| `WS /ws/dialogue` | WebSocket wrapper around the dialogue flow | Available |
| `GET /inspector/conversations/{id}` | Return a reconstructed memory view | Limited |
| `GET /auditor/incidents/{player_id}` | Return recorded incidents and linked shared events | Limited |

## Repository layout

| Path | Contents |
|---|---|
| `backend/app/memory/` | Memory storage, semantic retrieval, and shared-event publication |
| `backend/app/providers/` | LM Studio and Amazon Bedrock dialogue adapters |
| `backend/app/routers/` | Dialogue, inspector, and auditor API routes |
| `schema/` | CockroachDB schema and deterministic demo data |
| `scripts/mini_scenario.py` | Automated visibility verification |
| `docs/SCENARIO.md` | Comprehensive scenario and implementation status |
| `docs/MINI_SCENARIO.md` | Focused verification scenario |
| `frontend/` | Uncustomized Next.js application scaffold |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `root certificate file ... does not exist` | The CockroachDB Cloud CA certificate is missing from `~/.postgresql/root.crt` |
| `expected 384 dimensions, not N` | The stored vector type and embedding model use different dimensions |
| Dialogue requests time out | The selected model server is unavailable or its credentials are invalid |
| Bedrock returns an access or billing error | The AWS account or selected model is not enabled for invocation |

Backend logs are available with:

```bash
docker compose logs backend --tail=50
```

## Security

`backend/.env` contains database and provider credentials and is excluded from Git. If a
credential is committed, rotate it immediately; removing it from the latest commit does
not remove it from repository history.

The sample policy in `iam/omninpc-policy.json` grants model invocation and speech
synthesis permissions. Review and restrict the resource scope before using it outside a
demo environment.

## License

Licensed under the [MIT License](LICENSE).

Created by Rishi Chhabra and Aryan Kandari.
