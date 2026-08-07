-- OmniNPC schema — CockroachDB
-- Requires CockroachDB 25.x+ with vector indexing enabled:
--   SET CLUSTER SETTING feature.vector_index.enabled = true;

CREATE TABLE IF NOT EXISTS branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name STRING NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS npcs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID NOT NULL REFERENCES branches (id),
    name STRING NOT NULL,
    role STRING NOT NULL,              -- teller | manager | guard | customer
    personality JSONB NOT NULL,        -- traits, tone, goals
    permissions JSONB NOT NULL,        -- what info/actions this role can access
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name STRING NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    npc_id UUID NOT NULL REFERENCES npcs (id),
    player_id UUID NOT NULL REFERENCES players (id),
    trust_score DECIMAL NOT NULL DEFAULT 0,
    last_interaction_at TIMESTAMPTZ,
    notes STRING,
    UNIQUE (npc_id, player_id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    npc_id UUID NOT NULL REFERENCES npcs (id),
    player_id UUID NOT NULL REFERENCES players (id),
    session_id UUID NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    -- One conversation per character, player, and session. Without this the dialogue
    -- route's upsert has nothing to conflict on and writes a fresh row every turn.
    UNIQUE (npc_id, player_id, session_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations (id),
    speaker STRING NOT NULL,           -- player | npc
    content STRING NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    INDEX (conversation_id, created_at)
);

CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID NOT NULL REFERENCES branches (id),
    type STRING NOT NULL,              -- e.g. suspicious_question, vault_approach
    description STRING NOT NULL,
    npc_id UUID REFERENCES npcs (id),
    player_id UUID REFERENCES players (id),
    severity STRING NOT NULL DEFAULT 'low',
    visibility STRING NOT NULL DEFAULT 'private',  -- private | shared
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS promises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    npc_id UUID NOT NULL REFERENCES npcs (id),
    player_id UUID NOT NULL REFERENCES players (id),
    description STRING NOT NULL,
    status STRING NOT NULL DEFAULT 'pending',  -- pending | fulfilled | broken
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    due_at TIMESTAMPTZ
);

-- Branch-wide knowledge visible to any NPC whose role is in visible_to_roles
CREATE TABLE IF NOT EXISTS shared_branch_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID NOT NULL REFERENCES branches (id),
    incident_id UUID REFERENCES incidents (id),
    summary STRING NOT NULL,
    visible_to_roles JSONB NOT NULL,   -- e.g. ["guard", "manager"]
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Semantic memory: one row per memorable event (message, incident, promise, shared event)
CREATE TABLE IF NOT EXISTS memory_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type STRING NOT NULL,       -- message | incident | promise | shared_event
    source_id UUID NOT NULL,
    npc_id UUID REFERENCES npcs (id),  -- null when the memory is branch-shared, not NPC-private
    player_id UUID REFERENCES players (id),
    content STRING NOT NULL,
    -- Must match app/embeddings.py embedding_dim() for the configured provider:
    -- Bedrock Titan Text Embeddings V2 at 1024, or local all-MiniLM-L6-v2 at 384.
    embedding VECTOR(1024) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE VECTOR INDEX IF NOT EXISTS memory_embeddings_vec_idx
    ON memory_embeddings (embedding);

-- LangGraph-style checkpoints so a conversation survives an EKS pod restart.
-- idempotency_key lets the agent safely retry a write after a crash mid-turn.
CREATE TABLE IF NOT EXISTS agent_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    npc_id UUID NOT NULL REFERENCES npcs (id),
    player_id UUID NOT NULL REFERENCES players (id),
    idempotency_key STRING NOT NULL,
    state JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (session_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS agent_checkpoints_session_idx ON agent_checkpoints (session_id, updated_at DESC);
