-- ============================================================
-- MIGANCORE — Migration 005: RLS for tools + test harness
-- Day 5: Tenant isolation completeness
-- ============================================================

-- tools table: some are global (tenant_id NULL), some are tenant-specific
ALTER TABLE tools ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_tools ON tools
    USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.current_tenant')::uuid
    );

-- agent_tool_grants: join through agents for tenant isolation
ALTER TABLE agent_tool_grants ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_agent_tool_grants ON agent_tool_grants
    USING (
        agent_id IN (
            SELECT id FROM agents
            WHERE tenant_id = current_setting('app.current_tenant')::uuid
        )
    );

-- Verify: list all RLS-enabled tables and their policies
-- Run this manually to confirm:
-- SELECT schemaname, tablename, rowsecurity FROM pg_tables WHERE rowsecurity = true;
