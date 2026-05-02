# ERD & DATABASE SCHEMA — ADO System
**Version:** 1.0
**Database:** PostgreSQL 16 + pgvector
**Last Updated:** 2026-05-02

---

## 1. ENTITY RELATIONSHIP DIAGRAM

```
┌─────────────┐       ┌───────────────┐       ┌──────────────────┐
│   TENANTS   │──1:N──│     USERS     │──1:N──│     AGENTS       │
│             │       │               │       │                  │
│ id          │       │ id            │       │ id               │
│ name        │       │ tenant_id FK  │       │ tenant_id FK     │
│ plan        │       │ email         │       │ owner_user_id FK │
│ created_at  │       │ password_hash │       │ parent_agent_id FK│
└─────────────┘       │ role          │       │ name             │
                      │ created_at    │       │ model_version FK  │
                      └───────────────┘       │ persona_blob     │
                                              │ letta_agent_id   │
                                              └──────────────────┘
                                                       │ 1:N (lineage)
                                                       │ self-ref
                                                       ▼
                                              ┌──────────────────┐
                                              │  child agents... │
                                              └──────────────────┘

┌──────────────────┐       ┌───────────────────┐
│   CONVERSATIONS  │──1:N──│    MESSAGES       │
│                  │       │                   │
│ id               │       │ id                │
│ tenant_id FK     │       │ conversation_id FK│
│ agent_id FK      │       │ role              │
│ user_id FK       │       │ content           │
│ started_at       │       │ tool_calls        │
└──────────────────┘       │ model_version FK  │
                           │ latency_ms        │
                           └─────────┬─────────┘
                                     │ 1:N
                                     ▼
                           ┌─────────────────────┐
                           │ INTERACTIONS_FEEDBACK│
                           │                     │
                           │ id                  │
                           │ message_id FK       │
                           │ signal_type         │
                           │ value               │
                           │ source              │
                           └─────────────────────┘

┌──────────────────┐       ┌───────────────────┐
│  MODEL_VERSIONS  │──1:N──│  TRAINING_RUNS    │
│                  │       │                   │
│ id               │       │ id                │
│ base_model       │       │ model_version FK  │
│ version_tag      │       │ dataset_id FK     │
│ parent_version FK│       │ method            │
│ adapter_uri      │       │ hyperparameters   │
│ eval_scores      │       │ cost_usd          │
│ deployed_at      │       │ runpod_pod_id     │
└──────────────────┘       │ started_at        │
                           └───────────────────┘

┌──────────────────┐
│    DATASETS      │
│                  │
│ id               │
│ name             │
│ source_type      │
│ size_samples     │
│ parent_dataset FK│
│ hf_dataset_uri   │
└──────────────────┘

┌──────────────────┐       ┌───────────────────┐
│  PREFERENCE_PAIRS│       │     TOOLS         │
│                  │       │                   │
│ id               │       │ id                │
│ prompt           │       │ tenant_id FK NULL │
│ chosen           │       │ name              │
│ rejected         │       │ schema            │
│ judge_score      │       │ handler_type      │
│ source_method    │       │ handler_config    │
│ used_in_run FK   │       │ scopes_required   │
└──────────────────┘       └──────────┬────────┘
                                      │ M:N
                           ┌──────────▼────────┐
                           │ AGENT_TOOL_GRANTS │
                           │                   │
                           │ agent_id FK       │
                           │ tool_id FK        │
                           │ granted_by FK     │
                           │ granted_at        │
                           └───────────────────┘

┌──────────────────┐       ┌───────────────────┐
│  MEMORY_BLOCKS   │       │  ARCHIVAL_MEMORY  │
│  (Letta-style)   │       │                   │
│                  │       │ id                │
│ id               │       │ agent_id FK       │
│ agent_id FK      │       │ namespace         │
│ label            │       │ content           │
│ content          │       │ embedding VECTOR  │
│ embedding VECTOR │       │ metadata JSONB    │
│ last_edited_at   │       │ created_at        │
└──────────────────┘       └───────────────────┘

┌──────────────────┐       ┌───────────────────┐
│  KG_ENTITIES     │──1:N──│   KG_RELATIONS    │
│  (Sidixlab)      │       │                   │
│                  │       │ id                │
│ id               │       │ head_id FK        │
│ name             │       │ tail_id FK        │
│ entity_type      │       │ relation          │
│ embedding VECTOR │       │ evidence          │
│ source_paper FK  │       │ confidence        │
└──────────────────┘       └───────────────────┘

┌──────────────────┐       ┌───────────────────┐
│     PAPERS       │       │   EXPERIMENTS     │
│  (Sidixlab)      │       │   (Sidixlab)      │
│                  │       │                   │
│ id               │       │ id                │
│ arxiv_id         │       │ hypothesis        │
│ title            │       │ method            │
│ abstract         │       │ status            │
│ embedding VECTOR │       │ results JSONB     │
│ insights JSONB   │       │ model_version FK  │
│ ingested_at      │       │ started_at        │
└──────────────────┘       └───────────────────┘
```

