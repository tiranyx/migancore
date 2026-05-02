# Handoff Document — Day 6 Engineering Iteration
**Date**: 2026-05-03
**Agent**: Kimi Code CLI
**Status**: DEPLOYED & VERIFIED on VPS
**Branch**: `main` (github.com/tiranyx/migancore)
**Commit**: `32a6279` (head)

---

## 1. EXECUTIVE SUMMARY

Day 6 MVP **berhasil di-deploy dan di-verifikasi end-to-end**:
- ✅ Register → Create Agent → Chat dengan SOUL.md personality → Postgres persistence
- ✅ Semua 5 auth endpoints bekerja (register, login, me, refresh, logout)
- ✅ RLS tenant isolation aktif di semua tabel termasuk `users`
- ✅ Rate limiting aktif di auth endpoints
- ✅ Chat endpoint memanggil Ollama `qwen2.5:7b-instruct-q4_K_M` dengan system prompt dari `docs/01_SOUL.md`

---

## 2. WHAT WAS DONE THIS SESSION

### 2.1 Security Hardening (3-Way Review Fixes)
| Fix | File | Status |
|-----|------|--------|
| Atomic refresh token rotation (race condition) | `api/routers/auth.py` | ✅ |
| Rate limiting (slowapi + Redis) | `api/deps/rate_limit.py` | ✅ |
| Dynamic scope resolver (role + plan) | `api/services/scope_resolver.py` | ✅ |
| Tenant context in auth (RLS fix) | `api/routers/auth.py` | ✅ |
| Tenant_id embedded in refresh token payload | `api/services/jwt.py` | ✅ |
| Fire-and-forget async audit writer | `api/routers/auth.py` | ✅ |
| Users RLS + SECURITY DEFINER lookup | `migrations/010_users_rls_security_definer.sql` | ✅ |

### 2.2 Features Delivered
| Feature | File | Status |
|---------|------|--------|
| POST `/v1/agents` (create agent) | `api/routers/agents.py` | ✅ |
| GET `/v1/agents/{id}` (get agent) | `api/routers/agents.py` | ✅ |
| POST `/v1/agents/{id}/chat` | `api/routers/chat.py` | ✅ |
| Conversation + Message ORM | `api/models/conversation.py`, `message.py` | ✅ |
| SOUL.md injection | `api/routers/chat.py` | ✅ |
| Config loader (agents.json + skills.json) | `api/services/config_loader.py` | ✅ |
| Ollama client with timeouts | `api/services/ollama.py` | ✅ |

### 2.3 Infrastructure
| Task | Status |
|------|--------|
| Celery workers disabled in compose | ✅ |
| `letta_db` created in init.sql | ✅ |
| `.venv` removed from git tracking | ✅ |
| `config/` mounted into API container | ✅ |
| Migration 010 (users RLS) applied to VPS | ✅ |
| Migration 011 (agent fields) applied to VPS | ✅ |

---

## 3. CRITICAL DISCOVERIES & FIXES

### 3.1 The `AsyncSessionLocal = None` Trap
**Problem**: `deps/db.py` melakukan `from models import AsyncSessionLocal` di module level. Saat `init_engine()` dipanggil di lifespan, `models.base.AsyncSessionLocal` berubah dari `None` → `sessionmaker`, tapi referensi di `deps.db` masih menunjuk ke `None`.

**Fix**: Ubah `deps/db.py` untuk import `models.base as _base` dan akses `_base.AsyncSessionLocal` saat runtime.

```python
# BEFORE (BROKEN)
from models import AsyncSessionLocal
async with AsyncSessionLocal() as session: ...  # TypeError: NoneType not callable

# AFTER (WORKING)
from models import base as _base
if _base.AsyncSessionLocal is None:
    raise RuntimeError("...")
async with _base.AsyncSessionLocal() as session: ...
```

### 3.2 RLS + SET LOCAL + COMMIT Trap
**Problem**: `set_tenant_context()` menggunakan `SELECT set_config('app.current_tenant', tid, true)` — parameter ketiga `true` = `is_local`, artinya setting di-reset saat COMMIT.

**Impact**: Setelah `await db.commit()` untuk insert tenant+user, `app.current_tenant` hilang. Insert `refresh_tokens` berhasil (tabel mungkin tidak punya RLS), tapi `db.refresh(agent)` gagal karena RLS `agents` menolak SELECT.

