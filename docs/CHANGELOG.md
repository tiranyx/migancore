# MIGANCORE — CHANGELOG.md

All notable changes to the MiganCore API.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.3.6] — 2026-05-03 (Day 16)

### Added
- **Episodic Context Retrieval** (`services/vector_retrieval.py`) — NEW FILE
  - `retrieve_episodic_context()` — async retrieval from Qdrant with 1.5s timeout guard
  - `format_episodic_context()` — formats retrieved turns as numbered list, sorted by relevance
  - Score threshold: 0.65 (stricter than index 0.55; research: 0.70 English → 0.65 Bahasa Indonesia)
  - Top-k search=5, inject=3 — research: >3 chunks confuses 7B models (Mem0 production, 2025)
  - Sort by relevance descending (NOT recency) — prevents "lost in the middle" degradation
- **Qdrant retrieval wired in chat** (`routers/chat.py`)
  - `retrieve_episodic_context()` called synchronously before `run_director()`
  - `format_episodic_context()` result passed to `_build_system_prompt()`
  - Injected as last section in system prompt (highest attention weight for 7B)
- **`_build_system_prompt()` extended** (`routers/chat.py`)
  - New `episodic_context: str = ""` parameter — backward compatible, empty = no-op
  - Injection order: Persona → Mission → Knowledge → Redis → Qdrant Episodic (Day 16)
- **Score exposed in search results** (`services/vector_memory.py`)
  - `search_semantic()` now accepts `score_threshold` parameter (default: existing 0.55)
  - `_retrieval_score` key added to returned payloads — enables caller-side sorting

### Research Notes (docs/DAY16_RAG_RESEARCH.md)
- Mem0 (arxiv 2504.19413): top-k=3 for 7B models; top-k=10+ overwhelms model
- Lost in the Middle (arxiv 2505.15561): sort by relevance, NOT recency — 30% accuracy drop if recency-sorted
- Zep/LangMem production: score threshold 0.70 English → 0.65 multilingual Bahasa Indonesia
- CRAG/Self-RAG: NOT practical for CPU-only 7B without fine-tuning — skipped
- Format: numbered [N] list with role-per-line outperforms chain-of-thought for 7B
- Separate recency vs relevance: message history (last 5) handles recency; Qdrant handles relevance

### Changed
- Version bumped: `0.3.5` → `0.3.6`

---

## [0.3.5] — 2026-05-03 (Day 15)

### Added
- **Constitutional AI Pipeline** (`services/cai_pipeline.py`) — NEW FILE
  - `run_cai_pipeline()` — fire-and-forget entry point, 50% sampling gate
  - `_critique()` — 7B judge evaluates response vs. 10 Constitution principles, structured JSON output
  - `_revise()` — 7B model generates improved response based on critique (temp=0.3)
  - `_store_preference_pair()` — AsyncSessionLocal INSERT into `preference_pairs` table
  - `JUDGE_MODEL = qwen2.5:7b-instruct-q4_K_M` — research-validated: 0.5B fails on Chat Hard tasks
  - `CAI_SAMPLE_RATE = 0.5` — CPU resource management on CPU-only VPS
  - `CRITIQUE_THRESHOLD = 3` — score ≤ 3 triggers revision + DPO pair storage
- **Constitution** (`docs/CONSTITUTION.md`) — NEW FILE
  - 10 specific, measurable principles (P1–P10): Kejelasan, Relevansi, Akurasi, Proporsi, Kejujuran, Manfaat, Keamanan, Persona Konsisten, Bahasa Adaptif, Anti-Verbosity
  - Each principle has measurable proxies (sentence length, language match, actionable content presence)
  - Scoring scale: 1-5, threshold ≤ 3 → revision required
  - Designed per C3AI (ACM Web 2025) insight: specific + measurable + in-tension principles generate 5x better pairs
- **CAI wired in Chat** (`routers/chat.py`)
  - 3rd `asyncio.create_task` after Qdrant index + Letta knowledge extraction
  - Passes `assistant_msg.id` as `source_message_id` for training data lineage

### Changed
- Version bumped: `0.3.4` → `0.3.5`

