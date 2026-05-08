"""Apply post-baseline SQL patches (004, 025) with backward compatibility.

Tables created:
  - refresh_tokens  (patch 004)
  - audit_events    (patch 004)
  - api_keys        (patch 025)

RLS policies added:
  - tenant_isolation_audit_events
  - tenant_isolation_memory_blocks
  - tenant_isolation_archival_memory

For existing databases where these tables already exist from manual patch
application: each CREATE is wrapped in a PL/pgSQL block that swallows
duplicate_table / duplicate_object exceptions, so the migration is idempotent.
"""

from alembic import op

# revision identifiers
revision = "003_patches"
down_revision = "002_hafidz_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # refresh_tokens (patch 004)
    # ------------------------------------------------------------------
    op.execute("""
    DO $$
    BEGIN
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
    EXCEPTION WHEN duplicate_table THEN
        NULL;
    END $$;
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_family ON refresh_tokens(session_family);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires ON refresh_tokens(expires_at) WHERE revoked_at IS NULL;")

    # ------------------------------------------------------------------
    # audit_events (patch 004)
    # ------------------------------------------------------------------
    op.execute("""
    DO $$
    BEGIN
        CREATE TABLE audit_events (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            event_type VARCHAR(64) NOT NULL
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
    EXCEPTION WHEN duplicate_table THEN
        NULL;
    END $$;
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_tenant ON audit_events(tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_user ON audit_events(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_created ON audit_events(created_at DESC);")

    # RLS for audit_events
    op.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;")
    op.execute("""
    DO $$
    BEGIN
        CREATE POLICY tenant_isolation_audit_events ON audit_events
            USING (tenant_id = current_setting('app.current_tenant')::uuid);
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END $$;
    """)

    # RLS for memory_blocks & archival_memory (patch 004)
    op.execute("""
    DO $$
    BEGIN
        CREATE POLICY tenant_isolation_memory_blocks ON memory_blocks
            USING (
                agent_id IN (
                    SELECT id FROM agents
                    WHERE tenant_id = current_setting('app.current_tenant')::uuid
                )
            );
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END $$;
    """)

    op.execute("""
    DO $$
    BEGIN
        CREATE POLICY tenant_isolation_archival_memory ON archival_memory
            USING (
                agent_id IN (
                    SELECT id FROM agents
                    WHERE tenant_id = current_setting('app.current_tenant')::uuid
                )
            );
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END $$;
    """)

    # ------------------------------------------------------------------
    # api_keys (patch 025)
    # ------------------------------------------------------------------
    op.execute("""
    DO $$
    BEGIN
        CREATE TABLE api_keys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            prefix TEXT NOT NULL,
            key_hash BYTEA NOT NULL,
            scopes TEXT[] NOT NULL DEFAULT ARRAY['tools:exec','chat:read','chat:write']::text[],
            last_used_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            revoked_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    EXCEPTION WHEN duplicate_table THEN
        NULL;
    END $$;
    """)

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_hash_active ON api_keys(key_hash) WHERE revoked_at IS NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(prefix);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id) WHERE revoked_at IS NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id) WHERE revoked_at IS NULL;")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_api_keys_tenant;")
    op.execute("DROP INDEX IF EXISTS idx_api_keys_user;")
    op.execute("DROP INDEX IF EXISTS idx_api_keys_prefix;")
    op.execute("DROP INDEX IF EXISTS idx_api_keys_hash_active;")
    op.execute("DROP TABLE IF EXISTS api_keys;")

    op.execute("DROP POLICY IF EXISTS tenant_isolation_archival_memory ON archival_memory;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_memory_blocks ON memory_blocks;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_audit_events ON audit_events;")
    op.execute("ALTER TABLE audit_events DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP INDEX IF EXISTS idx_audit_events_created;")
    op.execute("DROP INDEX IF EXISTS idx_audit_events_type;")
    op.execute("DROP INDEX IF EXISTS idx_audit_events_user;")
    op.execute("DROP INDEX IF EXISTS idx_audit_events_tenant;")
    op.execute("DROP TABLE IF EXISTS audit_events;")

    op.execute("DROP INDEX IF EXISTS idx_refresh_tokens_expires;")
    op.execute("DROP INDEX IF EXISTS idx_refresh_tokens_user;")
    op.execute("DROP INDEX IF EXISTS idx_refresh_tokens_family;")
    op.execute("DROP INDEX IF EXISTS idx_refresh_tokens_hash;")
    op.execute("DROP TABLE IF EXISTS refresh_tokens;")
