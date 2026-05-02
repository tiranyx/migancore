# Day 4 → Day 5 Gap Analysis
> **Date:** 2026-05-03
> **Status:** Day 4 Complete, Day 5 Ready to Start

---

## What Day 4 Delivered (Solid Foundation)

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| RS256 JWT Auth | ✅ Working | All 5 endpoints tested |
| Argon2id Password Hash | ✅ Working | OWASP 2024 compliant |
| Refresh Token Rotation | ✅ Working | Session family + revocation |
| Real `/ready` Checks | ✅ Working | Postgres, Redis, Qdrant, Ollama |
| Migration 004 Applied | ✅ Applied | refresh_tokens + audit_events tables |
| Code Review Completed | ✅ Done | 4 critical fixes applied |

---

## Gap: What Separates Day 4 from Production-Ready Multi-Tenancy

### Gap 1: RLS Context Not Set in Auth Queries

**Current State:** `get_current_user()` queries the DB directly without `SET LOCAL app.current_tenant`. This means:
- The query works because RLS policies use `current_setting('app.current_tenant')` 
- But `current_setting` will fail with `NULL` if not set
- Currently it "works" because `get_current_user` doesn't hit tenant-scoped tables directly (it queries `users` by UUID primary key)

**Day 5 Fix Needed:**
```python
# deps/db.py — tenant-aware session
async def get_db_with_tenant(tenant_id: str):
    async with AsyncSessionLocal() as session:
        await session.execute(text("SET LOCAL app.current_tenant = :tid"), {"tid": tenant_id})
        yield session
```

All endpoints that query tenant-scoped tables must use this.

### Gap 2: No Cross-Tenant Isolation Tests

**Current State:** We trust RLS policies exist, but we haven't proven they work.

**Day 5 Test Needed:**
```python
# Pseudo-test:
# 1. User A (tenant 1) creates an agent
# 2. User B (tenant 2) queries agents
# 3. Assert: User B sees empty list
# 4. Assert: Direct SQL without SET LOCAL sees nothing
```

### Gap 3: audit_events Table Empty

**Current State:** Table exists, no code writes to it.

**Day 5 or Week 2:** Add `AuditEvent` model and `log_audit_event()` helper. Log at minimum:
- `auth.login`, `auth.logout`, `auth.register`
- `auth.token_revoked` (session family termination)
- `security.suspicious_activity` (reuse revoked token)

### Gap 4: No Alembic Migration Runner

**Current State:** Migrations applied manually via `docker cp` + `psql`.

**Week 2:** Initialize Alembic for proper migration tracking.

### Gap 5: Workers Reference Non-Existent Celery App

**Current State:** `docker-compose.yml` workers reference `app.celery` which doesn't exist.

**Week 2:** Create `api/celery_app.py` when Celery tasks are needed.

---

## Day 5 Implementation Plan (Refined)

### Task 1: Tenant Session Helper (30 min)
- Modify `deps/db.py` to support `SET LOCAL`
- Ensure `get_current_user` sets tenant context
- All future endpoints inherit this automatically

### Task 2: RLS Isolation Tests (45 min)
- Create `api/tests/test_rls.py`
- Test: cross-tenant read blocked
- Test: cross-tenant write blocked
- Test: admin/superuser bypass (if needed)
- Test: pooled connection resets after transaction

### Task 3: Audit Logging Helper (30 min)
- Create `models/audit_event.py`
- Add `log_audit_event()` utility
- Wire into auth endpoints (login, logout, register, refresh, revoked)

### Task 4: Schema Completeness Check (15 min)
- Verify all tenant-scoped tables have RLS
- Verify `tools`, `agent_tool_grants` have policies
- Add missing policies

### Task 5: Documentation (15 min)
- `docs/DAY5_RLS_TEST_RESULTS.md`
- Update `MASTER_HANDOFF.md`

**Total Estimated Time:** ~2.5 hours

---

## Risk Assessment for Day 5

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| RLS `current_setting` fails with NULL | Medium | High | Always set in session helper |
| Cross-tenant leak in join queries | Medium | Critical | Test with real data |
| Performance degradation from RLS | Low | Medium | Monitor query plans |
| Connection pool leaks tenant setting | Low | High | Use `SET LOCAL` (not `SET`) + test |

---

## Decision Log for Day 5

| Decision | Options | Recommendation |
|----------|---------|---------------|
| Tenant context: SQLAlchemy event vs manual helper | Event listener (`before_execute`) vs explicit helper | **Explicit helper** — clearer, easier to debug |
| Audit logs: sync DB write vs Celery background | Immediate vs async queue | **Immediate for now** — Celery not ready yet |
| Superuser bypass: separate role or `BYPASS RLS` | `BYPASS RLS` privilege vs `role='superadmin'` in app | **App-level check** — don't use `BYPASS RLS` (too powerful) |
| Test strategy: pytest in container vs host | Container vs host Python | **Container** — same environment as production |

---

## Ready to Proceed

All blockers cleared. Day 4 is solid. Day 5 scope is well-defined. No research needed — standard engineering.

**Next action:** Implement Task 1 (tenant session helper) → Task 2 (RLS tests) → Task 3 (audit logging) → Task 4 (schema check) → Task 5 (docs).
