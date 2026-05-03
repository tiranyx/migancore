# MIGANCORE — MASTER_CONTEXT.md
**The Living Document — Single Source of Truth**

**Last Updated:** 2026-05-03  
**Current Version:** 0.3.1  
**Git Commit:** `1ee6ca4`  
**Maintainer:** Every agent MUST update this after each session.

> This document is the "project RAM." It is designed to be read by coding agents in a single pass to understand the full state of the project. If you are picking up this project, **read this first**.

---

## 1. PROJECT ESSENCE

| Field | Value |
|-------|-------|
| **Name** | MiganCore — Autonomous Digital Organism |
| **Tagline** | Every vision deserves a digital organism. |
| **Phase** | Week 1 Complete → Week 2 Transition |
| **Sprint** | Day 10 of 30 |
| **Status** | ✅ MVP Stable, Deployed, Tool-Calling Verified |
| **VPS** | 72.62.125.6 (Ubuntu 22.04, 32GB RAM, 8 cores, 400GB) |
| **Domain** | api.migancore.com (nginx reverse proxy, SSL) |

### Vision (from 01_SOUL.md)
MiganCore is not a chatbot. It is the substrate upon which a civilization of digital agents is built. Each agent is a self-contained organism with memory, tools, lineage, and the ability to spawn children. The system evolves continuously through interaction, training, and genealogical inheritance.

### Core Values
1. **Truth Over Comfort** — Agents tell the truth even when inconvenient
2. **Action Over Advice** — Agents execute, not just suggest
3. **Memory Is Sacred** — Every interaction is remembered and shapes future behavior
4. **Frugality of Compute** — Resources are precious; waste is a bug

---

## 2. ARCHITECTURE SNAPSHOT

```
┌─────────────────────────────────────────────────────────────┐
│                      NGINX (aaPanel)                        │
│                  SSL + Reverse Proxy                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              MiganCore API (FastAPI) v0.3.1                 │
│              Port 127.0.0.1:18000 → 8000                   │
│                                                             │
│  Routers:  auth | agents | chat | conversations            │
│  Services: director | tool_executor | memory | config      │
│  Models:   User | Tenant | Agent | Conversation | Message  │
└──────┬─────────────────┬─────────────────┬──────────────────┘
       │                 │                 │
┌──────▼──────┐ ┌────────▼────────┐ ┌─────▼──────┐
│  Postgres   │ │     Redis       │ │  Qdrant    │
│  16 + pgV   │ │   (Memory T1)   │ │  (Vector)  │
└─────────────┘ └─────────────────┘ └────────────┘
                       │
              ┌────────▼────────┐
              │     Ollama      │
              │  qwen2.5:7b     │
              │  qwen2.5:0.5b   │
              └─────────────────┘
```

### Service Matrix

| Service | Container | Status | Port | Notes |
|---------|-----------|--------|------|-------|
| API | `ado-api` | ✅ Running | 127.0.0.1:18000 | FastAPI + uvicorn |
| Postgres | `ado-postgres` | ✅ Running | 5432 | pgvector, RLS enabled |
| Redis | `ado-redis` | ✅ Running | 6379 | Tier 1 memory, 30d TTL |
| Qdrant | `ado-qdrant` | ✅ Running | 6333 | Semantic vectors (Day 12) |
| Ollama | `ado-ollama` | ✅ Running | 11434 | qwen2.5:7b-instruct-q4_K_M |
| Letta | — | ⏸️ Disabled | — | Defer Day 11 |
| Celery | — | ⏸️ Disabled | — | Defer Week 4 |
| Caddy | — | ⏸️ Disabled | — | Nginx handles SSL |

---

## 3. ENDPOINT INVENTORY (v0.3.1)

### Auth (`/v1/auth`)
| Method | Endpoint | Status | Rate Limit |
|--------|----------|--------|------------|
| POST | `/register` | ✅ | 10/min |
| POST | `/login` | ✅ | 5/min |
| POST | `/refresh` | ✅ | 10/min |
| POST | `/logout` | ✅ | — |
| GET | `/me` | ✅ | — |

### Agents (`/v1/agents`)
| Method | Endpoint | Status | Notes |
|--------|----------|--------|-------|
| POST | `/` | ✅ | Create agent |
| GET | `/{id}` | ✅ | Get agent |
| POST | `/{id}/spawn` | ✅ | **Day 10** — Spawn child with inheritance |
| GET | `/{id}/children` | ✅ | **Day 10** — List direct children |

### Chat (`/v1/agents/{id}`)
| Method | Endpoint | Status | Notes |
|--------|----------|--------|-------|
| POST | `/chat` | ✅ | Sync chat + tool calling via LangGraph |
| POST | `/chat/stream` | ✅ | SSE streaming (no tools) |
| GET | `/conversations` | ✅ | List agent conversations |

### Conversations (`/v1/conversations`)
| Method | Endpoint | Status | Notes |
|--------|----------|--------|-------|
| GET | `/` | ✅ | List all user conversations |
| GET | `/{id}` | ✅ | Get conversation + messages |
| DELETE | `/{id}` | ✅ | Soft archive |

