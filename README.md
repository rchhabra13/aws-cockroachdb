# OmniNPC

OmniNPC is a memory backend for AI characters. Each character stores its own memories of
a player in CockroachDB and retrieves them by meaning, through a query that decides which
memories that character is allowed to see.

The demo scenario is a bank branch where a private conversation with the manager stays
private, while a security alert reaches the guard. Parts of that scenario are built and
parts are not; see [Current status](#current-status).

![CockroachDB](https://img.shields.io/badge/CockroachDB-Vector%20Index-6933FF)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![License](https://img.shields.io/badge/License-MIT-green)

Built for the [CockroachDB x AWS Hackathon: Build with Agentic Memory](https://devpost.com), deadline 18 August 2026.

## Contents

- [What works today](#what-works-today)
- [What is being built](#what-is-being-built)
- [How it works](#how-it-works)
- [Getting started](#getting-started)
- [Using OmniNPC](#using-omninpc)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [Current status](#current-status)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [License](#license)

## What works today

- Every character has its own memory of a player, stored in CockroachDB and durable
  across restarts.
- Recall is semantic rather than keyword based. Asking about "that secure storage room"
  retrieves an earlier conversation about the vault, with no shared vocabulary between
  the two.
- Each dialogue turn returns the memories that informed it, so you can see what the
  character was given before it answered.

## What is being built

These are designed and specified but not implemented. Each links to the section of the
scenario that defines it.

- Publishing security events to roles rather than individuals, so a guard learns about
  an incident without gaining access to the conversation behind it.
- Creating incidents from world actions such as approaching the vault.
- Checkpointing so an in flight conversation survives a pod restart.
- An auditor that reconstructs from stored records why a character acted as it did.

## How it works

Each dialogue turn runs the same four steps. The API embeds the player's message,
searches CockroachDB's distributed vector index for memories that NPC is permitted to
see, composes a prompt from those memories plus the NPC's personality, and sends it to
the language model. The reply and the player's message are both written back as new
memories.

Access control lives in the retrieval query rather than in the prompt. Memories are
stored one of two ways. A private memory carries the owning character's id and is
returned only for that character. A shared memory carries no owner and is instead linked
to a branch event tagged with the roles allowed to see it, so any character holding a
listed role retrieves it. Because a character can only be given what the query returns,
a private memory cannot reach another character's response.

The intended payoff is that telling the branch manager about an authorized security test
writes two records: the transcript, private to the manager, and the authorization itself,
shared with the guard and manager roles. The guard then acts on the authorization while
the teller, whose role is on neither list, knows nothing about it.

The private half of that query runs today. The shared half is written but has no data to
return, because nothing yet publishes branch events. The full scenario, with the
assertion and implementation status for each step, is specified in
[docs/SCENARIO.md](docs/SCENARIO.md).

## Getting started

These steps take you from a fresh checkout to a working local API at
`http://localhost:8000`.

### Before you begin

You will need:

- Docker with Compose.
- A CockroachDB Cloud cluster. The free tier is enough.
- A Google Gemini API key. Gemini is the development model provider; see
  [Current status](#current-status) for the Bedrock path.
- `psql` for applying the schema.

### 1. Clone the project

```bash
git clone https://github.com/rchhabra13/aws-cockroachdb.git
cd aws-cockroachdb
```

### 2. Download the cluster certificate

CockroachDB Cloud requires TLS. Take the cluster id from your CockroachDB Cloud console
and download its CA certificate once:

```bash
curl --create-dirs -o $HOME/.postgresql/root.crt \
  'https://cockroachlabs.cloud/clusters/<cluster-id>/cert'
```

Compose mounts this file into the backend container, so it must exist before you start
the stack.

### 3. Fill in the configuration

```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and set two values. `COCKROACHDB_URL` is the connection string from
the CockroachDB Cloud console, which looks like this:

```
postgresql://<user>:<password>@<host>:26257/defaultdb?sslmode=verify-full
```

`GEMINI_API_KEY` is your Gemini key. Leave the Bedrock values alone for now. This file is
excluded from Git; do not commit it.

### 4. Apply the schema

```bash
export $(grep COCKROACHDB_URL backend/.env | xargs)
psql "$COCKROACHDB_URL" -f schema/init.sql
```

This creates eleven tables and the distributed vector index. Confirm it worked:

```bash
psql "$COCKROACHDB_URL" -c "\dt"
```

### 5. Start the backend

```bash
docker compose up --build backend
```

The first build takes a few minutes because the image downloads the local embedding
model. Once it is running, open `http://localhost:8000/docs` for the interactive API
reference.

### 6. Seed a branch and an NPC

```bash
psql "$COCKROACHDB_URL" <<'SQL'
WITH b AS (
  INSERT INTO branches (name) VALUES ('Downtown Branch') RETURNING id
), n AS (
  INSERT INTO npcs (branch_id, name, role, personality, permissions)
  SELECT id, 'Marge', 'teller',
         '{"tone":"friendly","goal":"process transactions, flag suspicious behavior"}',
         '{"can_publish":[]}'
  FROM b RETURNING id
), p AS (
  INSERT INTO players (name) VALUES ('TestPlayer') RETURNING id
)
SELECT 'npc_id=' || n.id, 'player_id=' || p.id FROM n, p;
SQL
```

Keep the two identifiers it prints.

### 7. Talk to the NPC

```bash
curl -X POST http://localhost:8000/dialogue \
  -H "Content-Type: application/json" \
  -d '{
    "npc_id": "<npc_id>",
    "player_id": "<player_id>",
    "session_id": "11111111-1111-1111-1111-111111111111",
    "message": "Hi, can you tell me about the vault?"
  }'
```

Then ask again using different words, reusing the same identifiers:

```bash
curl -X POST http://localhost:8000/dialogue \
  -H "Content-Type: application/json" \
  -d '{
    "npc_id": "<npc_id>",
    "player_id": "<player_id>",
    "session_id": "11111111-1111-1111-1111-111111111111",
    "message": "So earlier I was asking about that secure storage room, remember?"
  }'
```

The response includes a `recalled_memories` array containing the first exchange with a
similarity score, even though the two messages share no vocabulary. That array is the
memory system working.

## Using OmniNPC

`POST /dialogue` is the main entry point. It takes an NPC, a player, a session, and a
message, and returns the reply along with the memories that informed it.

```json
{
  "npc_id": "bc73e5e0-ba22-47bc-b66b-1431b0f4037b",
  "reply": "Oh, yes, the vault! The one I mentioned...",
  "recalled_memories": [
    {
      "source_type": "message",
      "source_id": "663d5bce-860e-4cd2-9e34-7bd52c0bea03",
      "content": "Hi, can you tell me about the vault?",
      "similarity": 0.515
    }
  ]
}
```

Reusing a `session_id` continues a conversation. Changing the `npc_id` while keeping the
`player_id` starts a separate memory for a different character, which is how the
visibility rules are exercised.

`GET /inspector/conversations/{id}` shows what a character recalled. `GET
/auditor/incidents/{player_id}` reconstructs the incidents and shared events behind a
character's behaviour. Both are described under [Current status](#current-status).

## Configuration

All settings live in `backend/.env`.

| Variable | Default | What it controls |
|---|---|---|
| `COCKROACHDB_URL` | none | Cluster connection string. Required. |
| `GEMINI_API_KEY` | none | Gemini API key. Required for dialogue. |
| `GEMINI_MODEL_ID` | `gemini-2.5-flash` | Dialogue model. |
| `AWS_REGION` | `us-east-1` | Region for the Bedrock provider. |
| `BEDROCK_DIALOGUE_MODEL_ID` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Bedrock dialogue model. Must be an inference profile id. |
| `BEDROCK_EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Bedrock embedding model. |

Embeddings currently run locally with `all-MiniLM-L6-v2` at 384 dimensions, which is why
`memory_embeddings.embedding` is declared `VECTOR(384)`. Titan Embed v2 returns 1024
dimensions, so moving to Bedrock requires altering that column and re-embedding stored
rows. It is a migration, not a configuration change.

## Project structure

| Path | Purpose |
|---|---|
| `backend/app/routers/` | HTTP endpoints for dialogue, inspection, and auditing. |
| `backend/app/memory/` | Visibility scoped retrieval and memory writes. |
| `backend/app/providers/` | Amazon Bedrock dialogue and embeddings, not yet wired up. |
| `backend/app/gemini.py` | Dialogue generation, current provider. |
| `backend/app/embeddings.py` | Local embeddings, current provider. |
| `schema/init.sql` | Tables and the distributed vector index. |
| `docs/SCENARIO.md` | Full bank scenario, one section per step, with status. |
| `docs/MINI_SCENARIO.md` | Minimal test isolating the visibility rules. |
| `frontend/` | Next.js interface. Scaffold only. |
| `iam/` | Least privilege IAM policy for Bedrock. |

## Current status

Under active development. This table is kept accurate rather than aspirational.

| Capability | Status |
|---|---|
| Dialogue loop and message persistence | Working |
| Semantic recall over the vector index | Working |
| Role based visibility rules | Query written, needs testing across multiple NPCs |
| Incident and shared event creation | Not built |
| Checkpointing and restart recovery | Not built |
| Memory inspector | Returns recent memories rather than a per turn trace |
| Auditor endpoint | Written, no data to return until incidents exist |
| Frontend | Scaffold only |
| Amazon EKS deployment | Not built |

Gemini and local embeddings are the development path, chosen because Bedrock access on
the project's AWS account is blocked by an AWS Marketplace payment restriction. The
Bedrock provider in `backend/app/providers/bedrock.py` is written against verified model
identifiers and is the intended production path alongside EKS.

## Troubleshooting

**`root certificate file "/root/.postgresql/root.crt" does not exist`**
The CA certificate from step 2 is missing on the host. Compose mounts it from
`~/.postgresql/root.crt`, so download it before starting the stack.

**`expected 384 dimensions, not N`**
The embedding model and the `VECTOR` column disagree. Either the provider changed or the
schema predates it. Recreate `memory_embeddings` with the correct dimension and
re-embed.

**`address already in use` on port 8000**
An older backend is still running. Check with `docker compose ps` and
`ps aux | grep uvicorn`, and stop it before restarting.

**A request to `/dialogue` hangs**
Usually an empty `GEMINI_API_KEY`. The client retries rather than failing fast. Confirm
the key is set in `backend/.env` and that the container was recreated after editing it.

**`AccessDeniedException ... INVALID_PAYMENT_INSTRUMENT`**
Bedrock only. Anthropic models are billed through AWS Marketplace, which requires a
verified payment method on the account regardless of credit balance.

Container logs are usually the fastest next step:

```bash
docker compose logs backend --tail=50
```

## Security

`backend/.env` holds database credentials and API keys and is excluded from Git. If a
key is ever committed, rotate it rather than relying on removing it from history.

The IAM policy in `iam/bedrock-invoke-policy.json` is scoped to model invocation instead
of account wide Bedrock access. Use it rather than attaching a broader policy.

## License

MIT. See [LICENSE](LICENSE).

## Team

Rishi Chhabra and Aryan Kandari.
