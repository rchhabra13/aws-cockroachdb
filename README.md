# OmniNPC

**Production-grade persistent memory for AI NPCs.**

Built for the [CockroachDB × AWS Hackathon: Build with Agentic Memory](https://devpost.com) (deadline Aug 18, 2026).

> Created by **Rishi Chhabra** & **Aryan Kandari**

---

## Overview

OmniNPC is an agentic backend that gives non-playable characters (NPCs) permanent, globally distributed memory. It's built for the massive concurrency of modern console games and digital entertainment titles, bringing persistent, evolving narratives to complex game worlds — think *Cyberpunk 2077*, *Marvel's Spider-Man: Miles Morales*, or *Resident Evil* — without degrading performance under heavy player load.

This project demonstrates that AI agents can lean on a fault-tolerant, distributed database as their state machine to maintain long-term episodic and semantic memory across millions of concurrent player interactions.

## Why this matters

Most game NPCs "forget" the player the moment a scene ends — dialogue trees reset, side quests don't reference earlier choices, and the world feels static. OmniNPC solves this by treating every player interaction as a durable, queryable event. NPCs recall what you said, what you did, and how it felt — consistently, at scale, and without single points of failure.

## Architecture

OmniNPC uses a containerized microservice architecture instead of serverless functions, so agent workloads keep persistent database connection pools and scale horizontally with zero downtime during in-game events (e.g., a live server launch or a world event with a player surge).

```
                    ┌─────────────────────┐
                    │   Players / Game     │
                    │   Clients            │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Amazon EKS          │
                    │   NPC Agent Pods      │
                    │   (autoscaling)       │
                    └───┬───────────────┬───┘
                        │               │
            ┌───────────▼───┐   ┌───────▼────────────┐
            │ Amazon Bedrock │   │ CockroachDB Cloud   │
            │ (LLM reasoning │   │ MCP Server          │
            │  + dialogue)   │   │ (secure read/write) │
            └────────────────┘   └───────┬─────────────┘
                                          │
                                  ┌───────▼─────────────┐
                                  │ Distributed Vector   │
                                  │ Index (episodic +    │
                                  │ semantic memory)     │
                                  └──────────────────────┘
```

### AWS

| Service | Role |
|---|---|
| **Amazon EKS** | Hosts the containerized AI agent workloads. Kubernetes `Deployments` autoscale NPC dialogue generation and memory-retrieval services horizontally to meet player load. |
| **Amazon Bedrock** | Powers the foundational LLM reasoning. Agents running on EKS call Bedrock to generate real-time, contextually aware dialogue grounded in memory retrieved from CockroachDB. |

### CockroachDB (Agentic Memory)

| Component | Role |
|---|---|
| **Cloud Managed MCP Server** | The secure read/write bridge between EKS pods and the database cluster. Pods hold persistent connections, letting NPCs log every player interaction as an immutable event. |
| **Distributed Vector Indexing** | Stores high-dimensional embeddings of every player conversation and action. When a player approaches an NPC, the agent runs a semantic search over the vector index to instantly retrieve relevant past interactions and inform the Bedrock prompt. |

## Repository structure

```
├── backend/                      # FastAPI + WebSockets agent service
│   ├── app/
│   │   ├── main.py               # FastAPI app, /ws/dialogue endpoint
│   │   ├── config.py             # env settings
│   │   ├── db.py                 # CockroachDB (asyncpg) connection pool
│   │   ├── bedrock.py            # Amazon Bedrock dialogue + embedding calls
│   │   ├── models.py             # pydantic schemas
│   │   ├── memory/
│   │   │   ├── retrieval.py      # visibility-scoped semantic recall
│   │   │   └── extraction.py     # store a turn as a memory embedding
│   │   └── routers/
│   │       ├── dialogue.py       # POST /dialogue — retrieve, call Bedrock, save
│   │       ├── inspector.py      # GET /inspector/conversations/{id} — memory inspector
│   │       └── auditor.py        # GET /auditor/incidents/{player_id} — MCP-style auditor
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                     # Next.js NPC dialogue UI + memory inspector
│   └── Dockerfile
├── schema/
│   └── init.sql                  # tables + distributed vector index
├── k8s/                          # EKS manifests (deployment.yaml, service.yaml, secrets-template.yaml — TODO)
├── docker-compose.yml            # local dev: backend + frontend
└── README.md
```

## Prerequisites

- An AWS account with permissions to provision EKS clusters and access Amazon Bedrock
- A CockroachDB Cloud account
- `kubectl`, `aws-cli`, and `docker` installed locally

## Local development

```bash
cp backend/.env.example backend/.env   # fill in COCKROACHDB_URL + AWS creds
cockroach sql --url "$COCKROACHDB_URL" -f schema/init.sql

cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev

# or both at once:
docker compose up --build
```

## Setup & deployment

### 1. Provision the database

Spin up a CockroachDB Cloud cluster and enable the Cloud Managed MCP Server from the console, then copy your connection configuration.

Run the schema initialization to set up the relational tables and the distributed vector index:

```bash
cockroach sql --url "postgresql://<user>:<password>@<cluster-url>:26257/defaultdb" -f schema/init.sql
```

### 2. Build and push the agent image

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.us-east-1.amazonaws.com
docker build -t omninpc-agent ./backend
docker push <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/omninpc-agent:latest
```

### 3. Provision EKS

Create your cluster with `eksctl` or the AWS Management Console, then point `kubectl` at it:

```bash
aws eks update-kubeconfig --region us-east-1 --name omninpc-cluster
```

### 4. Deploy the agents

Copy the secrets template and fill in your Bedrock ARN and CockroachDB MCP credentials:

```bash
cp k8s/secrets-template.yaml k8s/secrets.yaml
# edit k8s/secrets.yaml with your credentials
```

Apply the manifests:

```bash
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

Verify the pods are running and holding connection pools to CockroachDB:

```bash
kubectl get pods
kubectl logs -l app=omninpc-agent
```

## Hackathon

Built for the **CockroachDB × AWS Hackathon: Build with Agentic Memory** (Devpost, deadline Aug 18, 2026) — building an agentic application that uses CockroachDB as its persistent memory layer, deployed on AWS, using at least two CockroachDB tools (Cloud Managed MCP Server, Distributed Vector Indexing, ccloud CLI, or the Agent Skills Repo) and at least one AWS service (Bedrock, Lambda, ECS/EKS, S3, SageMaker, etc.).

## Team

- **Rishi Chhabra**
- **Aryan Kandari**

## Demo

_(Insert link to demo video here)_

## Status

🚧 Work in progress.

## License

MIT — see [LICENSE](LICENSE).