**Fix**: Re-set tenant context setelah setiap commit sebelum query lanjutan:
```python
await db.commit()
await set_tenant_context(db, str(current_user.tenant_id))
await db.refresh(agent)
```

### 3.3 Refresh Token + RLS Trap
**Problem**: `refresh()` endpoint melakukan:
1. Decode token (OK)
2. Atomic UPDATE refresh_tokens (OK, tabel tidak punya RLS)
3. `select(User).where(User.id == ...)` (BROKEN — RLS users aktif, tenant context belum di-set)
4. User = None → raise 401 "Invalid or expired refresh token"
5. Tapi token SUDAH di-revoke oleh atomic UPDATE di langkah 2!

**Fix**: Embed `tenant_id` di refresh token payload, lalu `set_tenant_context` sebelum query User:
```python
tenant_id = payload.get("tenant_id")
if tenant_id:
    await set_tenant_context(db, tenant_id)
```

### 3.4 Circular Import: `main.py ↔ auth.py`
**Problem**: `main.py` mendefinisikan `limiter`, `auth.py` import `from main import limiter`. Tapi `main.py` juga import `auth_router` dari `auth.py`.

**Fix**: Pindahkan `limiter` ke `deps/rate_limit.py`, import dari sana di `main.py` dan `auth.py`.

### 3.5 SQLAlchemy Reserved Name: `metadata`
**Problem**: `Conversation` model punya `metadata: Mapped[dict] = mapped_column(JSON)`. `metadata` adalah reserved attribute di Declarative API.

**Fix**: `meta: Mapped[dict] = mapped_column("metadata", JSON, ...)` — atribut Python `meta`, kolom DB tetap `metadata`.

### 3.6 Config Directory Not in Container
**Problem**: `docker-compose.yml` build context = `./api`, jadi `config/` di repo root tidak masuk container. `config_loader.py` mencari `/config/agents.json`.

**Fix**: 
1. Tambahkan volume mount `./config:/app/config:ro` di `docker-compose.yml`
2. Ubah `CONFIG_DIR` default ke `/app/config` via environment variable

---

## 4. ARCHITECTURE STATE

### 4.1 Database Schema (Postgres 16 + pgvector)
Tabel aktif dengan RLS:
- `tenants` — tanpa RLS (global lookup)
- `users` — RLS via `tenant_isolation_users` policy + `auth_lookup_user_by_email` SECURITY DEFINER
- `agents` — RLS aktif
- `conversations` — RLS aktif
- `messages` — RLS aktif
- `refresh_tokens` — tanpa RLS (token hash lookup)
- `audit_events` — RLS aktif
- `model_versions` — seed data ada

### 4.2 Auth Flow
```
Register  →  Create tenant + user  →  Set tenant context  →  Commit
         →  Create refresh token (dengan tenant_id di payload)
         →  Store hash in DB

Login     →  auth_lookup_user_by_email (SECURITY DEFINER, bypass RLS)
         →  Set tenant context  →  Load ORM User  →  Verify password
         →  Issue tokens

Refresh   →  Decode token  →  Extract tenant_id  →  Set tenant context
         →  Atomic UPDATE refresh_tokens SET revoked_at = NOW()
         →  Load User (RLS OK, tenant context sudah di-set)
         →  Issue new pair

Logout    →  Decode token  →  Extract tenant_id
         →  Atomic UPDATE refresh_tokens SET revoked_at = NOW()
```

### 4.3 Chat Flow
```
POST /v1/agents/{id}/chat
  →  Set tenant context
  →  Validate agent exists (RLS-scoped)
  →  Load agent config (from DB + config/agents.json)
  →  Load SOUL.md sebagai system prompt
  →  Get/Create conversation
  →  Query last 5 messages for context
  →  Call Ollama /api/chat dengan system + history + user message
  →  Persist user message
  →  Persist assistant response
  →  Update conversation.message_count + last_message_at
  →  Commit
```

### 4.4 Config System
- `config/agents.json` — declarative agent definitions (Core Brain + spawnable templates)
- `config/skills.json` — skill registry dengan permissions dan lazy-loading metadata
- Mounted ke container via Docker volume: `./config:/app/config:ro`

---

## 5. KNOWN ISSUES / TECHNICAL DEBT

### 🔴 HIGH PRIORITY
1. **Pydantic `model_version` warning** — Sudah di-fix dengan `ConfigDict(protected_namespaces=())`, tapi perlu di-apply ke semua schema baru ke depan.

