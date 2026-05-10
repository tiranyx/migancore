-- Day 72a: Fix audit_events RLS for service role
-- Problem: audit_events inserts were failing with RLS violation every hour
-- because the inserting role (ado_app) did not satisfy tenant_isolation_audit_events policy.
-- Solution: Add a permissive policy that allows ado_app to bypass RLS for audit logging.

DROP POLICY IF EXISTS service_bypass_audit_events ON audit_events;
CREATE POLICY service_bypass_audit_events ON audit_events FOR ALL TO ado_app WITH CHECK (true);