### System
| Method | Endpoint | Status |
|--------|----------|--------|
| GET | `/health` | ✅ |
| GET | `/ready` | ✅ |

**Total: 14 endpoints**

---

## 4. DATABASE SCHEMA

### Key Tables

#### `agents` (The Digital Organisms)
| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `id` | UUID PK | gen_random | Unique identifier |
| `tenant_id` | UUID FK | — | Multi-tenancy |
| `owner_user_id` | UUID FK | — | Creator |
| `parent_agent_id` | UUID FK | NULL | Genealogy |
| `name` | VARCHAR(255) | — | Display name |
| `slug` | VARCHAR(63) | — | URL-safe ID |
| `description` | VARCHAR(1024) | NULL | Bio |
| `generation` | INTEGER | 0 | Lineage depth |
| `model_version` | VARCHAR(64) | qwen2.5:7b | Ollama model |
| `system_prompt` | TEXT | NULL | Custom prompt |
| `persona_blob` | JSONB | `{}` | Mutable traits |
| `persona_locked` | BOOLEAN | false | Immutable flag |
| `template_id` | VARCHAR(64) | NULL | Source template |
| `visibility` | VARCHAR(16) | private | private/tenant/public |
| `status` | active/paused/archived | active | Lifecycle |

#### Other Tables
- `tenants` — Multi-tenancy root
- `users` — Auth + roles (owner/admin/member/readonly)
- `conversations` — Chat sessions
- `messages` — Individual messages + tool_calls JSONB
- `refresh_tokens` — JWT rotation
- `audit_events` — Security audit trail
- `model_versions` — Model lineage
- `tools` — Tool registry
- `agent_tool_grants` — Junction: agent ↔ tool permissions

### RLS Policy
```sql
POLICY "tenant_isolation_agents"
  USING (tenant_id = current_setting('app.current_tenant')::uuid)
```
Every tenant-scoped query MUST call `set_tenant_context(db, tenant_id)` before querying.

---

## 5. CODE PATTERNS (Agent Onboarding)

### Router Pattern
```python
router = APIRouter(prefix="/v1/agents", tags=["agents"])

@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: CreateAgentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await set_tenant_context(db, str(current_user.tenant_id))
    # ... logic ...
    await db.commit()
    await set_tenant_context(db, str(current_user.tenant_id))  # Re-set after commit!
    await db.refresh(agent)
    return AgentResponse(...)
```

### Service Pattern
```python
async def some_service(db: AsyncSession, tenant_id: uuid.UUID, ...):
    # Accept db session as arg — caller manages transaction
    # Never create your own session inside a service
```

### Model Pattern (SQLAlchemy 2.0)
```python
class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
```

### Critical Rules
1. **Always** `await set_tenant_context(db, tid)` before tenant-scoped queries
2. **Always** re-set tenant context after `await db.commit()`
3. **Never** create new `AsyncSession` inside services — pass `db` as arg
4. **Never** skip `ConfigDict(protected_namespaces=())` on Pydantic models
5. **Always** use `uuid.UUID(string_id)` when comparing with `Mapped[uuid.UUID]`

---

## 6. CONFIGURATION SYSTEM

### `config/agents.json`
Declarative agent identities. Key fields:
- `id`, `name`, `role`, `soul_md_path`
- `model_version`, `memory_blocks`, `default_tools`
- `persona_locked`, `visibility`, `generation`, `parent_agent_id`
- `persona_overrides` (voice, tone, values, anti_patterns)

Fallback logic: `get_agent_config(agent_id)` returns first public agent if no exact match.

### `config/skills.json`
Declarative skill registry. Key fields:
- `id`, `name`, `description`, `handler` (builtin)
- `mcp_compatible` — only `true` skills are exposed to Ollama
- `schema` — JSON Schema for parameters
- `permissions`, `requires_approval`, `npc_assignable`

### Environment Variables
| Var | Default | Description |
|-----|---------|-------------|
| `DATABASE_URL` | postgresql+asyncpg://... | Postgres DSN |
| `REDIS_URL` | redis://... | Redis DSN |
| `QDRANT_URL` | http://qdrant:6333 | Vector DB |
| `OLLAMA_URL` | http://ollama:11434 | LLM inference |
| `JWT_PRIVATE_KEY_PATH` | /etc/ado/keys/private.pem | RS256 private key |
| `ENVIRONMENT` | production | dev/staging/prod |

---

## 7. TECH DEBT REGISTER