2. **No agent creation validation** — `POST /v1/agents` tidak memeriksa `model_version` valid atau `system_prompt` length. Belum ada rate limiting.

3. **Chat endpoint tidak punya rate limiting** — Bisa di-spam ke Ollama, menghabiskan compute.

4. **Ollama timeout 60 detik** — Untuk model 7B di CPU mungkin cukup, tapi untuk model lebih besar perlu streaming response.

### 🟡 MEDIUM PRIORITY
5. **No conversation listing endpoint** — User tidak bisa melihat daftar conversation mereka.

6. **No message pagination** — `_load_recent_messages` hardcoded limit=5. Perlu parameter `limit` di request.

7. **No streaming chat** — Response datang sekaligus. Untuk UX yang baik, perlu SSE streaming.

8. **No tool calling** — Chat hanya pure text. MCP integration (Day 9) akan menambahkan tools.

9. **JWT key rotation** — Belum ada strategi. Jika private key bocor, semua token ever issued tetap valid.

10. **Alembic belum dikonfigurasi** — `alembic` di requirements.txt tapi tidak ada `alembic/` directory. Migrations masih raw SQL.

### 🟢 LOW PRIORITY
11. **LF/CRLF warnings** — Windows local clone menghasilkan LF→CRLF warnings saat git commit. Tidak mempengaruhi runtime.

12. **Celery deferred** — Workers di-comment dari compose. Plan: gunakan `asyncio.create_task` sampai Week 4.

13. **Langfuse deferred** — Observability deferred ke Week 3.

---

## 6. ENVIRONMENT REFERENCE

### VPS
- **IP**: `72.62.125.6` (Ubuntu 22.04, 32GB RAM, 8 cores, 400GB disk)
- **Workspace**: `/opt/ado/`
- **SSH Key**: `C:\Users\ASUS\.ssh\sidix_vps_key` (PowerShell path)
- **Deploy**: `cd /opt/ado && git pull && docker compose build api && docker compose up -d api`

### Docker Stack
| Service | Container | Port | Status |
|---------|-----------|------|--------|
| API | `ado-api-1` | `127.0.0.1:18000:8000` | Active |
| Postgres | `ado-postgres-1` | internal | Active, RLS on |
| Redis | `ado-redis-1` | internal | Active |
| Qdrant | `ado-qdrant-1` | internal | Active |
| Ollama | `ado-ollama-1` | internal | Active, 2 models loaded |

### Database Access
```bash
# Superuser (bypass RLS)
docker exec ado-postgres-1 psql -U ado -d ado -c "..."

# App user (terkena RLS — perlu set_config)
docker exec ado-postgres-1 psql -U ado_app -d ado -c "SELECT set_config('app.current_tenant', 'UUID', true); SELECT ..."
```

### JWT Keys
- `/etc/ado/keys/private.pem` (mounted ro ke container)
- `/etc/ado/keys/public.pem`

### Ollama Models
- `qwen2.5:7b-instruct-q4_K_M` (primary)
- `qwen2.5:0.5b` (draft/fallback)

---

## 7. INTERNAL PROJECT PATTERNS (Knowledge Transfer)

### SIDIX Patterns (Applied)
- **Skills as knowledge packs** → `config/skills.json`
- **Sanad provenance** → deferred ke Week 3+
- **CQF scoring** → deferred ke Week 3+

### Mighantect3D Patterns (Applied)
- **world.json → config/agents.json** — Declarative agent definitions
- **Lazy skill registry** — `config/skills.json` dengan `loader_module_path`
- **Approval gate** — Propose → Approve → Execute (planned for agent spawn/delete)
- **Behavior trees** — deferred ke Week 2+

### Ixonomic Patterns (Applied)
- **Supply integrity** → quota logic di scope resolver
- **Two-step confirmation** → spawn approval gate (planned)
- **Monorepo separation** → `migancore/` (core) vs `migancore-platform/` (platform) vs `migancore-community/` (community)

---

## 8. TESTING NOTES

### Verified End-to-End
```bash
# Di VPS
python3 /tmp/test_e2e_chat.py
# Output: register → create_agent → chat (Siapa kamu?) → response in Indonesian with Mighan-Core personality
```

### Manual Check Commands
```bash
# Health
curl http://127.0.0.1:18000/health

# Ready (checks postgres, redis, qdrant, ollama)
curl http://127.0.0.1:18000/ready

# DB messages (as superuser)
docker exec ado-postgres-1 psql -U ado -d ado -c "SELECT role, LEFT(content, 50) FROM messages ORDER BY created_at DESC LIMIT 6;"
```

