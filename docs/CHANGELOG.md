# MIGANCORE — CHANGELOG.md

All notable changes to the MiganCore API.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.3.2] — 2026-05-03 (Day 11 + Day 12)

### Added
- **Tool Policy Taxonomy** (`services/tool_policy.py`)
  - 6-class classification: `read_only`, `write`, `destructive`, `open_world`, `requires_approval`, `sandbox_required`
  - Plan tier enforcement (free/pro/enterprise)
  - Approval gate (hard block for MVP)
  - Sandbox gate (logs warning for audit)
  - Per-tenant, per-tool daily call counters (Redis)
- **Max Agents Enforcement** (`routers/agents.py`)
  - `tenant.max_agents` checked before `db.add(agent)`
  - Applies to both `create_agent` and `spawn_agent`
- **Spawn Depth Limit** (`routers/agents.py`)
  - `MAX_GENERATION_DEPTH = 5`
  - Blocks spawn when `parent.generation + 1 > 5`
- **Persona Lock Enforcement** (`routers/agents.py`)
  - `persona_locked=True` blocks `persona_overrides` during spawn
- **Tenant Message Quota** (`routers/chat.py`)
  - Checks `tenant.messages_today >= tenant.max_messages_per_day`
  - Auto-resets counter at UTC midnight
- **Python REPL Security** (`services/tool_policy.py`)
  - Import blacklist: `os`, `sys`, `subprocess`, `socket`, `urllib`, `pickle`, etc.
  - Pattern matching for `import X`, `from X import`, `__import__('X')`, `import_module('X')`
- **Redis-backed Rate Limiting** (`deps/rate_limit.py`)
  - Switched slowapi from in-memory to `RedisStorage`
  - Hybrid key function: `X-Tenant-ID` header → tenant key, fallback to IP
- **Tool ORM Model** (`models/tool.py`)
  - Full SQLAlchemy 2.0 mapping for `tools` table
  - Fields: `risk_level`, `policy`, `max_calls_per_day`, `scopes_required`
- **Database Migration**: `migrations/011_day11_safety_gates.sql`
  - Idempotent ALTER TABLE for `tools` and `tenants`
  - Updated seed data with policy JSONB
  - Added indexes: `idx_tools_risk_level`, `idx_tools_policy` (GIN)

### Fixed
- **H1** `agents.py`: `max_agents` now enforced (was unlimited)
- **H3** `models/`: `tools` table now has ORM model
- **H5** `deps/rate_limit.py`: In-memory storage replaced with Redis backend
- **C3** `tool_executor.py`: `python_repl` now has import blacklist + policy gate

---

### Added (Day 12 — Qdrant RAG Tier 2)
- **Embedding Service** (`services/embedding.py`) — NEW FILE
  - Model: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (768-dim, Bahasa Indonesia native)
  - Singleton `TextEmbedding` with asyncio.Lock double-checked init — prevents memory leak from multiple loads
  - `embed_text()` offloads ONNX inference to thread pool via `run_in_threadpool`
  - `format_turn_pair()` — "Pengguna:/Asisten:" labels, 300-char truncation per side
  - Pre-warmed at lifespan startup — avoids 35s cold start on first chat request
- **Vector Memory Service** (`services/vector_memory.py`) — NEW FILE
  - Per-agent Qdrant collections: `episodic_{agent_id}`
  - `ensure_collection()` — idempotent, HNSW brute-force for <10k vectors, handles concurrent race
  - `index_turn_pair()` — embed turn pair → upsert PointStruct, asyncio.Semaphore(2) for CPU protection
  - `search_semantic()` — cosine similarity search, score_threshold=0.55, graceful degradation to `[]`
  - AsyncQdrantClient singleton with asyncio.Lock