### Research Notes (docs/DAY15_CAI_RESEARCH.md)
- Self-Evolving Agents survey: Optimizer was the missing 4th component (arxiv 2508.07407)
- Constitutional AI: self-critique generates preference pairs without human labels (arxiv 2212.08073)
- DPO 2025: 1.9k high-quality pairs × 3 epochs = 5% improvement on 7B models
- LLM-as-Judge: 0.6B fails Chat Hard (<50%), 7B achieves ~75% — 7B required
- Fire-and-forget aligned with production memory systems (Mem0, Letta) → industry standard

---

## [0.3.4] — 2026-05-03 (Day 14)

### Added
- **Fact Extractor Service** (`services/fact_extractor.py`) — NEW FILE
  - `extract_facts()` — calls Qwen2.5-0.5B to extract new user facts from a conversation turn
  - `maybe_update_knowledge_block()` — fire-and-forget wrapper; appends extracted facts to Letta knowledge block
  - `_trim_knowledge_if_needed()` — FIFO section trimming when approaching 4000-char limit
  - Date-sectioned format: `[YYYY-MM-DD]\n- fact1\n- fact2` — human and LLM readable
  - LLM-based deduplication: shows last 500 chars of existing knowledge to avoid re-extraction
  - `EXTRACT_MODEL = "qwen2.5:0.5b"` — fast, low RAM, no resource contention with 7B chat model
- **Knowledge Extraction Wired in Chat** (`routers/chat.py`)
  - After `index_turn_pair` background task, adds `maybe_update_knowledge_block` as second create_task
  - Only fires when `agent.letta_agent_id` is set (no Letta = no-op)
  - Zero latency impact on HTTP response — fully fire-and-forget

### Changed
- Version bumped: `0.3.2` → `0.3.4` in `main.py` (skipped 0.3.3 tag, now matching Day 13 docs)

### Research Notes (docs/DAY14_KNOWLEDGE_EXTRACTION_RESEARCH.md)
- Decision rationale: 0.5B vs 7B for extraction, date-sectioned format, FIFO trim strategy
- Complementary to Qdrant Tier 2: Qdrant = episodic turns, Letta knowledge = semantic user profile
- Scope-out rationale: stream endpoint, mission auto-update, persona evolution deferred

---

## [0.3.3] — 2026-05-03 (Day 13)

### Added
- **Letta Client** (`services/letta.py`) — NEW FILE
  - Singleton `httpx.AsyncClient` with `asyncio.Lock` for thread-safe init
  - `ensure_letta_agent()` — idempotent get-or-create; creates 3 memory blocks:
    `persona` (2000 chars) | `mission` (1000 chars) | `knowledge` (4000 chars)
  - `get_blocks()` — returns `dict[label, value]`, `{}` on any Letta error
  - `update_block()` — PATCH `/memory/block/{label}`, silent fail, never raises
  - `format_persona_block()` — builds structured persona from soul_text + overrides
  - Full graceful degradation: Letta down → chat continues with soul_text fallback
- **Letta wiring in Agent Router** (`routers/agents.py`)
  - `create_agent`: auto-provisions Letta agent after DB commit, saves `letta_agent_id`
  - `spawn_agent`: child agent inherits merged `persona_blob` as Letta persona block
- **Letta block injection in Chat** (`routers/chat.py`)
  - Fetches Letta blocks before building system prompt
  - `persona` block replaces static `soul_text` (Tier 3 > Tier 0 fallback chain)
  - `mission` block injected as `[MISI AKTIF]` section
  - `knowledge` block injected as `[KONTEKS DIKETAHUI]` (only if non-empty)

### Research Notes (docs/DAY13_LETTA_RESEARCH.md)
- Full VPS ecosystem map: MiganCore + Sidix + Mighantech3D + Ixonomic on same VPS
- RunPod serverless: vLLM 80GB (LLM) + mighan-media-worker 48GB (media gen)
- Letta port fix documented: server on 8283, EXPOSE says 8083 (Dockerfile mismatch)
- `/memory` endpoint bug in Letta 0.6.0 documented — use `/memory/block` instead
- RunPod vLLM future-proofing: `LLMConfig.model_endpoint_type: "vllm"` noted for Day 14+

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
