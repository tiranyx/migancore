-- Migration 006: Force RLS for table owners
-- PostgreSQL table owners bypass RLS by default. We must FORCE it
-- so the API (connecting as 'ado') is also subject to tenant isolation.

ALTER TABLE agents FORCE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;
ALTER TABLE tools FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