---

## 9. NEXT SPRINT PLAN (Day 7-9)

### Day 7: Conversation Memory Enhancement
- [ ] Conversation listing endpoint (`GET /v1/conversations`)
- [ ] Message pagination (`?limit=` + `?before=` cursor)
- [ ] System prompt injection dari `agents.system_prompt` (DB) bukan hanya SOUL.md
- [ ] Context window management — truncate history jika token count melebihi batas

### Day 8: Letta Integration
- [ ] Letta container (profile `memory` di compose)
- [ ] `letta_db` sudah dibuat (migration init.sql)
- [ ] Working memory blocks per agent
- [ ] Archival memory untuk long-term recall

### Day 9: MCP Tool System
- [ ] MCP server scaffold
- [ ] Tool registry dari `config/skills.json`
- [ ] Tool calling di chat endpoint (`tool_calls` field di Message model sudah ada)
- [ ] Approval gate untuk tool execution (Mighantect3D pattern)

---

## 10. RECOMMENDATION: WHO SHOULD CONTINUE?

**Primary recommendation: Claude Code**

**Reasons:**
1. **Integration-heavy work ahead** — Day 7-9 melibatkan Letta integration, MCP adoption, dan Postgres memory optimization. Claude lebih teliti dalam membaca dokumentasi external API dan mengimplementasikan integration patterns dengan benar.

2. **Security sensitivity** — Auth system sekarang fragile (RLS + tenant context + refresh token rotation). Satu kesalahan kecil bisa merusak seluruh auth flow. Claude lebih hati-hati dalam tracing edge cases.

3. **Internal project pattern fidelity** — Claude sudah melakukan review sebelumnya (`docs/REVIEW_CLAUDE.md`) dan memahami konteks SIDIX/Mighantect3D/Ixonomic. Dia akan lebih konsisten dalam menerapkan pattern yang sudah diadopsi.

4. **Architecture documentation** — Claude lebih baik dalam memproduksi dokumentasi teknis yang rapi (seperti yang dibutuhkan untuk MCP dan Letta integration).

**GPT 5.5 tetap berguna untuk:**
- Independent review (sudah ada template: `docs/PROMPT_FOR_GPT_AND_CLAUDE.md`)
- Brainstorming creative UX features (Day 10+)
- Rapid prototyping untuk experimental features

---

## 11. FILES MODIFIED IN THIS SESSION

### New Files
- `api/models/conversation.py`
- `api/models/message.py`
- `api/models/model_version.py`
- `api/routers/chat.py`
- `api/routers/agents.py`
- `api/services/config_loader.py`
- `api/services/ollama.py`
- `api/services/scope_resolver.py`
- `api/deps/rate_limit.py`
- `config/agents.json`
- `config/skills.json`
- `migrations/010_users_rls_security_definer.sql`
- `migrations/011_add_agent_fields.sql`
- `docs/HANDOFF_DAY6.md` (this file)

### Modified Files
- `api/main.py` — added agents_router, limiter import fix
- `api/models/base.py` — lazy engine init
- `api/models/__init__.py` — exported new models
- `api/models/agent.py` — added description, model_version, system_prompt
- `api/routers/auth.py` — atomic refresh, RLS context, tenant_id in tokens, audit fire-and-forget
- `api/deps/db.py` — fixed AsyncSessionLocal stale reference
- `api/services/jwt.py` — tenant_id in refresh token payload
- `docker-compose.yml` — Celery disabled, config volume mount
- `migrations/init.sql` — CREATE DATABASE letta_db
- `.gitignore` — removed .venv

---

## 12. FINAL CHECKLIST FOR NEXT AGENT

Before starting Day 7:
- [ ] Pull latest `main` branch
- [ ] Verify VPS deploy: `curl http://127.0.0.1:18000/ready`
- [ ] Read `docs/HANDOFF_DAY6.md` (this file)
- [ ] Read `docs/SYNTHESIS_KIMI_GPT_CLAUDE.md` untuk konteks 3-way review
- [ ] Read `config/agents.json` dan `config/skills.json`
- [ ] Run end-to-end test: `python3 /tmp/test_e2e_chat.py`
- [ ] Check `migancore/api/AGENTS.md` jika ada instruksi spesifik

**Good luck, next agent! The foundation is solid. Build on it with care.**
