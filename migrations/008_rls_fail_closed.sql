-- Migration 008: Make RLS policies fail-closed when tenant context is missing
--
-- Problem: current_setting('app.current_tenant') raises an error or returns ''
-- when not set, causing UUID cast failures or unexpected behavior.
-- Fix: Use NULLIF(..., '') so unset context → NULL → tenant_id = NULL → FALSE/NULL
-- which is fail-closed (no rows visible, inserts rejected).

-- Drop and recreate policies with safe NULLIF handling
DROP POLICY IF EXISTS tenant_isolation_users ON users;
CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid);

DROP POLICY IF EXISTS tenant_isolation_agents ON agents;
CREATE POLICY tenant_isolation_agents ON agents
    USING (tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid);

DROP POLICY IF EXISTS tenant_isolation_tools ON tools;
CREATE POLICY tenant_isolation_tools ON tools
    USING (tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid);

DROP POLICY IF EXISTS tenant_isolation_audit_events ON audit_events;
CREATE POLICY tenant_isolation_audit_events ON audit_events
    USING (tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid);
