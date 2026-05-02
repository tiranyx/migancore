# Day 4 Code Review & Iteration Items
> **Date:** 2026-05-03
> **Reviewer:** Kimi Code CLI (self-review)
> **Scope:** All code written during Day 4 (auth system, models, JWT, /ready)
> **Status:** 7 findings — 4 critical fixes, 3 improvements

---

## Executive Summary

Day 4 auth system is **functionally working** (all 5 endpoints pass tests) but has **4 issues that must be fixed before production use** and **3 improvements that raise code quality**. None are blocking for Day 5 RLS work, but all should be addressed before any user-facing deployment.

**Recommendation:** Fix critical items now (30 min), proceed to Day 5, address improvements in Week 2.

---

## CRITICAL FINDINGS (Fix Before Production)

### 🔴 C1: Dead Code + Unused Query in Refresh Endpoint

**File:** `api/routers/auth.py`, lines 188-194

**Problem:** Inside the `if rt.is_revoked or rt.is_expired:` block, there is a `SELECT` query that is executed but its result is never used:

```python
# Line 190-194 — DEAD CODE
await db.execute(
    select(RefreshToken)
    .where(RefreshToken.session_family == session_family)
    .where(RefreshToken.revoked_at.is_(None))
)
# Result is NOT assigned to any variable!
```

**Impact:** Wastes a DB round-trip on every revoked token reuse. No functional bug, but inefficient and confusing.

**Fix:** Remove the unused `SELECT`. The `UPDATE` on lines 196-201 is sufficient.

```python
# Remove lines 190-194 entirely. Keep only the UPDATE.
```

**Effort:** 2 minutes

---

### 🔴 C2: Race Condition in Register (Duplicate Email/Slug)

**File:** `api/routers/auth.py`, lines 44-57

**Problem:** The `check email uniqueness → check slug uniqueness → create` sequence is not atomic. Two parallel requests could both pass the checks and insert duplicates. DB has `UNIQUE` constraints so one would fail with `IntegrityError`, but we don't catch it — user gets a 500 instead of a clean 409.

**Impact:** 500 Internal Server Error on race condition instead of clean 409 Conflict.

**Fix:** Wrap creation in `try/except IntegrityError`:

```python
from sqlalchemy.exc import IntegrityError

@router.post("/register", ...)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # ... existing checks ...
    
    try:
        db.add(tenant)
        await db.flush()
        db.add(user)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        # Parse which constraint failed
        if "users_email_key" in str(exc):
            raise HTTPException(409, "Email already registered")
        if "tenants_slug_key" in str(exc):
            raise HTTPException(409, "Tenant slug already taken")
        raise HTTPException(409, "Registration conflict")
    
    # ... token creation ...
```

**Effort:** 10 minutes

---

### 🔴 C3: JWT Key Lazy-Load is Not Startup-Safe

**File:** `api/services/jwt.py`, lines 14-23

**Problem:** `_get_keys()` lazy-loads RSA keys on first token operation. If keys are missing, the API starts successfully but fails on the first auth request. This delays failure detection.

**Impact:** `/ready` returns OK even if JWT keys are missing. First user login explodes.

**Fix:** Load keys in `lifespan` startup:

```python
# main.py lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("migan.startup", message="MiganCore API starting up")
    # Eager-load JWT keys — fail fast if missing
    from services.jwt import _get_keys
    _get_keys()
    yield
    logger.info("migan.shutdown", message="MiganCore API shutting down")
```

**Effort:** 5 minutes

---

### 🔴 C4: Error Messages Leak Internal Details

**File:** `api/routers/auth.py`, line 162-166; `api/deps/auth.py`, line 28-35

**Problem:** Exception details are returned to the client:

```python
detail=f"Invalid token: {exc}"  # Could leak key format, clock skew, etc.
```

**Impact:** Information disclosure. Attacker learns token validation internals.

**Fix:** Generic client message, structured server log:

```python
# Client gets generic message
detail="Invalid or expired token"

# Server logs detail for debugging
logger.warning("auth.token_invalid", error=str(exc), jti=get_token_jti(token))
```

Same pattern for `deps/auth.py` line 31-35.

**Effort:** 10 minutes

---

## IMPROVEMENTS (Address in Week 2)

### 🟡 I1: No Rate Limiting on Auth Endpoints

**File:** `api/routers/auth.py`