- **Semantic Memory in Tool Executor** (`services/tool_executor.py`)
  - `_memory_search` now tries Qdrant semantic search first (Tier 2)
  - Falls back to Redis K-V substring search (Tier 1) if Qdrant unavailable or empty
  - Response includes `source` field: `"qdrant_semantic"` or `"redis_kv"`
- **Background Embedding in Chat** (`routers/chat.py`)
  - `asyncio.create_task(index_turn_pair(...))` fires after `db.commit()` — never blocks HTTP response

---

## [0.3.1] — 2026-05-03

### Added
- `POST /v1/agents/{id}/spawn` — Spawn child agent with inherited persona
- `GET /v1/agents/{id}/children` — List direct children of an agent
- New database columns: `template_id`, `persona_locked`, `letta_agent_id`, `webhook_url`, `avg_quality_score`
- Migration script: `migrations/010_day10_schema_sync.sql`
- Agent genealogy tracking: `parent_agent_id` + `generation` inheritance
- Auto-copy of parent tool grants to spawned children
- Comprehensive documentation suite: `MASTER_CONTEXT.md`, `SPRINT_LOG.md`, `CHANGELOG.md`, `FOUNDER_JOURNAL.md`, `QA_REPORT.md`

### Fixed
- ORM ↔ SQL schema mismatch: `description`, `model_version`, `system_prompt` now in init.sql
- Missing SQLAlchemy imports: `Boolean`, `Float` in `models/agent.py`
- Tech debt T2: moved `import secrets` to top-level in `routers/agents.py`
- **E2E Bug:** Stream chat 503 — `AsyncSessionLocal` import moved inside `chat_stream` function
- **Security:** Path traversal in `load_soul_md` — added `resolve()` + base_dir restriction
- **Tech Debt:** Removed 97 lines of dead code `_run_agentic_loop` from `chat.py`

---

## [0.3.0] — 2026-05-03

### Added
- LangGraph `StateGraph` director (`services/director.py`)
  - `reason_node` → `execute_tools_node` → conditional routing
  - Circuit breaker: max 5 tool iterations
  - `reasoning_trace` for observability
- Fallback to plain chat when Ollama tool calling unsupported (404)
- `ChatResponse` now includes `tool_calls_made` count

### Fixed
- `_memory_search` namespace bug: `memory_list()` keyword arg fixed
- `director.py` orphaned code: wired into `chat.py`
- `health_check` version: "0.2.0" → "0.3.0"
- `build_ollama_tools_spec` late import moved to module top-level
- `_get_pool()` race condition: added `asyncio.Lock()` singleton

### Changed
- Sync chat now uses `run_director()` instead of `_run_agentic_loop`

---

## [0.2.0] — 2026-05-02 (Estimated)

### Added
- Tool executor (`services/tool_executor.py`)
  - DuckDuckGo web search
  - `memory_write` / `memory_search`
  - `python_repl` subprocess sandbox
- `build_ollama_tools_spec()` — OpenAI-compatible tool schemas
- ReAct agentic loop in `chat.py`
- `OllamaClient.chat_with_tools()` — native tool calling
- Tool calls persisted in `messages.tool_calls` JSONB column

---

## [0.1.0] — 2026-05-01 (Estimated)

### Added
- Auth system: RS256 JWT, Argon2id, refresh rotation
- Agent CRUD: create, get
- Chat endpoint with SOUL.md injection
- Postgres persistence: conversations, messages
- Redis memory service (Tier 1)
- SSE streaming chat
- Conversation management (list, get, soft delete)
- Rate limiting via slowapi
- Request tracing with structlog
- RLS tenant isolation

---

## [Unreleased / Week 2 Preview]

### Planned
- Letta integration (Day 11)
- Qdrant semantic memory / RAG (Day 12)
- MCP (Model Context Protocol) (Day 13-14)
- Training pipeline v1 (Day 15)
- Model versioning endpoints
- Agent archiving / soft delete
- Max agents enforcement per tenant

---

*Changelog maintained by coding agents. Update after every version bump.*