| ID | Severity | File | Issue | Fix Plan |
|----|----------|------|-------|----------|
| H4 | **HIGH** | git | `.venv` tracked in git | `git rm -r --cached api/.venv` |
| D1 | **MEDIUM** | `chat.py` | `_run_agentic_loop` is dead code (replaced by director) | Remove function (lines 444-540) |
| D2 | **MEDIUM** | `chat.py` | `ChatResponse` missing `reasoning_trace` field | Add to schema + return from endpoint |
| D3 | **MEDIUM** | `agents.py` | No `max_agents` enforcement from `tenants` table | Add count check before create/spawn |
| D4 | **MEDIUM** | `agents.py` | No soft-delete endpoint for agents | Add `DELETE /v1/agents/{id}` |
| D5 | **LOW** | `models/` | `tools` and `agent_tool_grants` have no ORM models | Add when tool CRUD needed (Week 2) |
| D6 | **LOW** | `config.py` | `ENVIRONMENT` pattern may not work with Pydantic v2 | Verify + fix if needed |
| D7 | **LOW** | `memory.py` | `memory_list` has no limit enforcement | Add limit param + respect `_MAX_MEMORY_ITEMS` |
| H2 | **LOW** | `migrations/` | No Alembic — raw SQL migrations only | Setup Alembic before beta |
| C8 | **LOW** | `services/jwt.py` | No key rotation strategy | Defer until user base > 0 |
| T3 | **INFO** | `chat.py` | Rate limit uses IP, not JWT `sub` | Fix Week 2 |
| T1 | **INFO** | `models/base.py` | Duplicate `get_db()` vs `deps/db.py` | Remove from base.py |

---

## 8. DEPLOYMENT CHECKLIST

When deploying changes:
1. `git commit && git push` to `main`
2. SSH to VPS: `cd /opt/ado && git pull`
3. If schema changed: run `migrations/NNN_*.sql` via `psql -U ado -d ado -f file.sql`
4. `docker compose build api && docker compose up -d api`
5. Verify: `docker compose ps` + `curl http://127.0.0.1:18000/health`
6. Run E2E test script
7. Update this document

---

## 9. TROUBLESHOOTING

### "Ollama HTTP error: 404"
- Model name mismatch. Check `ollama list` on VPS. Exact match required.
- Fallback to plain chat exists in `director.py` but 404 from model not found will still fail.

### "must be owner of table"
- Run migrations as `ado` (superuser), not `ado_app`.

### Container keeps restarting
- Check logs: `docker compose logs --tail=30 api`
- Common cause: missing import (e.g. `Boolean`, `Float` in models)

### SSE stream not working
- Verify `X-Accel-Buffering: no` header is set
- Nginx may buffer — check `proxy_buffering off;`

---

## 10. WEEK 2 ROADMAP (3-Agent Consensus)

Deep research completed by Kimi + GPT-5.5 + Claude Code. Full details in `WEEK2_SYNTHESIS.md`.

| Day | Feature | Priority | Approach | Complexity |
|-----|---------|----------|----------|------------|
| 11 | **Safety Gate + Tool Policy** | 🔴 P0 | 6-class tool policy, approval gates, spawn limits | Medium |
| 12 | **Qdrant RAG Tier 2** | 🟡 P1 | Turn-pair chunking + paraphrase-multilingual-mpnet | Medium |
| 13 | **Letta Tier 3 Memory** | 🟡 P1 | Passive storage only (blocks.retrieve/update) | Medium |
| 14 | **MCP Adapter** | 🟡 P1 | Expose 3 tools, consume external via Streamable HTTP | Medium |
| 15-17 | **Data Ledger** | 🟢 P2 | Auto-collect chat logs, user feedback, PII scrubber | Medium |

### Key Decisions (3-Agent Consensus)
- **Safety First:** Tool policy framework before any new features (GPT-5.5: "jangan tambah otak sebelum sistem imun")
- **Letta:** Passive storage ONLY — don't invoke agents.messages.create() (Claude: Q4 model below Letta threshold)
- **Chunking:** Turn-pair (user+assistant) not per-message (Claude)
- **Embedding:** paraphrase-multilingual-mpnet-base-v2 (Claude: bge-m3 buggy, BGE English-only)
- **MCP Transport:** Streamable HTTP (NOT legacy HTTP+SSE) — spec 2025-03-26 (GPT-5.5)
- **Training:** Data ledger dulu, DPO nanti. Min 500 pairs before training (GPT-5.5)
- **Training Cost:** RunPod RTX 4090 Community Cloud $0.34/hr, 500 pairs × 3 epochs = $0.10 (Claude)
- **Training Method:** DPO (not GRPO) — GRPO for reasoning, DPO for chat alignment (Claude)

---

## 11. DOCUMENT INVENTORY

| Document | Purpose | Update Frequency |
|----------|---------|------------------|
| `MASTER_CONTEXT.md` | Living project RAM | Every session |
| `SPRINT_LOG.md` | Completed sprint history | End of each day |
| `CHANGELOG.md` | Version history | Every release |
| `FOUNDER_JOURNAL.md` | Strategic decisions | As needed |
| `QA_REPORT.md` | Audit findings | After major changes |
| `WEEK2_RESEARCH.md` | Deep research for upcoming work | Before sprint |
| `WEEK2_SYNTHESIS.md` | Consolidated research (Kimi + GPT-5.5 + Claude) | After research complete |
| `AGENT_PROMPTS.md` | Prompt templates for multi-agent research | As needed |

---

*End of MASTER_CONTEXT.md — Last updated by Kimi Code CLI, Day 10+Research*
