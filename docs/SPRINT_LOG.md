# MIGANCORE — SPRINT_LOG.md
**Completed Sprint History**

---

## Week 1: Foundation (Days 1–10)

### Day 0 — Project Genesis
**Agent:** Kimi  
**Scope:** Architecture, documentation, planning

- Created 8 master docs: SOUL.md, VISION.md, PRD.md, ARCHITECTURE.md, ERD_SCHEMA.md, SPRINT_ROADMAP.md, AGENT_PROTOCOL.md, RISK_TRAINING_CONTEXT.md
- Defined 30-day sprint plan
- Established coding conventions and agent handoff protocol

**Deliverables:** 8 markdown docs + ADO_MASTER.html

---

### Day 1 — VPS Provisioning
**Agent:** Kimi  
**Scope:** Infrastructure baseline

- Ubuntu 22.04 VPS provisioned (32GB RAM, 8 cores, 400GB)
- Docker + Docker Compose installed
- 32GB swap configured
- SSH key-based auth (sidix_vps_key)
- Basic firewall (ufw)

**Deliverables:** Running VPS, SSH access

---

### Day 2 — DNS + Reverse Proxy
**Agent:** Kimi  
**Scope:** Network edge

- DNS A record: api.migancore.com → 72.62.125.6
- aaPanel nginx reverse proxy configured
- SSL self-signed certificate (temporary)
- Ports 80/443 → 127.0.0.1:18000

**Deliverables:** HTTPS endpoint reachable

---

### Day 3 — Ollama + Models
**Agent:** Kimi  
**Scope:** AI inference layer

- Ollama container deployed via Docker Compose
- Qwen2.5-7B-Instruct-Q4_K_M pulled (~4.7GB)
- Qwen2.5-0.5B pulled (~400MB)
- Benchmark: 7-14 tok/s on 7B model
- GPU not available (CPU inference)

**Deliverables:** Ollama API at `:11434`, 2 models loaded

---

### Day 4 — Auth System Core
**Agent:** Kimi  
**Scope:** Identity + security

- RS256 JWT with 2048-bit RSA keys
- Access token: 15min expiry
- Refresh token: 7-day expiry with atomic rotation
- Argon2id password hashing
- 5 endpoints: register, login, refresh, logout, me
- Rate limiting: 5/min login, 10/min register

**Deliverables:** 5 auth endpoints, JWT keypair, password hashing

---

### Day 5 — RLS + Tenant Isolation
**Agent:** Kimi  
**Scope:** Multi-tenancy security

- PostgreSQL RLS policies on all tenant-scoped tables
- `set_config('app.current_tenant', ...)` pattern
- `ado_app` non-superuser with limited privileges
- Cross-tenant isolation tests (integration)
- Audit logging: async fire-and-forget

**Deliverables:** RLS enforced, audit events, security tests

---

### Day 6 — Agent System + Chat MVP
**Agent:** Kimi  
**Scope:** Digital organism core

- `POST /v1/agents` — create agent
- `GET /v1/agents/{id}` — retrieve agent
- `POST /v1/agents/{id}/chat` — basic chat with Ollama
- SOUL.md injection into system prompt
- Postgres persistence: conversations + messages
- Config system: `agents.json` + `skills.json`
- `config_loader.py` with LRU cache

**Deliverables:** Agent CRUD, chat endpoint, config system

---

### Day 7 — Memory + Streaming + Conversations
**Agent:** Claude Sonnet 4.6  
**Scope:** Memory tier 1 + UX

- Redis K-V memory service (`services/memory.py`)
  - `memory_write`, `memory_read`, `memory_list`, `memory_summary`
  - Key pattern: `mem:{tenant_id}:{agent_id}:{namespace}:{key}`
  - 30-day TTL, singleton pool with asyncio.Lock
- SSE streaming chat (`POST /chat/stream`)
  - Pre-flight DB ops before streaming
  - Background persistence via `asyncio.create_task`
- Conversation management endpoints
  - `GET /v1/conversations` — global list
  - `GET /v1/conversations/{id}` — detail with messages
  - `DELETE /v1/conversations/{id}` — soft archive
- Rate limiting on chat: 30/min sync, 20/min stream

**Deliverables:** Memory service, SSE streaming, 3 conversation endpoints

---

### Day 8 — Tool Executor + ReAct Loop
**Agent:** Claude Sonnet 4.6  
**Scope:** Agent capabilities

- `services/tool_executor.py`
  - DuckDuckGo web search
  - `memory_write` / `memory_search`
  - `python_repl` via subprocess sandbox
  - Structured error handling
- `build_ollama_tools_spec()` — OpenAI-compatible tool schema
- ReAct agentic loop in `chat.py`
  - Max 5 iterations circuit breaker
  - Tool result injection as `role:"tool"`
  - `tool_calls_made` in ChatResponse
- `OllamaClient.chat_with_tools()` — native tool calling

**Deliverables:** 4 tools, ReAct loop, tool persistence

---

### Day 9 — LangGraph Director
**Agent:** Claude Sonnet 4.6 (code) + Kimi (audit + fix)  
**Scope:** Orchestration engine

- `services/director.py` — LangGraph StateGraph
  - `AgentState` TypedDict
  - `reason_node` → `execute_tools_node` → conditional routing
  - Circuit breaker: `MAX_TOOL_ITERATIONS=5`
  - `reasoning_trace` for debugging
- Wired into `chat.py` (replaced `_run_agentic_loop`)
- Fallback: plain chat if tool calling unsupported

**Known Issue:** Ollama 0.22.1 tool calling 404 → fallback works

**Deliverables:** LangGraph director, reasoning trace

---

### Day 10 — Agent Spawning + Schema Sync
**Agent:** Kimi Code CLI  
**Scope:** Genealogy + technical debt

**Schema Sync:**
- Discovered ORM ↔ SQL mismatch (missing columns in both directions)
- Fixed `migrations/init.sql` to match VPS reality
- Added to ORM: `letta_agent_id`, `webhook_url`, `avg_quality_score`, `template_id`, `persona_locked`
- Created `migrations/010_day10_schema_sync.sql`
- Applied migration to live DB

**Spawn Feature:**
- `POST /v1/agents/{id}/spawn` — create child agent
  - Inherits: model_version, visibility, system_prompt, description
  - Persona merge: parent blob + overrides
  - Generation: parent.generation + 1
  - Template tracking: template_id column
  - Auto-grants: copies parent's tool grants
- `GET /v1/agents/{id}/children` — list direct children
- Moved `import secrets` to top-level (tech debt T2)

**Version:** 0.3.0 → 0.3.1

**Deliverables:** Spawn endpoint, children list, schema sync, 5 new columns

---

## Sprint Metrics: Week 1

| Metric | Value |
|--------|-------|
| Days completed | 10/30 |
| Endpoints delivered | 14 |
| Database tables | 20 |
| Lines of code (API) | ~3,500 |
| Commits to main | ~25 |
| E2E tests passed | All critical paths ✅ |
| VPS uptime | 100% |
| Models deployed | 2 (7B + 0.5B) |

---

*Next: Week 2 (Days 11–17) — Letta, Qdrant RAG, MCP, Training Pipeline*