**Problem:** `/register` and `/login` have no rate limiting. Brute-force attacks are trivial.

**Fix Options:**
- **Fast:** Redis-backed rate limiter (`slowapi` or custom middleware)
- **Better:** Per-IP limit (5 attempts/minute) + per-email limit (10 attempts/hour)
- **Best:** CAPTCHA after 3 failed attempts

**Effort:** 1-2 hours
**Priority:** High for production, medium for beta

---

### 🟡 I2: audit_events Table Created but Not Used

**File:** `api/routers/auth.py`, `migrations/004_auth_refresh_tokens.sql`

**Problem:** The `audit_events` table exists but no code writes to it. Auth events (login, logout, refresh, session_terminated) should be logged.

**Fix:** Add `log_audit_event()` helper and call it from auth endpoints:

```python
async def log_audit_event(db, event_type, tenant_id, user_id, details=None):
    event = AuditEvent(event_type=event_type, tenant_id=tenant_id, ...)
    db.add(event)
    # Don't await commit — let endpoint commit or use background task
```

**Effort:** 30 minutes
**Priority:** Medium — needed for security compliance

---

### 🟡 I3: Tenant Slug Has No Format Validation

**File:** `api/schemas/auth.py`, line 13

**Problem:** `tenant_slug` accepts any string. Should enforce URL-safe format (`^[a-z0-9-]+$`).

**Fix:**
```python
from pydantic import Field, field_validator

class RegisterRequest(BaseModel):
    # ...
    tenant_slug: str = Field(..., min_length=1, max_length=63)
    
    @field_validator("tenant_slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens")
        return v
```

**Effort:** 5 minutes
**Priority:** Low — data quality issue

---

## MINOR NOTES (Non-blocking)

| # | Note | File | Action |
|---|------|------|--------|
| N1 | `CORS` allows only `app.` and `lab.` domains — add `localhost` for dev | `main.py` | Config via env var |
| N2 | `__init__.py` files are empty — OK for now, but could export public API | Multiple | Add exports later |
| N3 | Docker workers reference `app.celery` which doesn't exist | `docker-compose.yml` | Fix when Celery app created |
| N4 | No Alembic migration runner — manual `psql` used | `migrations/` | Init Alembic in Week 2 |
| N5 | `get_current_user` doesn't set `SET LOCAL app.current_tenant` | `deps/auth.py` | Needed for Day 5 RLS |

---

## Security Posture Assessment

| Control | Status | Notes |
|---------|--------|-------|
| Password hashing (Argon2id) | ✅ Strong | OWASP 2024 compliant |
| JWT signing (RS256) | ✅ Strong | Asymmetric, key rotation ready |
| Token expiry (15 min access) | ✅ Good | Short-lived |
| Refresh rotation | ✅ Good | Session family pattern |
| Session termination on reuse | ✅ Good | Revokes entire family |
| Rate limiting | ❌ Missing | Brute force risk |
| Audit logging | ❌ Missing | Compliance gap |
| Input validation (slug) | ⚠️ Weak | No format check |
| Error message leakage | ⚠️ Medium | Internal details exposed |
| Race condition handling | ⚠️ Medium | 500 on IntegrityError |

**Overall:** Solid B+ for a Day 4 auth system. Fix C1-C4 to reach A-.

---

## Recommended Action Plan

### Option A: Quick Fix Now (Recommended)
Fix C1-C4 in one commit (~30 min), then proceed to Day 5.

### Option B: Deferred
Proceed to Day 5 now, create GitHub issue for C1-C4, fix in Week 2.

**My recommendation: Option A.** The fixes are small and prevent tech debt from accumulating.

---

## Handoff Context for Next Agent

**If you are the next agent reading this:**

1. **Day 4 is functionally complete.** Auth endpoints work. Tests pass.
2. **C1-C4 are known issues** — fix them before Day 5 or mark as Week 2 debt.
3. **Day 5 scope:** RLS enforcement, `SET LOCAL` helper, cross-tenant tests.
4. **Key file to read:** `docs/KIMI_ANALYSIS_AND_PLAN.md` for Day 5-6 plan.
5. **Key decision needed:** Whether to use SQLAlchemy events for `SET LOCAL` or manual helper.
6. **Database state:** Migration 004 applied. `refresh_tokens` and `audit_events` tables exist. `users` and `tenants` have seed data from register test.

---

*Review completed. Ready for iteration or Day 5 handoff.*
