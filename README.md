# OmniNPC

Memory for AI characters that respects who is allowed to know what.

Each character stores its own memories in CockroachDB and retrieves them by meaning,
through a query that decides what that character may see. A private conversation with the
bank manager stays private; a security clearance reaches the guard.

![CockroachDB](https://img.shields.io/badge/CockroachDB-Vector%20Index-6933FF)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![License](https://img.shields.io/badge/License-MIT-green)

Built for the [CockroachDB x AWS Hackathon](https://devpost.com), deadline 18 August 2026.

## How it works

Memories are stored one of two ways.

**Private.** Owned by one character, returned only to that character, filtered by
relevance.

**Shared.** Owned by nobody, tagged with the roles allowed to see it. Any character with
a listed role retrieves it, regardless of similarity, because an entitled character
should always hear about a standing branch event.

Because a character can only be told what the query returns, a private memory cannot
reach another character's response.

## Status

| | |
|---|---|
| Dialogue loop, semantic recall | Working |
| Role based visibility | Working, verified by the test scenario |
| Shared event publication | Working, called explicitly rather than extracted |
| Incidents, checkpoints, auditor data | Not built |
| Memory inspector | Returns recent memories, not a per turn trace |
| Frontend, EKS deployment | Not built |

Dialogue runs locally through LM Studio. Embeddings are local `all-MiniLM-L6-v2` at 384
dimensions. Bedrock is the intended production path but is blocked on this account by an
AWS Marketplace payment restriction; the provider is written and unwired.

## Quick start

Needs Docker, a CockroachDB Cloud cluster, and a local model server.

```bash
curl --create-dirs -o $HOME/.postgresql/root.crt \
  'https://cockroachlabs.cloud/clusters/<cluster-id>/cert'

cp backend/.env.example backend/.env      # set COCKROACHDB_URL and LM_STUDIO_API_KEY
psql "$COCKROACHDB_URL" -f schema/init.sql
psql "$COCKROACHDB_URL" -f schema/seed.sql

docker compose up --build backend
```

API on `http://localhost:8000`, docs at `/docs`.

Verify the memory model end to end:

```bash
backend/.venv/bin/python scripts/mini_scenario.py
```

## Configuration

`backend/.env`.

| Variable | Default | Purpose |
|---|---|---|
| `COCKROACHDB_URL` | none | Cluster connection string. Required. |
| `LLM_PROVIDER` | `lmstudio` | `lmstudio`, `gemini`, or `bedrock`. |
| `LM_STUDIO_BASE_URL` | `http://host.docker.internal:1234` | Use `localhost` outside Docker. |
| `LM_STUDIO_API_KEY` | none | Token from LM Studio's Developer tab. |
| `LM_STUDIO_MODEL_ID` | `google/gemma-4-12b` | Local dialogue model. |
| `GEMINI_API_KEY` | none | Only if `LLM_PROVIDER=gemini`. Free tier is 20 requests per day. |

## Structure

| Path | Purpose |
|---|---|
| `backend/app/memory/` | Retrieval, writes, shared event publication |
| `backend/app/prompts.py` | Prompt composition, separates private memory from branch bulletins |
| `backend/app/providers/` | LM Studio and Bedrock dialogue providers |
| `backend/app/routers/` | Dialogue, inspector, auditor endpoints |
| `schema/` | Tables, vector index, demo seed data |
| `scripts/mini_scenario.py` | End to end test of the visibility rules |
| `docs/` | Scenario specifications |

## Documentation

- [`docs/SCENARIO.md`](docs/SCENARIO.md), the full eight step bank scenario.
- [`docs/MINI_SCENARIO.md`](docs/MINI_SCENARIO.md), the test that proves the visibility
  rules.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `root certificate file ... does not exist` | CA cert not downloaded; compose mounts it from `~/.postgresql/root.crt` |
| `expected 384 dimensions, not N` | Embedding model and `VECTOR` column disagree |
| Requests hang | Empty or wrong model provider key |
| `INVALID_PAYMENT_INSTRUMENT` | Bedrock only; Anthropic models bill through AWS Marketplace |

```bash
docker compose logs backend --tail=50
```

## Security

`backend/.env` holds credentials and is gitignored. Rotate anything committed by
accident. The IAM policy in `iam/omninpc-policy.json` is scoped to model invocation and
speech synthesis rather than account wide access.

## License

MIT. See [LICENSE](LICENSE).

Rishi Chhabra and Aryan Kandari.
