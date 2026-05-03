# MIGANCORE — CONTEXT.md (Project RAM)
**Last Updated:** 2026-05-03 | **Last Agent:** Kimi Code CLI (Day 7-9 Audit + Fix)
**API Version:** 0.3.0 (stable, Day 9)
**Git Commit:** `f5c10cd`

> Ini adalah "project RAM" — sumber kebenaran tunggal untuk state proyek saat ini.
> **Setiap agent WAJIB baca ini sebelum mulai kerja. Update setelah setiap sesi.**
> Format: lihat 07_AGENT_PROTOCOL.md untuk panduan lengkap.

---

## CURRENT STATUS

| Field | Value |
|-------|-------|
| Phase | Week 1 → Week 2 transition |
| Sprint Day | Day 10 (COMPLETE) |
| API Version | 0.3.1 |
| VPS | Ubuntu 22.04, 32GB RAM, 8 core, 400GB |
| Stack Status | Postgres ✅ Redis ✅ Qdrant ✅ Ollama ✅ API ✅ |

---

## WORKING COMPONENTS (VERIFIED END-TO-END)

### Auth System (Day 1–5, Kimi)
- ✅ `POST /v1/auth/register` — Argon2id hash, tenant auto-create, scope assignment
- ✅ `POST /v1/auth/login` — RS256 JWT, access (15m) + refresh (7d) token pair
- ✅ `POST /v1/auth/refresh` — atomic token rotation, session family termination
- ✅ `POST /v1/auth/logout` — token revocation
- ✅ `GET /v1/auth/me` — current user info
- ✅ Rate limiting: 5/min login, 10/min register (per IP via slowapi)
- ✅ Audit logging: events ke Postgres (async, no rollback risk)
- ✅ RLS: cross-tenant isolation verified, ado_app non-superuser

