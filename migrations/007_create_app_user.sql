-- Migration 007: Create non-superuser application role (ado_app)
--
-- WHY: The 'ado' user is the PostgreSQL bootstrap superuser. Superusers
-- ALWAYS bypass Row Level Security (RLS), making tenant isolation impossible.
-- We create a dedicated non-superuser role for the API so RLS policies are
-- actually enforced on every query.
--
-- NOTE: Run this as 'ado' (superuser). The password should match PG_PASSWORD.

CREATE ROLE ado_app WITH LOGIN PASSWORD 'changeme';

GRANT USAGE ON SCHEMA public TO ado_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ado_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ado_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ado_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ado_app;