---

## 2. COMPLETE SQL SCHEMA

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================
-- MULTI-TENANCY FOUNDATION
-- ============================================================

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(63) UNIQUE NOT NULL,
    plan VARCHAR(32) NOT NULL DEFAULT 'free'
        CHECK (plan IN ('free', 'starter', 'pro', 'enterprise')),
    max_agents INTEGER NOT NULL DEFAULT 3,
    max_messages_per_day INTEGER NOT NULL DEFAULT 1000,
    api_key_hash VARCHAR(255),
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'member'
        CHECK (role IN ('owner', 'admin', 'member', 'readonly')),
    display_name VARCHAR(255),
    avatar_url VARCHAR(512),
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);

-- ============================================================
-- MODEL VERSIONING — The Evolution Lineage
-- ============================================================

CREATE TABLE model_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    base_model VARCHAR(128) NOT NULL, -- "qwen2.5-7b-instruct"
    version_tag VARCHAR(64) UNIQUE NOT NULL, -- "v0.3-soul-2026-04-22"
    parent_version_id UUID REFERENCES model_versions(id),
    adapter_uri VARCHAR(512), -- HuggingFace Hub URL for LoRA adapter
    gguf_uri VARCHAR(512),    -- URL to GGUF file
    evaluation_scores JSONB NOT NULL DEFAULT '{}',
    -- {"alpaca_eval": 85.2, "persona_consistency": 0.91, "tool_use_accuracy": 0.84}
    is_active BOOLEAN NOT NULL DEFAULT false,
    is_candidate BOOLEAN NOT NULL DEFAULT false, -- A/B testing candidate
    deployed_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_model_versions_active ON model_versions(is_active) WHERE is_active = true;

-- ============================================================
-- AGENTS — The Digital Organisms
-- ============================================================

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    parent_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL, -- lineage!
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(63) NOT NULL,
    generation INTEGER NOT NULL DEFAULT 0, -- 0 = Core Brain, 1 = first child, etc.
    model_version_id UUID REFERENCES model_versions(id),
    persona_blob JSONB NOT NULL DEFAULT '{}',
    -- {soul_md: "...", mode: "customer_success", voice: "warm", anti_patterns: [...], values: [...]}
    letta_agent_id VARCHAR(255), -- reference to Letta service
    visibility VARCHAR(16) NOT NULL DEFAULT 'private'
        CHECK (visibility IN ('private', 'tenant', 'public')),
    webhook_url VARCHAR(512),
    status VARCHAR(16) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'paused', 'archived')),
    interaction_count INTEGER NOT NULL DEFAULT 0,
    avg_quality_score FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ,
    UNIQUE (tenant_id, slug)
);

CREATE INDEX idx_agents_tenant ON agents(tenant_id);
CREATE INDEX idx_agents_owner ON agents(owner_user_id);
CREATE INDEX idx_agents_parent ON agents(parent_agent_id);
CREATE INDEX idx_agents_status ON agents(status) WHERE status = 'active';

-- Lineage query helper (recursive CTE example)
-- WITH RECURSIVE lineage AS (
--   SELECT id, parent_agent_id, name, generation, 0 AS depth FROM agents WHERE id = $core_brain_id
--   UNION ALL
--   SELECT a.id, a.parent_agent_id, a.name, a.generation, l.depth+1
--   FROM agents a JOIN lineage l ON a.parent_agent_id = l.id
-- )
-- SELECT * FROM lineage ORDER BY depth;

-- ============================================================
-- CONVERSATIONS & MESSAGES
-- ============================================================

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    external_user_id VARCHAR(255), -- for webhook-based conversations
    title VARCHAR(255),
    status VARCHAR(16) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'archived')),
    message_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_conversations_agent ON conversations(agent_id);
