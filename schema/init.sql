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
    role STRING NOT NULL,
    personality JSONB NOT NULL,
    permissions JSONB NOT NULL,
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
    -- Required by the dialogue route's conversation upsert.
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
    type STRING NOT NULL,
    description STRING NOT NULL,
    npc_id UUID REFERENCES npcs (id),
    player_id UUID REFERENCES players (id),
    severity STRING NOT NULL DEFAULT 'low',
    visibility STRING NOT NULL DEFAULT 'private',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS promises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    npc_id UUID NOT NULL REFERENCES npcs (id),
    player_id UUID NOT NULL REFERENCES players (id),
    description STRING NOT NULL,
    status STRING NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    due_at TIMESTAMPTZ
);

-- Branch events are filtered against visible_to_roles during recall.
CREATE TABLE IF NOT EXISTS shared_branch_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID NOT NULL REFERENCES branches (id),
    incident_id UUID REFERENCES incidents (id),
    event_key STRING,
    summary STRING NOT NULL,
    visible_to_roles JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE shared_branch_events ADD COLUMN IF NOT EXISTS event_key STRING;
CREATE UNIQUE INDEX IF NOT EXISTS shared_branch_events_event_key_idx
    ON shared_branch_events (event_key);

-- Searchable representations of messages and branch events.
CREATE TABLE IF NOT EXISTS memory_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type STRING NOT NULL,
    source_id UUID NOT NULL,
    npc_id UUID REFERENCES npcs (id),  -- null for shared events
    player_id UUID REFERENCES players (id),
    -- Null permits server-side verification across sessions.
    session_id UUID,
    content STRING NOT NULL,
    -- Must match the configured embedding provider.
    embedding VECTOR(1024) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE VECTOR INDEX IF NOT EXISTS memory_embeddings_vec_idx
    ON memory_embeddings (embedding);

CREATE INDEX IF NOT EXISTS memory_embeddings_session_idx ON memory_embeddings (session_id);

-- Reserved for agent state; application code does not use this table yet.
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
