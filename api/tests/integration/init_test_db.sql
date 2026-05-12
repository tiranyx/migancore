-- MIGANCORE Test DB Init — create non-superuser app role (matches production)
-- PostgreSQL Docker runs this on first startup via /docker-entrypoint-initdb.d/

-- pgvector extension requires superuser; create it before app user connects
CREATE EXTENSION IF NOT EXISTS "vector";

CREATE USER ado_app WITH PASSWORD 'test' CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE ado_test TO ado_app;
GRANT ALL PRIVILEGES ON SCHEMA public TO ado_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ado_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ado_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO ado_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TYPES TO ado_app;