CREATE INDEX idx_conversations_tenant ON conversations(tenant_id);
CREATE INDEX idx_conversations_last ON conversations(last_message_at DESC);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL, -- denormalized for RLS efficiency
    role VARCHAR(16) NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    tool_calls JSONB, -- [{name, args, result}]
    model_version_id UUID REFERENCES model_versions(id),
    tokens_in INTEGER,
    tokens_out INTEGER,
    latency_ms INTEGER,
    quality_score FLOAT, -- from LLM-as-Judge, computed async
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_tenant ON messages(tenant_id);
CREATE INDEX idx_messages_quality ON messages(quality_score) WHERE quality_score IS NOT NULL;

-- ============================================================
-- FEEDBACK — The Soul Food
-- ============================================================

CREATE TABLE interactions_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    signal_type VARCHAR(32) NOT NULL
        CHECK (signal_type IN ('thumb_up','thumb_down','followup','retry','length_ok','length_bad','correction')),
    value FLOAT, -- normalized 0-1 where applicable
    source VARCHAR(16) NOT NULL CHECK (source IN ('user', 'llm_judge', 'implicit')),
    judge_model VARCHAR(64), -- which judge model if source=llm_judge
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feedback_message ON interactions_feedback(message_id);
CREATE INDEX idx_feedback_tenant ON interactions_feedback(tenant_id);
CREATE INDEX idx_feedback_created ON interactions_feedback(created_at DESC);

-- ============================================================
-- TRAINING PIPELINE — The Evolution Engine
-- ============================================================

CREATE TABLE datasets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(32) NOT NULL
        CHECK (source_type IN ('magpie','curated','distilled','feedback','self_play','constitutional')),
    size_samples INTEGER,
    hf_dataset_uri VARCHAR(512),
    local_path VARCHAR(512),
    parent_dataset_id UUID REFERENCES datasets(id),
    quality_avg FLOAT,
    language VARCHAR(8) DEFAULT 'id',
    domain VARCHAR(64),
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE preference_pairs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt TEXT NOT NULL,
    chosen TEXT NOT NULL,
    rejected TEXT NOT NULL,
    judge_score FLOAT NOT NULL, -- 0-1, how certain the judge is
    judge_model VARCHAR(64),
    source_method VARCHAR(64) NOT NULL, -- "self_rewarding_v1", "constitutional_cai", "user_feedback"
    source_message_id UUID REFERENCES messages(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    used_in_training_run_id UUID -- set when used
);

CREATE INDEX idx_prefs_score ON preference_pairs(judge_score DESC);
CREATE INDEX idx_prefs_used ON preference_pairs(used_in_training_run_id) WHERE used_in_training_run_id IS NULL;

CREATE TABLE training_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID REFERENCES model_versions(id),
    base_model VARCHAR(128) NOT NULL,
    method VARCHAR(16) NOT NULL CHECK (method IN ('sft','dpo','simpo','orpo','kto')),
    dataset_id UUID REFERENCES datasets(id),
    hyperparameters JSONB NOT NULL DEFAULT '{}',
    -- {"lr": 2e-4, "epochs": 3, "batch_size": 4, "rank": 16, "alpha": 32}
    runpod_pod_id VARCHAR(64),
    cost_usd NUMERIC(8,4),
    mlflow_run_id VARCHAR(128),
    status VARCHAR(16) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','running','success','failed','rolled_back')),
    train_loss_final FLOAT,
    eval_loss_final FLOAT,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    error_log TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TOOLS REGISTRY
-- ============================================================

CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE, -- NULL = global tool
    name VARCHAR(64) NOT NULL,
    display_name VARCHAR(128),
    description TEXT,
    schema JSONB NOT NULL, -- JSON Schema for parameters
    handler_type VARCHAR(16) NOT NULL CHECK (handler_type IN ('builtin','python_callable','webhook','mcp')),
    handler_config JSONB NOT NULL DEFAULT '{}',
    scopes_required TEXT[] NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, name)
);

CREATE TABLE agent_tool_grants (
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    granted_by_user_id UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (agent_id, tool_id)
);

-- ============================================================
-- MEMORY — The Hippocampus
-- ============================================================

