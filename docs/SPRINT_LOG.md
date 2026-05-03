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

---

## Week 2: Safety + Intelligence (Days 11–17)

### Day 11 — Safety Gates + Tool Policy
**Agent:** Kimi Code CLI
**Scope:** Security hardening ("Jangan tambah otak sebelum tambah sistem imun")

**Tool Policy Taxonomy (6-class):**
- `read_only` — web_search, memory_search
- `write` — memory_write
- `destructive` — spawn_agent
- `open_world` — web_search, http_get
- `requires_approval` — spawn_agent, python_repl
- `sandbox_required` — python_repl

**Database:**
- Migration `011_day11_safety_gates.sql` applied to live DB
- Added to `tools`: `risk_level`, `policy` (JSONB), `max_calls_per_day`
- Added to `tenants`: `messages_today`, `messages_day_reset`
- Updated seed data with policy assignments

**ORM:**
- Created `models/tool.py` — Tool ORM model
- Updated `models/tenant.py` — added `messages_today`, `messages_day_reset`

**Enforcement:**
- `routers/agents.py`: `max_agents` enforced in `create_agent` and `spawn_agent`
- `routers/agents.py`: `MAX_GENERATION_DEPTH = 5` enforced in spawn
- `routers/agents.py`: `persona_locked` blocks `persona_overrides`
- `services/tool_policy.py`: Policy checker with plan tier, approval, sandbox, and rate limit gates
- `services/tool_executor.py`: Policy check before handler dispatch
- `services/tool_executor.py`: Python REPL import blacklist (`os`, `sys`, `subprocess`, `socket`, etc.)
- `routers/chat.py`: Tenant message quota check (`messages_today >= max_messages_per_day`)
- `deps/rate_limit.py`: Redis-backed slowapi storage (multi-worker safe)

**E2E Test Results:**
- max_agents: blocks at 3/3 ✅
- spawn depth: blocks at gen=6 (max=5) ✅
- persona_lock: blocks overrides when locked ✅
- tool policy: python_repl blocked for free plan (requires enterprise) ✅
- python_repl blacklist: `import os`, `from subprocess`, `__import__` all blocked ✅
- tenant quota: `messages_today` increments correctly ✅

**Version:** 0.3.1 → 0.3.2

**Deliverables:** 6-class tool policy, max_agents enforcement, spawn depth limit, persona lock, Redis rate limiter, Python REPL blacklist, tenant message quota

---

### Day 13 — Letta Tier 3 Persistent Persona Memory
**Agent:** Claude Sonnet 4.6
**Scope:** Persona persistence — agent identity survives across sessions via Letta block storage

**Pre-Implementation Research (documented in DAY13_LETTA_RESEARCH.md):**
- VPS ecosystem audit: Sidix (`/opt/sidix/`), Mighantech3D (`/root/mighantect-3d/`), Ixonomic all on same VPS
- RunPod: `vLLM v2.14.0` (80GB) for LLM inference + `mighan-media-worker` (48GB) for media gen
- Letta probe: listens on 8283 (not 8083 — EXPOSE mismatch), accessible via `http://letta:8283`
- Letta `/memory` endpoint has 500 bug in 0.6.0 — use `/memory/block` instead
- 72 REST endpoints mapped, `memgpt_agent` type selected, block schema confirmed
- `letta-free` embedding avoids need for local embedding model in Letta agents
- RunPod vLLM noted as Day 14+ opportunity: `LLMConfig.model_endpoint_type: "vllm"` ready

**Architecture Decision: Multi-Block (not single persona block):**
- `persona` block (2000 chars) — stable identity, replaces soul_text in system prompt
- `mission` block (1000 chars) — active goals, can evolve per task
- `knowledge` block (4000 chars) — learned facts about owner/context, grows Day 14+
- Separates identity from context → selective updates without corrupting persona

**New Files:**
- `services/letta.py` — LettaClient singleton, `ensure_letta_agent`, `get_blocks`, `update_block`, `format_persona_block`

**Modified Files:**
- `routers/agents.py` — `create_agent` + `spawn_agent` auto-provision Letta agent
- `routers/chat.py` — fetch blocks pre-prompt, inject persona/mission/knowledge

**Deployment & Verification:**
- Bug caught: `docker compose restart` uses old image → must use `docker compose up -d`
- Bug caught: model cache not mounted → re-download on container recreate (35s)
- E2E result: `letta.agent_created` log ✅, `letta_agent_id` in DB ✅, 3 blocks readable ✅
- Chat: Tier 3 → Tier 0 fallback chain verified via `_build_system_prompt` logic

**Version:** 0.3.2 → 0.3.3 (no DB migration — `letta_agent_id` column already exists from Day 10)

**Deliverables:** Tier 3 persistent persona — every MiganCore agent auto-provisions a Letta agent with 3 memory blocks on creation

---

### Day 12 — Qdrant RAG Tier 2 Semantic Memory
**Agent:** Claude Sonnet 4.6
**Scope:** Vector memory — agent ingat konteks percakapan lampau via semantic search

**Research (pre-implementation):**
- Confirmed `paraphrase-multilingual-mpnet-base-v2` over BGE-small-en (English-only) and BAAI/bge-m3 (compatibility issues)
- fastembed ONNX CPU runtime — no GPU, no torch dependency
- Turn-pair chunking (user+assistant together) vs per-message: +2% accuracy per MemMachine research
- HNSW `full_scan_threshold=10000` forces exact brute-force for <10k vectors — faster and more accurate
- Cosine distance correct for mean-pool sentence-transformers
- Score threshold 0.55 — empirical noise floor for multilingual models

**New Files:**
- `services/embedding.py`
  - `MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"` (768-dim)
  - Singleton `TextEmbedding` with asyncio.Lock double-checked init
  - `embed_text()` — offloads ONNX inference to thread pool via `run_in_threadpool`
  - `format_turn_pair()` — Bahasa Indonesia labels, 300-char truncation per side
- `services/vector_memory.py`
  - `ensure_collection()` — idempotent, handles "already exists" race condition
  - `index_turn_pair()` — embed → upsert PointStruct, asyncio.Semaphore(2) guard
  - `search_semantic()` — cosine search, score_threshold=0.55, returns `[]` on any error
  - AsyncQdrantClient singleton with asyncio.Lock

**Modified Files:**
- `main.py` — pre-warm embedding model at lifespan startup (avoids 35s cold start on first chat)
- `routers/chat.py` — `asyncio.create_task(index_turn_pair(...))` after `db.commit()`
- `services/tool_executor.py` — `_memory_search` tries Qdrant first; Redis K-V fallback if unavailable or empty

**Deployment:**
- Git commit `3f22074` pushed and pulled to VPS
- Model download: 5 ONNX files, ~35s first-time load
- `embedding.model_ready` confirmed at 06:24:20 UTC
- `/health` → 200 ✅

**Version:** 0.3.2 (no DB migration required)

**Deliverables:** Tier 2 semantic memory — index + search + graceful degradation to Tier 1 Redis

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
