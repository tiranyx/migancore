"""Schema hardening â€” consolidate SQL patches 005â€“011 and 024 into Alembic.

Covers schema drift that existed between manual SQL patches and the ORM:
  â€¢ tools.risk_level, tools.policy, tools.max_calls_per_day  (patch 011)
  â€¢ tenants.messages_today, tenants.messages_day_reset       (patch 011)
  â€¢ auth_lookup_user_by_email() SECURITY DEFINER             (patch 010)
  â€¢ RLS policy fixes: NULLIF fail-closed, missing policies   (patches 005â€“009)
  â€¢ FORCE ROW LEVEL SECURITY on all tenant-isolated tables   (patch 006)
  â€¢ Tool seed updates: write_file, generate_image, read_file fix (patch 024)

All DDL is idempotent (IF NOT EXISTS / IF EXISTS) so it is safe to run on
production databases where these patches were already applied manually.
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "007_schema_hardening"
down_revision = "006_owner_datasets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()

    # ------------------------------------------------------------------
    # 1. TOOLS â€” add columns from patch 011 (safety gates)
    # ------------------------------------------------------------------
    connection.execute(text("""
        ALTER TABLE tools
            ADD COLUMN IF NOT EXISTS risk_level VARCHAR(16) NOT NULL DEFAULT 'medium'
                CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
            ADD COLUMN IF NOT EXISTS policy JSONB NOT NULL DEFAULT '{}',
            ADD COLUMN IF NOT EXISTS max_calls_per_day INT NOT NULL DEFAULT 1000;
    """))

    # ------------------------------------------------------------------
    # 2. TENANTS â€” add quota tracking columns from patch 011
    # ------------------------------------------------------------------
    connection.execute(text("""
        ALTER TABLE tenants
            ADD COLUMN IF NOT EXISTS messages_today INT NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS messages_day_reset TIMESTAMPTZ;
    """))

    # ------------------------------------------------------------------
    # 3. AUTH â€” SECURITY DEFINER lookup function from patch 010
    # ------------------------------------------------------------------
    # Use CREATE FUNCTION (not OR REPLACE) inside a DO block so that
    # if the function already exists (e.g. created manually by superuser)
    # we swallow the duplicate_function exception rather than failing
    # with "must be owner of function".
    #
    # NOTE: We use op.execute with a plain string (not sa.text) because
    # asyncpg does not support multiple commands in a prepared statement.
    # The DO block is a single PL/pgSQL anonymous block.
    op.execute("""
        DO $$
        BEGIN
            CREATE FUNCTION auth_lookup_user_by_email(p_email VARCHAR)
            RETURNS TABLE (
                id UUID,
                tenant_id UUID,
                email VARCHAR,
                password_hash VARCHAR,
                role VARCHAR,
                display_name VARCHAR,
                last_login_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ
            ) SECURITY DEFINER
            AS $func$
            BEGIN
                RETURN QUERY
                SELECT u.id, u.tenant_id, u.email, u.password_hash, u.role,
                       u.display_name, u.last_login_at, u.created_at
                FROM users u
                WHERE u.email = p_email;
            END;
            $func$ LANGUAGE plpgsql;
        EXCEPTION WHEN duplicate_function THEN
            RAISE NOTICE 'auth_lookup_user_by_email already exists, skipping creation.';
        END $$;
    """)
    op.execute("GRANT EXECUTE ON FUNCTION auth_lookup_user_by_email(VARCHAR) TO ado_app;")

    # ------------------------------------------------------------------
    # 4. RLS â€” fix policies to NULLIF fail-closed (patch 008 + 009)
    # ------------------------------------------------------------------
    # 4a. users â€” disable old policy, re-enable with NULLIF + SECURITY DEFINER fallback
    connection.execute(text("DROP POLICY IF EXISTS tenant_isolation_users ON users;"))
    connection.execute(text("ALTER TABLE users ENABLE ROW LEVEL SECURITY;"))
    connection.execute(text("""
        CREATE POLICY tenant_isolation_users ON users
            USING (tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid);
    """))

    # 4b. agents
    connection.execute(text("DROP POLICY IF EXISTS tenant_isolation_agents ON agents;"))
    connection.execute(text("""
        CREATE POLICY tenant_isolation_agents ON agents
            USING (tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid);
    """))

    # 4c. conversations
    connection.execute(text("DROP POLICY IF EXISTS tenant_isolation_conversations ON conversations;"))
    connection.execute(text("""
        CREATE POLICY tenant_isolation_conversations ON conversations
            USING (tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid);
    """))

    # 4d. messages
    connection.execute(text("DROP POLICY IF EXISTS tenant_isolation_messages ON messages;"))
    connection.execute(text("""
        CREATE POLICY tenant_isolation_messages ON messages
            USING (tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid);
    """))

    # 4e. interactions_feedback â€” MISSING from baseline + 003
    connection.execute(text("ALTER TABLE interactions_feedback ENABLE ROW LEVEL SECURITY;"))
    connection.execute(text("DROP POLICY IF EXISTS tenant_isolation_feedback ON interactions_feedback;"))
    connection.execute(text("""
        CREATE POLICY tenant_isolation_feedback ON interactions_feedback
            USING (tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid);
    """))

    # 4f. tools â€” allow NULL tenant_id for global tools (patch 005 + 009)
    connection.execute(text("ALTER TABLE tools ENABLE ROW LEVEL SECURITY;"))
    connection.execute(text("DROP POLICY IF EXISTS tenant_isolation_tools ON tools;"))
    connection.execute(text("""
        CREATE POLICY tenant_isolation_tools ON tools
            USING (
                tenant_id IS NULL
                OR tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid
            );
    """))

    # 4g. agent_tool_grants â€” join through agents (patch 005)
    connection.execute(text("ALTER TABLE agent_tool_grants ENABLE ROW LEVEL SECURITY;"))
    connection.execute(text("DROP POLICY IF EXISTS tenant_isolation_agent_tool_grants ON agent_tool_grants;"))
    connection.execute(text("""
        CREATE POLICY tenant_isolation_agent_tool_grants ON agent_tool_grants
            USING (
                agent_id IN (
                    SELECT id FROM agents
                    WHERE tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid
                )
            );
    """))

    # 4h. audit_events â€” allow NULL tenant_id for system events (patch 009)
    connection.execute(text("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;"))
    connection.execute(text("DROP POLICY IF EXISTS tenant_isolation_audit_events ON audit_events;"))
    connection.execute(text("""
        CREATE POLICY tenant_isolation_audit_events ON audit_events
            USING (
                tenant_id IS NULL
                OR tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid
            );
    """))

    # 4i. memory_blocks & archival_memory â€” join through agents (patch 004 + 008)
    connection.execute(text("ALTER TABLE memory_blocks ENABLE ROW LEVEL SECURITY;"))
    connection.execute(text("DROP POLICY IF EXISTS tenant_isolation_memory_blocks ON memory_blocks;"))
    connection.execute(text("""
        CREATE POLICY tenant_isolation_memory_blocks ON memory_blocks
            USING (
                agent_id IN (
                    SELECT id FROM agents
                    WHERE tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid
                )
            );
    """))

    connection.execute(text("ALTER TABLE archival_memory ENABLE ROW LEVEL SECURITY;"))
    connection.execute(text("DROP POLICY IF EXISTS tenant_isolation_archival_memory ON archival_memory;"))
    connection.execute(text("""
        CREATE POLICY tenant_isolation_archival_memory ON archival_memory
            USING (
                agent_id IN (
                    SELECT id FROM agents
                    WHERE tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid
                )
            );
    """))

    # ------------------------------------------------------------------
    # 5. FORCE ROW LEVEL SECURITY (patch 006)
    # ------------------------------------------------------------------
    for tbl in [
        "users", "agents", "conversations", "messages",
        "interactions_feedback", "tools", "agent_tool_grants",
        "audit_events", "memory_blocks", "archival_memory",
    ]:
        connection.execute(text(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;"))

    # ------------------------------------------------------------------
    # 6. INDEXES from patch 011
    # ------------------------------------------------------------------
    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_tools_risk_level ON tools(risk_level);"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_tools_policy ON tools USING GIN (policy);"))

    # ------------------------------------------------------------------
    # 7. TOOL SEED DATA â€” update existing tools with policy from 011 + 024
    # ------------------------------------------------------------------
    tool_updates = [
        (
            "web_search",
            "low",
            '{"classes":["read_only","open_world"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}',
            100,
        ),
        (
            "memory_search",
            "low",
            '{"classes":["read_only"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}',
            1000,
        ),
        (
            "memory_write",
            "low",
            '{"classes":["write"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}',
            500,
        ),
        (
            "http_get",
            "medium",
            '{"classes":["open_world"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["pro","enterprise"]}',
            200,
        ),
        (
            "read_file",
            "low",
            '{"classes":["read_only"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}',
            200,
        ),
        (
            "python_repl",
            "critical",
            '{"classes":["destructive","sandbox_required"],"requires_approval":true,"sandbox_required":true,"allowed_plans":["enterprise"]}',
            10,
        ),
        (
            "spawn_agent",
            "high",
            '{"classes":["destructive"],"requires_approval":true,"sandbox_required":false,"allowed_plans":["pro","enterprise"]}',
            20,
        ),
    ]
    for name, risk, policy, max_calls in tool_updates:
        # exec_driver_sql bypasses SQLAlchemy text() parsing so JSON
        # colons and ::jsonb casts are sent to PostgreSQL verbatim.
        connection.exec_driver_sql(
            f"""
            UPDATE tools
            SET risk_level = '{risk}',
                policy = '{policy}'::jsonb,
                max_calls_per_day = {max_calls}
            WHERE name = '{name}';
            """
        )

    # ------------------------------------------------------------------
    # 8. ADD write_file and generate_image tools (patch 024)
    # ------------------------------------------------------------------
    connection.exec_driver_sql("""
        INSERT INTO tools (name, description, schema, handler_type, handler_config, scopes_required, risk_level, policy, max_calls_per_day, is_active, tenant_id)
        SELECT
            'write_file',
            'Write content to a file in the agent sandboxed workspace. Creates parent directories automatically.',
            '{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}'::jsonb,
            'builtin', '{}'::jsonb, ARRAY[]::text[],
            'low',
            '{"classes":["write"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}'::jsonb,
            200, true, NULL
        WHERE NOT EXISTS (SELECT 1 FROM tools WHERE name = 'write_file');
    """)
    connection.exec_driver_sql("""
        UPDATE tools SET
            risk_level = 'low',
            policy = '{"classes":["write"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}'::jsonb,
            max_calls_per_day = 200,
            is_active = true
        WHERE name = 'write_file';
    """)

    connection.exec_driver_sql("""
        INSERT INTO tools (name, description, schema, handler_type, handler_config, scopes_required, risk_level, policy, max_calls_per_day, is_active, tenant_id)
        SELECT
            'generate_image',
            'Generate an image from a text prompt via fal.ai FLUX schnell. Returns URL.',
            '{"type":"object","properties":{"prompt":{"type":"string"},"image_size":{"type":"string"},"num_images":{"type":"integer"}},"required":["prompt"]}'::jsonb,
            'builtin', '{}'::jsonb, ARRAY[]::text[],
            'medium',
            '{"classes":["open_world","write"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}'::jsonb,
            100, true, NULL
        WHERE NOT EXISTS (SELECT 1 FROM tools WHERE name = 'generate_image');
    """)
    connection.exec_driver_sql("""
        UPDATE tools SET
            risk_level = 'medium',
            policy = '{"classes":["open_world","write"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}'::jsonb,
            max_calls_per_day = 100,
            is_active = true
        WHERE name = 'generate_image';
    """)


def downgrade() -> None:
    connection = op.get_bind()

    # Remove added tools
    connection.execute(text("DELETE FROM tools WHERE name IN ('write_file', 'generate_image');"))

    # Revert tool policy updates (set back to defaults)
    connection.execute(
        text("""
            UPDATE tools
            SET risk_level = 'medium',
                policy = '{}',
                max_calls_per_day = 1000
            WHERE name IN ('web_search', 'memory_search', 'memory_write', 'http_get',
                           'read_file', 'python_repl', 'spawn_agent');
        """)
    )

    # Drop indexes
    connection.execute(text("DROP INDEX IF EXISTS idx_tools_policy;"))
    connection.execute(text("DROP INDEX IF EXISTS idx_tools_risk_level;"))

    # Drop columns from tools
    connection.execute(text("ALTER TABLE tools DROP COLUMN IF EXISTS max_calls_per_day;"))
    connection.execute(text("ALTER TABLE tools DROP COLUMN IF EXISTS policy;"))
    connection.execute(text("ALTER TABLE tools DROP COLUMN IF EXISTS risk_level;"))

    # Drop columns from tenants
    connection.execute(text("ALTER TABLE tenants DROP COLUMN IF EXISTS messages_day_reset;"))
    connection.execute(text("ALTER TABLE tenants DROP COLUMN IF EXISTS messages_today;"))

    # Drop auth function
    connection.execute(text("DROP FUNCTION IF EXISTS auth_lookup_user_by_email(VARCHAR);"))

    # Drop added RLS policies
    for policy, table in [
        ("tenant_isolation_feedback", "interactions_feedback"),
        ("tenant_isolation_tools", "tools"),
        ("tenant_isolation_agent_tool_grants", "agent_tool_grants"),
        ("tenant_isolation_audit_events", "audit_events"),
        ("tenant_isolation_memory_blocks", "memory_blocks"),
        ("tenant_isolation_archival_memory", "archival_memory"),
    ]:
        connection.execute(text(f"DROP POLICY IF EXISTS {policy} ON {table};"))
        connection.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"))
        connection.execute(text(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;"))

    # For core tables, restore simple policies (pre-008 state) â€” matches 001_baseline
    for tbl in ["users", "agents", "conversations", "messages"]:
        connection.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_{tbl} ON {tbl};"))
        connection.execute(text(f"""
            CREATE POLICY tenant_isolation_{tbl} ON {tbl}
                USING (tenant_id = current_setting('app.current_tenant')::uuid);
        """))
        # Note: we do NOT disable RLS on core tables in downgrade because 001 baseline has them enabled.
        connection.execute(text(f"ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY;"))
