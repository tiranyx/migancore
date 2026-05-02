-- Migration 009: Fix RLS for auth system compatibility
--
-- 1. Disable RLS on users table (for now) — login/refresh need global email lookup.
--    Will re-enable in Week 2 with a SECURITY DEFINER login lookup function.
-- 2. Restore NULL tenant_id allowance on tools (global tools) and audit_events
--    (system events like failed logins have no tenant).

-- Users: disable RLS so auth endpoints can do global lookups
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_users ON users;

-- Tools: allow NULL tenant_id for global tools
DROP POLICY IF EXISTS tenant_isolation_tools ON tools;
CREATE POLICY tenant_isolation_tools ON tools
    USING ((tenant_id IS NULL) OR (tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid));

-- Audit events: allow NULL tenant_id for system events
DROP POLICY IF EXISTS tenant_isolation_audit_events ON audit_events;
CREATE POLICY tenant_isolation_audit_events ON audit_events
    USING ((tenant_id IS NULL) OR (tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid));
