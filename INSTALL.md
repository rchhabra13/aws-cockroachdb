# Installing OmniNPC

OmniNPC runs as a FastAPI backend, a Phaser client, and a CockroachDB database.

## Prerequisites

- A CockroachDB cluster
- `ccloud` and `psql`
- AWS credentials with access to Amazon Nova Pro and Titan Text Embeddings V2 in the configured region
- Python for local backend development; the backend image uses Python 3.12
- Node.js and npm; no Node.js version is pinned in the repository

The default configuration uses these Bedrock model IDs in `us-east-1`:

- `us.amazon.nova-pro-v1:0`
- `amazon.titan-embed-text-v2:0`

Enable access to both models for the AWS account and region before starting the backend.

## Database

The bootstrap script reads the cluster connection details from `ccloud`, creates the database when needed, applies both SQL files, and verifies the vector index and seed rows.

```bash
export CLUSTER='<cockroachdb-cluster-name>'
export SQL_USER='<cockroachdb-sql-user>'
export CRDB_SQL_PASSWORD='<cockroachdb-sql-password>'
ccloud auth login
./scripts/bootstrap.sh
```

`CLUSTER` and `SQL_USER` have project-specific defaults in `scripts/bootstrap.sh`. Set both explicitly when using another cluster or user.

Copy the environment template and replace `COCKROACHDB_URL` with the connection string reported by the script, including the SQL password required by the application:

```bash
cp backend/.env.example backend/.env
```

## Backend

Local Python environment:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Docker Compose:

```bash
docker compose up --build backend
```

The Compose configuration mounts `~/.postgresql/root.crt` into the container. For a CockroachDB Cloud URL using `sslmode=verify-full`, that host path must be the cluster CA certificate and must be a regular file.

Check the API:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/npcs
```

## Game

```bash
cd game
npm install
npm run dev
```

Open `http://localhost:3001`. The development client calls `http://localhost:8000` and registers a browser-specific player ID on first load. The **Remember me** control also stores the current session identifier; leave it disabled for automatic interaction-data cleanup on page teardown.

## Verification

From the repository root, with the backend running:

```bash
backend/.venv/bin/python scripts/verify.py
```

The script clears messages, memories, conversations, and shared events for the seeded demo players, then checks cross-character isolation, cross-player isolation, and automatic structuring-event publication.

## Troubleshooting

### Bedrock access errors

Confirm that both configured model IDs are enabled in the same region as `AWS_REGION`. Embeddings do not use the Gemini dialogue fallback.

### TLS certificate mount errors

If Docker reports `IsADirectoryError` for `/root/.postgresql/root.crt`, inspect `~/.postgresql/root.crt` on the host. Docker creates a directory at a missing bind-mount source path; replace it with the CockroachDB cluster CA certificate before restarting the container.

### Database connection errors

The value in `backend/.env.example` points to an insecure local CockroachDB instance. Replace it with the connection string for the provisioned cluster before running the backend against CockroachDB Cloud.
