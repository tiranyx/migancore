-- ============================================================
-- MIGANCORE — Migration 004: Auth & Refresh Tokens
-- Day 4: JWT foundation with refresh token rotation
-- ============================================================

-- Refresh tokens table for secure token rotation
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    session_family VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    replaced_by_token_hash VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_family ON refresh_tokens(session_family);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_expires ON refresh_tokens(expires_at) WHERE revoked_at IS NULL;

-- Audit events table for security and compliance
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    event_type VARCHAR(64) NOT NULL,
        CHECK (event_type IN (
            'auth.login', 'auth.logout', 'auth.register',
            'auth.refresh', 'auth.token_revoked',
            'agent.created', 'agent.updated', 'agent.deleted',
            'training.started', 'training.completed', 'training.failed',
            'model.promoted', 'model.rolled_back',
            'system.deploy', 'system.config_change',
            'security.suspicious_activity', 'security.session_terminated'
        )),
    resource_type VARCHAR(64),
    resource_id UUID,
    details JSONB NOT NULL DEFAULT '{}',
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_events_tenant ON audit_events(tenant_id);
CREATE INDEX idx_audit_events_user ON audit_events(user_id);
CREATE INDEX idx_audit_events_type ON audit_events(event_type);
CREATE INDEX idx_audit_events_created ON audit_events(created_at DESC);

-- RLS for audit_events (tenants can only see their own)
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_audit_events ON audit_events
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Fix: Add RLS policies for memory_blocks and archival_memory
-- They don't have tenant_id directly, so we join through agents

-- For memory_blocks: accessible if the agent belongs to the tenant
CREATE POLICY tenant_isolation_memory_blocks ON memory_blocks
    USING (
        agent_id IN (
            SELECT id FROM agents
            WHERE tenant_id = current_setting('app.current_tenant')::uuid
        )
    );

-- For archival_memory: same join-based policy
CREATE POLICY tenant_isolation_archival_memory ON archival_memory
    USING (
        agent_id IN (
            SELECT id FROM agents
            WHERE tenant_id = current_setting('app.current_tenant')::uuid
        )
    );
