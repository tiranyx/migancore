# Production Database Migration Guide

## Overview
MiganCore uses Alembic for schema migrations. The production database was initially bootstrapped via `init.sql` (PostgreSQL docker-entrypoint-initdb.d). This guide explains how to transition to Alembic-managed schema and apply new migrations.

## For Existing Production Databases

If your database was created before Alembic migrations (pre-2026-05-09), the tables already exist from `init.sql` + manual patches. You need to **stamp** the baseline so Alembic knows which migrations are already applied.

### Step 1: Stamp Baseline

SSH into the VPS and run:

```bash
cd /opt/ado/api
export DATABASE_URL="postgresql+asyncpg://ado_app:${PG_PASSWORD}@postgres:5432/ado"

# Stamp the baseline (001) â€” tells Alembic "schema up to 001 already exists"
alembic stamp 001_baseline

# Stamp subsequent migrations that are already applied
alembic stamp 002_hafidz_ledger
alembic stamp 003_patches
alembic stamp 004_brain_segments
alembic stamp 005_feedback_enhance
alembic stamp 006_owner_datasets
```

> **Why stamp each one?** Because patches 002â€“006 may or may not have been applied manually on your production DB. Stamping is idempotent â€” if the migration is already applied, Alembic just records it. If not, you should run `alembic upgrade` instead.

### Step 2: Apply Missing Migrations

After stamping, apply any missing migrations:

```bash
alembic upgrade head
```

This will safely apply `007_schema_hardening` (and any future migrations) using idempotent DDL (`IF NOT EXISTS` / `IF EXISTS`).

## For New Databases

On a fresh PostgreSQL instance:

```bash
# 1. Let PostgreSQL init run (creates extensions, roles via init.sql or manually)
# 2. Run Alembic migrations
alembic upgrade head
```

## Docker Compose Integration

### Test Environment
`docker-compose.test.yml` now runs `alembic upgrade head` instead of `init_test_db.py`:

```yaml
command:
  - /bin/bash
  - -c
  - |
    # ... wait for dependencies ...
    cd /app && alembic upgrade head
    pytest tests/ ...
```

### Production Environment
`docker-compose.yml` still mounts `init.sql` for initial PostgreSQL bootstrap (extensions, roles). For schema changes going forward:

1. Build and deploy new API image
2. Run `alembic upgrade head` inside the API container:

```bash
docker compose exec api alembic upgrade head
```

Or add a one-shot migration job to `docker-compose.yml`:

```yaml
  migrate:
    build: { context: ./api, dockerfile: Dockerfile }
    entrypoint: ["alembic"]
    command: ["upgrade", "head"]
    environment:
      DATABASE_URL: postgresql+asyncpg://ado_app:${PG_PASSWORD}@postgres:5432/ado
    depends_on: [postgres]
    profiles: ["migrate"]
```

Run: `docker compose --profile migrate up migrate`

## Rollback

If a migration causes issues, roll back one step:

```bash
alembic downgrade -1
```

Or roll back to a specific revision:

```bash
alembic downgrade 006_owner_datasets
```

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) automatically runs `alembic upgrade head` before integration tests. The deploy workflow (`deploy-staging.yml`) pulls code and rebuilds containers but does NOT run migrations automatically â€” this is intentional to prevent accidental schema changes during deploy.

**Recommended deploy flow:**
1. CI passes
2. Manual approval for deploy
3. Deploy code: `docker compose build api && docker compose up -d api`
4. Run migrations: `docker compose exec api alembic upgrade head`
5. Health check

## Migration Checklist

Before creating a new migration:
- [ ] Test locally: `alembic upgrade head` on fresh DB
- [ ] Test downgrade: `alembic downgrade -1`
- [ ] Run full test suite: 169 pass, 0 fail
- [ ] Document breaking changes in commit message

## Emergency Contacts

If a migration fails in production:
1. Do NOT panic â€” downgrades are supported
2. Check `alembic_version` table: `SELECT * FROM alembic_version;`
3. Run `alembic downgrade -1` to revert
4. Check logs: `docker compose logs api | tail -n 100`