### Agent System (Day 6, Kimi + Day 10, Kimi)
- ✅ `POST /v1/agents` — create agent, tenant-scoped
- ✅ `GET /v1/agents/{id}` — get agent by ID
- ✅ `POST /v1/agents/{id}/spawn` — spawn child agent with inherited persona (Day 10)
  - Inherits: `model_version`, `visibility`, `system_prompt`, `description`
  - Persona merge: parent `persona_blob` + `persona_overrides` from request
  - Generation: `parent.generation + 1`
  - Template tracking: `template_id` column (parent's id as fallback)
  - Auto-grants: copies parent's `agent_tool_grants` to child via raw SQL
- ✅ `GET /v1/agents/{id}/children` — list direct children of an agent

### Chat System (Day 6, Kimi + Day 7-9, Claude + Kimi)
- ✅ `POST /v1/agents/{id}/chat` — sync chat via LangGraph director, tool calling, Postgres persistence
  - Rate limited: 30/min per IP
  - Context window: last 5 messages
  - Memory injection: Redis K-V summary injected into system prompt
  - Tool calling: up to MAX_TOOL_ITERATIONS=5 via LangGraph StateGraph
  - Response: `ChatResponse` with `tool_calls_made` + `reasoning_trace`
- ✅ `POST /v1/agents/{id}/chat/stream` — SSE streaming chat (no tool calling)
  - Server-Sent Events format
  - Pre-flight DB ops selesai sebelum streaming mulai
  - Persist assistant message via asyncio.create_task setelah stream selesai
- ✅ `GET /v1/agents/{id}/conversations` — list conversations untuk agent

### Conversation Management (Day 7, Claude)
- ✅ `GET /v1/conversations` — list semua conversations user
- ✅ `GET /v1/conversations/{id}` — get conversation dengan messages
- ✅ `DELETE /v1/conversations/{id}` — soft delete (status → archived)

### Memory Service (Day 7, Claude)
- ✅ `services/memory.py` — Redis K-V memory tier 1
  - `memory_write(tenant_id, agent_id, key, value, namespace)` → Redis SET, 30d TTL
  - `memory_read(tenant_id, agent_id, key, namespace)` → Redis GET
  - `memory_list(tenant_id, agent_id, namespace)` → Redis SCAN
  - `memory_summary(tenant_id, agent_id)` → formatted string untuk system prompt injection
  - Key pattern: `mem:{tenant_id}:{agent_id}:{namespace}:{key}`
  - Race condition fix: `asyncio.Lock()` singleton pool initialization

### Config System (Day 6, Kimi)
- ✅ `config/agents.json` — world.json pattern, declarative agent identities
- ✅ `config/skills.json` — skill registry, MCP-compatible schemas declared
- ✅ `services/config_loader.py` — lru_cache load, get_agent_config, get_skill_config
  - Fallback: jika agent_id tidak exact match, return first `visibility == "public"` (core_brain)

### Tool Executor (Day 8, Claude)
- ✅ `services/tool_executor.py` — dispatcher skill_id → handler
  - `ToolContext(tenant_id, agent_id)` — dataclass untuk context propagation
  - `_web_search` → DuckDuckGo Instant Answers (free, no key, ~20 req/s per IP)
  - `_memory_write` → `services/memory.memory_write()`, delegates Redis K-V
  - `_memory_search` → SCAN all memory + substring match pada key+value
  - `_python_repl` → `subprocess.run` dengan real process isolation, output cap 2000 chars
  - `TOOL_REGISTRY` dict, `ToolExecutor.execute()` menangkap semua error
  - `build_ollama_tools_spec(skill_ids)` → baca skills.json, filter mcp_compatible=True

### LangGraph Director (Day 9, Claude + Kimi)
- ✅ `services/director.py` — LangGraph StateGraph orchestrator
  - `AgentState(TypedDict)`: messages, tools_spec, tool_ctx, model, options, tool_calls, iteration, final_response, reasoning_trace
  - `reason_node` → calls Ollama with tools (fallback ke plain chat on any error)
  - `execute_tools_node` → dispatches tool_calls via ToolExecutor
  - `_route_after_reason` → conditional edge ke execute_tools atau END
  - `run_director()` → public async entry point, returns `(final_response, tool_calls, reasoning_trace)`
  - Circuit breaker: `MAX_TOOL_ITERATIONS=5`
- ✅ Wired ke `POST /v1/agents/{id}/chat` via `routers/chat.py`

### Infrastructure
- ✅ `docker-compose.yml` — semua service dengan profiles
  - default: postgres, redis, qdrant, ollama, api
  - memory: letta (disabled — defer Day 11)
  - workers: celery (disabled — defer Week 4)
  - observability: langfuse (disabled — defer Week 3)
  - ingress: caddy (disabled — nginx aaPanel owns 80/443)
- ✅ `migrations/init.sql` — full schema, letta_db created
- ✅ OllamaClient: timeouts (60s/5s connect/30s read), streaming + tool calling
  - `chat_with_tools()` — stream=False hardcoded (Ollama requirement)
  - STREAM_TIMEOUT: no total limit, 30s per chunk
- ✅ Request tracing: X-Request-ID middleware + structlog context binding

---

## IN PROGRESS / NEXT SPRINT

### Day 10 — Agent Genealogy + Spawning
**Goal:** Agent bisa spawn child agents dengan inherited persona

- [ ] `POST /v1/agents/{id}/spawn` — create child agent
- [ ] parent_agent_id FK di agents table (verified ada di schema)
- [ ] generation counter + persona inheritance dari parent SOUL.md
- [ ] `services/spawner.py` — orchestrate multi-agent graph

---

## BLOCKERS

Tidak ada blocker saat ini.

---

## KNOWN BUGS & TECH DEBT

| ID | Severity | Description | Fix |
|----|----------|-------------|-----|
| H4 | MEDIUM | `.venv` masih di-track git | `git rm -r --cached api/.venv` |
| H2 | LOW | Alembic belum setup, migrations raw SQL | Setup sebelum beta |
| C8 | LOW | JWT key rotation belum ada strategi | Defer sampai user base > 0 |
| T1 | LOW | `models/base.py` punya `get_db()` duplikat dari `deps/db.py` | Hapus, semua router sudah pakai `deps.db.get_db` |
| T2 | LOW | ~~`create_agent` punya bare `import secrets` di dalam function~~ | **FIXED Day 10** — moved to top-level import |
| T3 | INFO | Chat rate limit pakai IP, bukan user_id | Fix Week 2: pakai JWT sub sebagai key |
| O1 | INFO | Ollama `0.22.1` tool calling 404 jika `tools` field dikirim | **RESOLVED** — fallback ke plain chat di `director.py` reason_node. Model `qwen2.5:7b-instruct-q4_K_M` ternyata support tools native. |
| S1 | INFO | Schema mismatch ORM ↔ SQL (`description`, `model_version`, `system_prompt` missing dari init.sql; `letta_agent_id`, `webhook_url`, `avg_quality_score` missing dari ORM) | **FIXED Day 10** — init.sql synced, ORM updated, migration applied to live DB |

---

## ARCHITECTURE DECISIONS (FINAL)

| Decision | Choice | Alasan |
|----------|--------|--------|
| Celery | DISABLED | RAM terlalu mahal untuk seed stage. asyncio.create_task cukup. |
| Letta | DEFERRED (Day 11) | Cold-start complexity tinggi. Redis K-V cukup untuk PoC. |
| Langfuse | DEFERRED (Week 3) | Belum ada yang perlu diobservasi. structlog sudah cukup. |
| Memory Tier 1 | Redis K-V | Fast, simple, TTL built-in, sudah ada di stack |
| Memory Tier 2 | Qdrant semantic (Day 12) | Semantic similarity untuk long-term recall |
| Memory Tier 3 | Letta (Day 11) | Working memory blocks + persona persistence |
| Streaming | SSE via StreamingResponse | Lebih simple dari WebSocket, cukup untuk MVP |
| Tool Protocol | MCP-compatible schemas | Future-proof, declared di skills.json |
| Orchestration | LangGraph (Day 9) | Controllable, stateful, circuit breaker built-in |
| Python REPL sandbox | subprocess.run() | exec() dengan restricted builtins mudah di-escape via __subclasses__(). subprocess = real process boundary |
| Tool calling | stream=False | Ollama native tool calling tidak support streaming. SSE endpoint tidak bisa pakai tool calling. |

---

## WHAT NEXT AGENT SHOULD NOT DO

- ❌ Jangan aktifkan Celery — disabled intentionally, re-enable Week 4
- ❌ Jangan start Letta container — profile:memory, defer Day 11
- ❌ Jangan tambah Langfuse ke default profile — defer Week 3
- ❌ Jangan commit `.venv/` ke git
- ❌ Jangan duplicate `get_db` — pakai `deps.db.get_db` exclusively
- ❌ Jangan pakai `models.base.get_db` di router baru (legacy only)
- ❌ Jangan skip `set_tenant_context` sebelum query tenant-scoped tables

---

## METRICS

| Metric | Value |
|--------|-------|
| API endpoints | 14 (5 auth + 4 agents + 3 chat + 3 conversations) |
| DB tables | 9 (tenants, users, agents, conversations, messages, model_versions, refresh_tokens, audit_events, training_runs) |
| Memory service | Redis K-V, 30d TTL |
| Test coverage | auth (unit) + RLS (integration) |
| Stack services | 5 running (postgres, redis, qdrant, ollama, api) |
| RunPod budget | $0 spent of $50 allocated |

---

## HANDOFF LOG

| Date | Agent | Session Summary |
|------|-------|-----------------|
| 2026-05-?? (Day 0) | Kimi | Buat 8 master docs, schema, architecture, sprint plan |
| 2026-05-?? (Day 1) | Kimi | VPS provisioning, Docker, swap, SSH, JWT keys |
| 2026-05-?? (Day 2) | Kimi | DNS + nginx reverse proxy, SSL self-signed |
| 2026-05-?? (Day 3) | Kimi | Ollama container, Qwen2.5-7B + 0.5B pulled, 7-14 tok/s |
| 2026-05-?? (Day 4) | Kimi | Auth system: RS256, Argon2id, refresh rotation, 5 endpoints |
| 2026-05-?? (Day 5) | Kimi | RLS, cross-tenant tests, audit logging, ado_app non-superuser |
| 2026-05-?? (Day 6) | Kimi | Agent CRUD, chat endpoint, SOUL.md injection, Postgres persistence, config system |
| 2026-05-03 (Day 7) | Claude Sonnet 4.6 | Chat rate limiting, SSE streaming, memory service (Redis K-V), conversation endpoints, OllamaClient streaming support |
| 2026-05-03 (Day 8) | Claude Sonnet 4.6 | Tool executor (web_search/memory_write/memory_search/python_repl), OllamaClient.chat_with_tools(), ReAct agentic loop wired ke chat.py, landing page interactive.jsx updated dengan real ADO event templates |
| 2026-05-03 (Day 7-9) | Kimi Code CLI | Audit Claude Code's Day 7-9 implementation: fixed `_memory_search` namespace bug, wired orphaned `director.py` into `chat.py`, fixed health_check version mismatch, fixed `build_ollama_tools_spec` late import, fixed `_get_pool()` race condition dengan `asyncio.Lock()`, added Ollama 404 fallback di `director.py`. Deployed v0.3.0 ke VPS. E2E verified: register → create agent → chat (sync+stream) → list conversations = ALL PASSED. Tool calling verified: 1 tool call executed successfully. |
| 2026-05-03 (Day 10) | Kimi Code CLI | Schema sync: fixed ORM↔SQL mismatch (added missing columns to init.sql + ORM + live DB migration). Agent spawning: `POST /v1/agents/{id}/spawn` with persona inheritance, generation counter, tool grant copy. `GET /v1/agents/{id}/children` endpoint. Deployed v0.3.1 ke VPS. E2E verified: create parent → spawn child → verify generation/parent_id → list children = ALL PASSED. |