CREATE TABLE memory_blocks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    label VARCHAR(64) NOT NULL, -- 'persona', 'human', 'current_task', 'world_state'
    content TEXT NOT NULL,
    char_limit INTEGER NOT NULL DEFAULT 4096,
    embedding VECTOR(1024),
    last_edited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (agent_id, label)
);

CREATE INDEX idx_memory_blocks_agent ON memory_blocks(agent_id);

CREATE TABLE archival_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    namespace VARCHAR(64) NOT NULL DEFAULT 'default',
    content TEXT NOT NULL,
    embedding VECTOR(1024),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_archival_agent ON archival_memory(agent_id, namespace);
CREATE INDEX idx_archival_embedding ON archival_memory USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ============================================================
-- SIDIXLAB — Research Pipeline
-- ============================================================

CREATE TABLE papers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    arxiv_id VARCHAR(32) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    authors TEXT[],
    abstract TEXT,
    full_text TEXT,
    published_at DATE,
    categories TEXT[],
    embedding VECTOR(1024),
    summary TEXT, -- LLM-generated
    insights JSONB, -- [{insight: "...", implementability: 0.9, priority: "high"}]
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX idx_papers_arxiv ON papers(arxiv_id);
CREATE INDEX idx_papers_published ON papers(published_at DESC);
CREATE INDEX idx_papers_embedding ON papers USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

CREATE TABLE kg_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    entity_type VARCHAR(64), -- 'method', 'model', 'dataset', 'concept', 'person'
    description TEXT,
    embedding VECTOR(1024),
    source_paper_id UUID REFERENCES papers(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE kg_relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    head_id UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    tail_id UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    relation VARCHAR(128) NOT NULL, -- 'outperforms', 'builds_on', 'contradicts', 'requires'
    evidence TEXT,
    confidence FLOAT NOT NULL DEFAULT 0.5,
    source_paper_id UUID REFERENCES papers(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE experiments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    hypothesis TEXT NOT NULL,
    method TEXT,
    expected_outcome TEXT,
    actual_outcome TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'hypothesis'
        CHECK (status IN ('hypothesis','planned','running','completed','abandoned')),
    priority VARCHAR(8) NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low','medium','high','critical')),
    model_version_id UUID REFERENCES model_versions(id),
    training_run_id UUID REFERENCES training_runs(id),
    results JSONB NOT NULL DEFAULT '{}',
    insights TEXT,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

-- Enable RLS on all tenant-scoped tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE interactions_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_blocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE archival_memory ENABLE ROW LEVEL SECURITY;

-- RLS policies (app sets current_setting before queries)
CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_agents ON agents
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_conversations ON conversations
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_messages ON messages
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- ============================================================
-- SEED DATA
-- ============================================================

-- Global tools (tenant_id NULL = available to all)
INSERT INTO tools (name, display_name, description, handler_type, schema) VALUES
('web_search', 'Web Search', 'Search the web for current information', 'builtin',
 '{"type":"object","properties":{"query":{"type":"string","description":"Search query"}},"required":["query"]}'),
('python_repl', 'Python REPL', 'Execute Python code in a sandbox', 'builtin',
 '{"type":"object","properties":{"code":{"type":"string"},"timeout":{"type":"integer","default":30}},"required":["code"]}'),
('read_file', 'Read File', 'Read contents of a file', 'builtin',
 '{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}'),
('http_get', 'HTTP GET', 'Make an HTTP GET request', 'builtin',
 '{"type":"object","properties":{"url":{"type":"string"},"headers":{"type":"object"}},"required":["url"]}'),
('spawn_agent', 'Spawn Agent', 'Create a new child agent', 'builtin',
 '{"type":"object","properties":{"template_id":{"type":"string"},"name":{"type":"string"},"persona":{"type":"object"}},"required":["name"]}'),
('memory_write', 'Memory Write', 'Write a fact to long-term memory', 'builtin',
 '{"type":"object","properties":{"key":{"type":"string"},"value":{"type":"string"},"namespace":{"type":"string","default":"default"}},"required":["key","value"]}'),
('memory_search', 'Memory Search', 'Search long-term memory semantically', 'builtin',
 '{"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer","default":5}},"required":["query"]}');

-- Core Brain model version seed
INSERT INTO model_versions (base_model, version_tag, is_active) VALUES
('qwen2.5-7b-instruct', 'v0.1-seed-2026-05', true);
```
