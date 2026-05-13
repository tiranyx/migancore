-- Migration 028: Chat-derived Knowledge Graph
-- Extends existing kg_entities/kg_relations (designed for papers) with
-- chat-derived equivalents that are tenant-aware and conversation-linked.
-- Day 73 — autonomous self-learning sprint

CREATE TABLE IF NOT EXISTS chat_entities (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL,
    name            VARCHAR(255) NOT NULL,
    entity_type     VARCHAR(64) NOT NULL DEFAULT 'CONCEPT',
    mention_count   INTEGER NOT NULL DEFAULT 1,
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, name, entity_type)
);

CREATE INDEX IF NOT EXISTS idx_chat_entities_tenant ON chat_entities (tenant_id, mention_count DESC);
CREATE INDEX IF NOT EXISTS idx_chat_entities_name   ON chat_entities (tenant_id, LOWER(name));

CREATE TABLE IF NOT EXISTS chat_relations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL,
    subject         TEXT NOT NULL,
    predicate       TEXT NOT NULL,
    object          TEXT NOT NULL,
    conversation_id UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_relations_tenant  ON chat_relations (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_relations_subject ON chat_relations (tenant_id, subject);
