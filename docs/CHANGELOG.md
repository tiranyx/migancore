# MIGANCORE — CHANGELOG.md

All notable changes to the MiganCore API.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
