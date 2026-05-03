# MIGANCORE — CONTEXT.md (Project RAM)
**Last Updated:** 2026-05-04 | **Last Agent:** Claude Opus 4.7 (Day 27 — API Keys + migan CLI + MCP Resources + TTS + Memory Pruning)
**API Version:** 0.4.5
**Git Commit:** `ff80996`

> Ini adalah "project RAM" — sumber kebenaran tunggal untuk state proyek saat ini.
> **Setiap agent WAJIB baca ini sebelum mulai kerja. Update setelah setiap sesi.**
> Jika ada konflik antara CONTEXT.md dan kode: **percayai kode, update CONTEXT.md**.
>
> Dokumen pendukung: `MASTER_CONTEXT.md` | `SPRINT_LOG.md` | `CHANGELOG.md` | `HANDOFF_DAY11_KIMI_TO_CLAUDE.md`

---

## CURRENT STATUS

| Field | Value |
|-------|-------|
| Phase | Week 3 — Distribution Layer + Production Polish |
| Sprint Day | Day 27 (COMPLETE) → Day 28 (Admin Dashboard + Handoff NEXT) |
| API Version | 0.4.5 |
| Git Commit | `ff80996` |
| Tool Catalog | 10 tools: web_search, python_repl, memory_*, spawn_agent, http_get, generate_image, read_file, write_file, **text_to_speech** (Day 27) |
| **MCP Server** | ✅ **LIVE** at `https://api.migancore.com/mcp/` — 8 tools + 4 resources |
| **API Keys** | ✅ `mgn_live_*` long-lived (Day 27) — replaces 15-min JWT for headless clients |
| **`migan` CLI** | ✅ one-line installer (`scripts/migan-setup.sh`/`.ps1`) |
| Episodic Filter | ✅ tool-error responses skip Qdrant indexing (Day 26) |
| Memory Pruner | ✅ daily daemon — points >30d AND importance<0.7 deleted (Day 27) |
| External APIs | fal.ai $9.99 · ElevenLabs free tier ready (key not set yet) |
| VPS | Ubuntu 22.04, 32GB RAM, 8 core, 400GB |
| External URL | **https://api.migancore.com** (API) · **https://app.migancore.com** (Chat UI) |
| Stack Status | Postgres ✅ Redis ✅ **Qdrant v1.12.0** ✅ Ollama ✅ API ✅ Letta ✅ (running, not yet wired) |

---

## WORKING COMPONENTS (VERIFIED END-TO-END)

### Auth System (Day 1–5, Kimi)
- ✅ `POST /v1/auth/register` — Argon2id hash, tenant auto-create, scope assignment
- ✅ `POST /v1/auth/login` — RS256 JWT, access (15m) + refresh (7d) token pair
- ✅ `POST /v1/auth/refresh` — atomic token rotation, session family termination
- ✅ `POST /v1/auth/logout` — token revocation
- ✅ `GET /v1/auth/me` — current user info
- ✅ Rate limiting: 5/min login, 10/min register
- ✅ Audit logging: events ke Postgres (async, no rollback risk)
- ✅ RLS: cross-tenant isolation verified, ado_app non-superuser

### Agent System (Day 6 + Day 10–11)
- ✅ `POST /v1/agents` — create agent, tenant-scoped + **max_agents enforcement** (Day 11)
- ✅ `GET /v1/agents/{id}` — get agent by ID
- ✅ `POST /v1/agents/{id}/spawn` — spawn child agent dengan:
  - Inherited: model_version, visibility, system_prompt, description
  - Persona merge: parent persona_blob + persona_overrides
  - Generation: parent.generation + 1
  - **MAX_GENERATION_DEPTH=5** (Day 11)
  - **persona_locked gate** — blok overrides jika parent locked (Day 11)
  - **max_agents enforcement** juga berlaku untuk spawn (Day 11)
- ✅ `GET /v1/agents/{id}/children` — list direct children

### Chat System (Day 6–11 + Day 20)
- ✅ `POST /v1/agents/{id}/chat` — sync chat via LangGraph director
  - Rate limited: 30/min per IP
  - **Context management (Day 20):** `MAX_HISTORY_LOAD=10`, token budget `MAX_HISTORY_TOKENS=1500`, per-message cap `MAX_MSG_CONTENT_CHARS=800`, `CHARS_PER_TOKEN=3.5`
  - **Explicit `num_ctx=4096`** in all Ollama call options (Day 20)
  - Memory injection: Redis K-V summary injected ke system prompt
  - Tool calling: MAX_TOOL_ITERATIONS=5 via LangGraph StateGraph
  - **Tenant message quota check** (Day 11): max_messages_per_day, auto-reset UTC midnight
  - **Tool policy enforcement** via ToolPolicyChecker (Day 11)
  - Response: `ChatResponse` dengan `tool_calls_made` + `reasoning_trace`
- ✅ `POST /v1/agents/{id}/chat/stream` — SSE streaming (no tool calling) — also `num_ctx=4096`
- ✅ `GET /v1/agents/{id}/conversations` — list conversations

### Conversation Management (Day 7, Claude)
- ✅ `GET /v1/conversations` — list semua conversations user
- ✅ `GET /v1/conversations/{id}` — get conversation dengan messages
- ✅ `DELETE /v1/conversations/{id}` — soft delete (status → archived)

### Safety Gates (Day 11, Kimi)
- ✅ `services/tool_policy.py` — 6-class tool policy taxonomy:
  - `read_only` | `write` | `destructive` | `open_world` | `requires_approval` | `sandbox_required`
  - Plan tier enforcement (free/pro/enterprise)
  - Approval gate (hard block)
  - Sandbox gate (log warning)
  - Per-tenant per-tool daily counters (Redis)
- ✅ Python REPL import blacklist: os, sys, subprocess, socket, urllib, pickle, ctypes...
- ✅ `deps/rate_limit.py` — RedisStorage backend (multi-worker safe), hybrid key (tenant-id → IP fallback)
- ✅ `models/tool.py` — Tool ORM model (risk_level, policy JSONB, max_calls_per_day)
- ✅ `migrations/011_day11_safety_gates.sql` — applied to live DB

### Letta Tier 3 — Persona Block Persistence (Day 13, Claude)
- ✅ `services/letta.py` — LettaClient singleton (httpx.AsyncClient)
  - `ensure_letta_agent()` — get-or-create Letta agent with 3 memory blocks
  - `get_blocks()` — `dict[label → value]`, returns `{}` on error (graceful degradation)
  - `update_block()` — PATCH `/memory/block/{label}`, silent fail
  - `format_persona_block()` — structured persona from soul_text + overrides
- ✅ `routers/agents.py` — `create_agent` + `spawn_agent` auto-provision Letta agent
  - Saves `letta_agent_id` to `agents` table after creation
  - Spawn: child inherits merged `persona_blob` as Letta persona block
- ✅ `routers/chat.py` — fetch blocks before prompt build; Tier 3 > Tier 0 fallback
  - `persona` block replaces soul_text if Letta available
  - `mission` + `knowledge` blocks injected as context sections
- ✅ Letta container: `ado-letta-1`, port 8283 internal, `letta_db` fully migrated
- ✅ E2E verified: 3 blocks created, `letta_agent_id` persisted, logs confirmed

### Admin Monitoring + Synthetic Generator (Day 17 + Day 19, Claude)
- ✅ `routers/admin.py` — admin endpoints, X-Admin-Key auth
  - `GET /v1/admin/stats` — pair count, unused, avg score, distribution, 24h/7d rate, training readiness
  - `GET /v1/admin/preference-pairs` — paginated listing with `score_max`, `unused_only` filters
  - `GET /v1/admin/export` — JSONL stream in Unsloth/TRL DPO-compatible format (prompt/chosen/rejected)
  - **`POST /v1/admin/synthetic/start`** — trigger synthetic generation run, returns run_id (Day 19)
  - **`GET /v1/admin/synthetic/status`** — Redis counters: status/total/processed/stored/progress_pct (Day 19)
  - **`POST /v1/admin/synthetic/stop`** — cancel running task (409 if already running) (Day 19)
  - Auth: X-Admin-Key header → `settings.ADMIN_SECRET_KEY` (503 unconfigured, 401 wrong)
  - Training readiness thresholds: not_ready <500 | approaching 500-999 | ready 1000+ | ideal 2000+
- ✅ `services/synthetic_pipeline.py` — synthetic DPO generator (Day 19, NEW)
  - `start_synthetic_generation()` — creates asyncio.Task, one-at-a-time (asyncio.Lock)
  - `run_synthetic_generation()` — generates initial response (T=0.7) → CAI critique → revise if ≤3 → store
  - `get_synthetic_status()` / `stop_synthetic_generation()` — status + cancellation
  - Redis keys: `synthetic:status/run_id/total/processed/stored/started_at`
  - source_method="synthetic_seed_v1" — distinguishes from real user pairs
- ✅ `services/seed_bank.py` — 120 diverse seed messages (Day 19, NEW)
  - 7 domains: Creative/Research/SEO/Social/Design/Ops/General AI
  - Triple-Source: MighanTech3D NPCs + SIDIX taxonomy (framing only!) + SynPO patterns
- ✅ `models/preference_pair.py` — PreferencePair SQLAlchemy ORM model
- ✅ `config.py` — `ADMIN_SECRET_KEY` setting (env var)
- ✅ **E2E verified (Day 19):** Synthetic start → run_id ✅ status: running/total:120 ✅ processed=1/stored=1 ✅ DB: source_method=synthetic_seed_v1 ✅

### Episodic Context Retrieval — Qdrant RAG (Day 16, Claude)
- ✅ `services/vector_retrieval.py` — semantic retrieval + formatter, NEW FILE
  - `retrieve_episodic_context()` — asyncio.wait_for(1.5s), graceful [] on failure
  - `format_episodic_context()` — numbered list [N], sorted by relevance desc, 150/200 char truncation
  - Score threshold: 0.65 (stricter than index 0.55; Bahasa Indonesia multilingual calibration)
  - Top-k search=5 → inject TOP_K_INJECT=3 (research: >3 confuses 7B models)
- ✅ `routers/chat.py` — Qdrant retrieval wired synchronously BEFORE run_director()
  - `episodic_context` injected as LAST section of system prompt (max attention weight)
  - `_build_system_prompt()` extended: `episodic_context: str = ""` parameter (backward-compat)
- ✅ `services/vector_memory.py` — `search_semantic()` upgraded
  - New `score_threshold` parameter (default: 0.55, overridable)
  - `_retrieval_score` key added to payloads for caller-side sorting

### Constitutional AI Pipeline — Preference Data (Day 15, Claude)
- ✅ `services/cai_pipeline.py` — Constitutional AI critique-revise, fire-and-forget
  - `run_cai_pipeline()` — entry point, 50% sampling gate (`CAI_SAMPLE_RATE=0.5`)
  - `_critique()` — 7B judge evaluates response vs. 10 Constitution principles, structured JSON `{score, violations, suggestions}`
  - `_revise()` — 7B generates improved response (temp=0.3) when score ≤ 3
  - `_store_preference_pair()` — INSERT into `preference_pairs` (no RLS, global training table)
  - `JUDGE_MODEL = qwen2.5:7b-instruct-q4_K_M` — research: 0.5B fails Chat Hard tasks
  - `CRITIQUE_THRESHOLD = 3` — score ≤ 3 triggers revision + pair storage
- ✅ `docs/CONSTITUTION.md` — 10 specific, measurable principles (P1–P10)
- ✅ `routers/chat.py` — CAI wired as 3rd `asyncio.create_task` after chat commit
  - Passes `assistant_msg.id` as `source_message_id` (FK to messages table — training lineage)
  - Zero latency impact — fully fire-and-forget

### Knowledge Block Auto-Extraction (Day 14, Claude)
- ✅ `services/fact_extractor.py` — Ollama 0.5B fact extraction, fire-and-forget
  - `extract_facts()` — structured extraction prompt, output validation (bullet lines only)
  - `maybe_update_knowledge_block()` — appends date-sectioned facts to Letta knowledge block
  - `_trim_knowledge_if_needed()` — FIFO section trim at 3600-char threshold
  - Format: `[YYYY-MM-DD]\n- fact1\n- fact2` — date-sectioned, LLM-readable
  - Dedup: shows last 500 chars of existing knowledge to avoid re-extraction
- ✅ `routers/chat.py` — knowledge extraction wired as second `asyncio.create_task` after chat commit
  - Only fires when `agent.letta_agent_id` is set
  - Zero latency impact — fully fire-and-forget

### Memory Service (Day 7, Claude)
- ✅ `services/memory.py` — Redis K-V Tier 1
  - Key pattern: `mem:{tenant_id}:{agent_id}:{namespace}:{key}`, 30d TTL
  - `memory_write` / `memory_read` / `memory_list` / `memory_summary`

### Qdrant RAG — Semantic Memory Tier 2 Hybrid (Day 12 + Day 18, Claude)
- ✅ `services/embedding.py` — fastembed CPU inference wrapper (Day 12 + **Day 18 upgrade**)
  - Dense model: `paraphrase-multilingual-mpnet-base-v2` (768-dim, Bahasa Indonesia native)
  - **Sparse model (Day 18):** `Qdrant/bm42-all-minilm-l6-v2-attentions` (BM42, keyword recall)
  - Both models pre-warmed at lifespan startup (step 3 dense, step 4 sparse)
  - BM42: `embed_sparse_document()` for indexing, `embed_sparse_query()` for queries (DIFFERENT)
  - `format_turn_pair()` — Bahasa Indonesia labels, 300-char truncation per side
- ✅ `services/vector_memory.py` — Qdrant hybrid CRUD per agent (Day 18 full rewrite)
  - Per-agent collections: `episodic_{agent_id}` — **hybrid schema** (named dense + sparse)
  - `_is_hybrid_collection()` — detect old vs new schema for auto-migration
  - `_create_hybrid_collection()` — `vectors_config={"dense": VectorParams(768, COSINE)}` + `sparse_vectors_config={"sparse": SparseVectorParams}`
  - `_migrate_collection_to_hybrid()` — zero-loss: scroll all → delete → recreate → re-upsert with BM42
  - `_search_hybrid()` — Prefetch dense (score_threshold) + Prefetch sparse (no threshold) → `FusionQuery(RRF)`
  - `_search_dense_only()` — legacy fallback via `client.search()` for old Qdrant or failures
  - `ensure_collection()` — idempotent, auto-detects old schema, auto-migrates on first access
  - `index_turn_pair()` — `asyncio.gather(embed_text, embed_sparse_document)` concurrent; `has_sparse` in payload
  - `search_semantic()` — hybrid first → dense fallback → `[]` graceful degradation
- ✅ `routers/chat.py` — background index after message save
  - `asyncio.create_task(index_turn_pair(...))` — fire-and-forget, never blocks response
- ✅ `services/tool_executor.py` — `_memory_search` upgraded: Qdrant first → Redis fallback
  - **Day 20:** `asyncio.wait_for(timeout=2.0)` around Qdrant call — prevents tool loop blocking
  - Returns `source: "qdrant_hybrid"` or `"redis_kv"` (label corrected from stale "qdrant_semantic")
  - Each result now includes `"score": r.get("_retrieval_score")` for transparency
- ✅ **7 existing collections auto-migrated** to hybrid schema on first API restart (zero data loss)

### Tool Executor (Day 8, Claude + Day 11 + Day 12 update)
- ✅ `services/tool_executor.py`
  - `ToolContext(tenant_id, agent_id, tenant_plan, tool_policies)` — diperluas Day 11
  - `_web_search` → DuckDuckGo Instant Answers
  - `_memory_write` → Redis K-V
  - `_memory_search` → **Qdrant semantic (Tier 2) → Redis K-V fallback (Tier 1)** (Day 12)
  - `_python_repl` → subprocess.run + import blacklist + policy check
  - Policy check via `ToolPolicyChecker.check()` sebelum dispatch

### LangGraph Director (Day 9, Claude + Kimi)
- ✅ `services/director.py` — StateGraph: reason_node → execute_tools_node
  - Circuit breaker: MAX_TOOL_ITERATIONS=5
  - Fallback: plain chat jika tool calling unsupported

### Infrastructure
- ✅ Docker Compose `/opt/ado/docker-compose.yml`:
  - **Running**: postgres, redis, qdrant, ollama, api
  - **Running (unintegrated)**: letta 0.6.0 (port 8083) — scheduled Day 13
  - **Disabled**: celery (Week 4), langfuse (Week 3), caddy (nginx handles 80/443)
- ✅ nginx aaPanel: `https://api.migancore.com` → port 18000 (Let's Encrypt SSL)
- ✅ OllamaClient: timeouts, streaming, tool calling (stream=False hardcoded)
- ✅ Request tracing: X-Request-ID + structlog

---

## IN PROGRESS / NEXT SPRINT

### ✅ Day 22 — Chat UI + app.migancore.com (COMPLETE)
**Git Commit:** `a8538d5` | **Deployed:** 2026-05-03 | **Version:** 0.4.1 (no API change)

**Delivered:**
- ✅ `frontend/chat.html` — Standalone React 18 Chat UI (single HTML file, no build step)
  - Dark sci-fi design: `--bg-0: #07100e`, Orbitron + Inter + JetBrains Mono fonts
  - Boot sequence animation (sessionStorage guard — skip after first visit)
  - Login/Register screen (tabs) — auto-generates tenant_slug from name
  - Auto-create agent on first login (stored in localStorage)
  - SSE streaming chat: `type: start/chunk/done/error` handling
  - Stop button during streaming (AbortController)
  - Conversation persistence in localStorage (last 60 messages)
  - Conversation history sidebar (last 20 conversations saved)
  - Logout with full localStorage clear
  - Responsive: sidebar hidden on mobile
- ✅ `docs/USER_GUIDE.md` — Complete user guide + credentials reference (private to Fahmi)
- ✅ `docs/nginx_app_migancore.conf` — nginx config for `app.migancore.com`
- ✅ **DEPLOYED** to VPS at `https://app.migancore.com` (Let's Encrypt SSL ✅)
  - nginx vhost: `/www/server/panel/vhost/nginx/app.migancore.com.conf`
  - Static files: `/opt/ado/frontend/`
  - HTTP 200 verified · SSL valid · 40KB · HTTP→HTTPS redirect ✅

**E2E verified:**
- `https://app.migancore.com/` → 200, `<title>MiganCore — Chat</title>` ✅
- HTTP 301 → HTTPS redirect ✅
- DNS resolving: `app.migancore.com → 72.62.125.6` ✅

---

### ✅ Day 21 — Auto-rerun Synthetic Generation (COMPLETE)
**Git Commit:** `2ef988d` | **Deployed:** 2026-05-03 | **Version:** 0.4.1

**Delivered:**
- ✅ `services/synthetic_pipeline.py` — multi-round loop: `run_synthetic_generation(run_id, auto_target)`, `_count_synthetic_pairs()` DB helper, new Redis keys (round/cumulative_stored/target_pairs), zero_yield safety abort, `done_target_reached` status
- ✅ `routers/admin.py` — `SyntheticStartRequest` body with `target_pairs`, `POST /start` returns `mode` + `target_pairs`, `GET /status` now includes round/cumulative_stored/target_pairs
- ✅ `main.py` — version 0.4.0 → 0.4.1

**E2E verified:**
- `POST /synthetic/start {"target_pairs": 1000}` → `mode: auto_rerun` ✅
- `GET /synthetic/status` → `round: 1, target_pairs: 1000, is_running: true` ✅
- Auto-rerun task running in VPS background ✅

**Architecture decisions locked:**
- DB count (not in-memory) for target check → restart-safe across container deploys
- `source_method LIKE 'synthetic%'` → counts all synthetic sources including future ones
- zero_yield_abort → Ollama failure detection without infinite loop
- `done_target_reached` status → distinguishable from single-run `done`

---

### ✅ Day 20 — Context Window Management + Tool Executor Timeout (COMPLETE)
**Git Commit:** `74e86e7` | **Deployed:** 2026-05-03 | **Version:** 0.4.0

**Delivered:**
- ✅ `services/tool_executor.py` — `asyncio.wait_for(timeout=2.0)` on Qdrant `memory_search` call; graceful Redis fallback; corrected source label "qdrant_hybrid"; added score field to results
- ✅ `routers/chat.py` — token budget trimming (`_estimate_tokens`, `_trim_history_to_budget`), `MAX_HISTORY_LOAD=10`, per-message 800-char cap, `num_ctx=4096` in all Ollama options
- ✅ `services/director.py` — explicit `num_ctx=4096` in default options dict
- ✅ `main.py` — version 0.3.9 → 0.4.0

**E2E verified:**
- `/health version: 0.4.0` ✅
- Sync chat with `num_ctx=4096` confirmed via Ollama call ✅
- memory_search timeout path verified ✅

**Architecture decisions locked:**
- `num_ctx=4096` everywhere — never leave unset (silent overflow risk)
- `MAX_MSG_CONTENT_CHARS=800` — per-message cap prevents budget hogging
- `MAX_HISTORY_TOKENS=1500` — history budget within 4096 total context
- `CHARS_PER_TOKEN=3.5` — conservative mixed-language estimate (no tokenizer dependency)
- Qdrant timeout 2.0s in tool executor (vs 1.5s in retrieval.py — tool path has Redis fallback)

---

### ✅ Day 19 — Synthetic DPO Generator (COMPLETE)
**Git Commits:** `a9a7b65`, `471e34b` | **Deployed:** 2026-05-03 | **Version:** 0.3.9

**Delivered:**
- ✅ `services/seed_bank.py` (NEW) — 120 diverse seed messages across 7 domains (Triple-Source architecture)
- ✅ `services/synthetic_pipeline.py` (NEW) — full generate→critique→revise pipeline with Redis tracking
- ✅ `routers/admin.py` — 3 new endpoints: /synthetic/start, /status, /stop
- ✅ `services/cai_pipeline.py` — `_store_preference_pair()` now accepts `source_method` param + nullable `source_message_id`

**E2E verified:**
- Synthetic generation started (run_id=3f49eb65) ✅
- First seed processed and stored: `source_method=synthetic_seed_v1, score=3` ✅
- Redis tracking working: status/total/processed/stored all updating ✅
- Generation running in background (120 seeds, ~2-4 hours on CPU-only VPS) ✅

**Architecture decisions locked:**
- One synthetic run at a time: `asyncio.Lock` prevents concurrent runs (CPU-only constraint)
- SIDIX content NOT used as seeds: only topic taxonomy framing patterns (hallucination transfer risk)
- source_method="synthetic_seed_v1": distinguishes from real CAI pairs for training provenance
- CAI filter gate: only score ≤3 pairs stored (expected 40-50% yield from 120 seeds = 50-60 pairs)

### ✅ Day 18 — Hybrid Search BM42 + RRF Fusion (COMPLETE)
**Git Commit:** `f8779ea` | **Deployed:** 2026-05-03 | **Version:** 0.3.8

**Delivered:**
- ✅ `docker-compose.yml` — Qdrant v1.9.0 → v1.12.0 + `fastembed_cache` named volume
- ✅ `services/embedding.py` — BM42 sparse model: `get_sparse_model`, `embed_sparse_document`, `embed_sparse_query`
- ✅ `services/vector_memory.py` — full hybrid rewrite: schema detection, zero-loss migration, hybrid RRF search, graceful degradation chain
- ✅ `main.py` — BM42 pre-warm at startup step 4

**Key findings:**
- Qdrant Query API (Prefetch + FusionQuery.RRF) requires ≥ v1.10.0 — v1.9.0 NOT supported
- BM42 MUST use `query_embed()` for queries (not `embed()`) — different token weighting
- Zero-loss migration works because `chunk_text` was stored in payload since Day 12
- Named volume `fastembed_cache` = instant BM42 reload (108,100 it/s vs 4s re-download)

**Architecture decisions locked:**
- Hybrid search: dense (threshold=0.55) + BM42 sparse (no threshold, different score range) + RRF
- Auto-migration: old schema detected → migrated transparently on first `ensure_collection()` call
- BM42 is OPTIONAL: graceful degradation to dense-only if unavailable (never crash)

### ✅ Day 17 — Admin Monitoring + CAI Visibility (COMPLETE)
**Git Commit:** `fac8e9a` | **Deployed:** 2026-05-03 | **Version:** 0.3.7

**Delivered:**
- ✅ `routers/admin.py` — 3 endpoints: /stats, /preference-pairs, /export (JSONL)
- ✅ `models/preference_pair.py` — PreferencePair ORM model registered in models/__init__.py
- ✅ `config.py` — ADMIN_SECRET_KEY setting
- ✅ `docker-compose.yml` — ADMIN_SECRET_KEY env wired to API container

**Research findings (Day 17 research agent, arxiv 2025-2026):**
- SimPO > DPO for first run: noise-tolerant, no reference model, +6.4pts AlpacaEval 2
- Minimum: 500 pairs any signal / 1000 reliable / 2000 ideal (arxiv 2502.14560)
- RunPod cost: ~$2-4 per 7B QLoRA run (RTX 4090, 2hr)
- HyDE/query rewriting: SKIP — CPU latency too high on 7B
- Hybrid search BM42: good ROI → planned Day 18

**Architecture decisions locked:**
- Training algorithm: SimPO (not DPO) for first run — see ARCHITECTURE DECISIONS
- Admin endpoints: READ ONLY — never mutate training data
- Export format: Unsloth/TRL-compatible JSONL (prompt/chosen/rejected)

### ✅ Day 16 — Episodic RAG Retrieval (COMPLETE)
**Git Commit:** `4eaa610` | **Deployed:** 2026-05-03 | **Version:** 0.3.6

**Delivered:**
- ✅ `services/vector_retrieval.py` — retrieve_episodic_context() + format_episodic_context()
- ✅ `routers/chat.py` — synchronous Qdrant retrieval before run_director(), injected last in system prompt
- ✅ `services/vector_memory.py` — score_threshold param + _retrieval_score in payload
- ✅ `docker-compose.yml` — Qdrant ulimits nofile 1024→65536 (RocksDB Too many open files fix)

**Architecture decisions locked:**
- Score threshold 0.65 (not 0.55) — research shows 0.65 is optimal for Bahasa Indonesia on multilingual MPNet
- Top-k: search=5, inject=3 — Mem0 production finding: >3 chunks confuses 7B models
- Sort by relevance (not recency) — "lost in the middle" research: recency-sorted degrades 30%
- Synchronous (not background) — retrieval result needed BEFORE Ollama inference
- Inject LAST in system prompt — primacy attention bias exploitation for 7B models
- Separate recency vs relevance concerns: history=last 5 turns, Qdrant=semantic match

---

### ✅ Day 15 — Constitutional AI Pipeline (COMPLETE)
**Git Commit:** `TBD` | **Deployed:** 2026-05-03 | **Version:** 0.3.5

**Delivered:**
- ✅ `docs/CONSTITUTION.md` — 10 specific, measurable principles (P1 Kejelasan → P10 Anti-Verbosity)
- ✅ `services/cai_pipeline.py` — critique + revise + store preference pair, fire-and-forget
- ✅ `routers/chat.py` — 3rd asyncio.create_task wired: `run_cai_pipeline()`

**Architecture decisions locked:**
- JUDGE_MODEL = `qwen2.5:7b` (NOT 0.5B) — 0.5B fails on Chat Hard quality assessment
- CAI_SAMPLE_RATE = 0.5 — CPU resource management on CPU-only VPS
- CRITIQUE_THRESHOLD = 3 — only revise clearly suboptimal (score ≤ 3/5)
- Preference pairs: chosen=revised, rejected=original — DPO training signal
- No RLS on preference_pairs — global training table, not tenant-scoped

---

### ✅ Day 14 — Knowledge Block Auto-Extraction (COMPLETE)
**Git Commit:** `26c399f` | **Deployed:** 2026-05-03 | **Version:** 0.3.4

**Delivered:**
- ✅ `services/fact_extractor.py` — Qwen2.5-0.5B extraction, date-sectioned format, FIFO trim
- ✅ `routers/chat.py` — fire-and-forget `asyncio.create_task(maybe_update_knowledge_block(...))`

**Architecture decisions locked:**
- EXTRACT_MODEL = `qwen2.5:0.5b` (not 7B) — avoids CPU resource contention, extraction is simple structured task
- Scope: sync chat ONLY — stream endpoint deferred (assistant message persists async there)
- knowledge block ONLY — persona and mission remain manually managed
- FIFO trim threshold: 3600 chars → section pop → hard cap at 4000

---

### ✅ Day 13 — Letta Tier 3 Persona Memory (COMPLETE)
**Git Commit:** `df47884` | **Deployed:** 2026-05-03 06:58 UTC | **Version:** 0.3.3

**Delivered:**
- ✅ `services/letta.py` — LettaClient singleton (httpx.AsyncClient), multi-block architecture
  - `ensure_letta_agent()` — idempotent get-or-create, 3 blocks: `persona`/`mission`/`knowledge`
  - `get_blocks()` — fetch all blocks → `dict[label, value]`, graceful degradation
  - `update_block()` — PATCH by label, silent fail on error
  - `format_persona_block()` — soul_text + overrides → structured Bahasa persona text
- ✅ `routers/agents.py` — `create_agent` + `spawn_agent` auto-provision Letta agent, save `letta_agent_id`
- ✅ `routers/chat.py` — fetch Letta blocks before prompt build; Tier 3 persona overrides Tier 0 soul_text
- ✅ E2E verified: `letta.agent_created` log ✅, `letta_agent_id` in DB ✅, 3 blocks readable ✅

**Architecture decisions locked:**
- `memgpt_agent` type with `llm_config` → Ollama (ready to switch to RunPod vLLM Day 14+)
- `letta-free` embedding (Letta hosted) — no local embedding needed for block storage
- NEVER call `/v1/agents/{id}/messages` — Letta as storage only
- `/memory/block` endpoint used (not `/memory` — has Letta 0.6.0 bug returning 500)

### ✅ Day 12 — Qdrant RAG Tier 2 (COMPLETE)
**Git Commit:** `3f22074` | **Deployed:** 2026-05-03 06:24:20 UTC | **Model load:** 35s

**Delivered:**
- ✅ `services/embedding.py` — fastembed singleton, `paraphrase-multilingual-mpnet-base-v2`, thread-pool offload
- ✅ `services/vector_memory.py` — `ensure_collection`, `index_turn_pair`, `search_semantic`
- ✅ `routers/chat.py` — fire-and-forget background embed via `asyncio.create_task`
- ✅ `services/tool_executor.py` — `_memory_search` Qdrant-first with Redis fallback
- ✅ `main.py` — model pre-warm at lifespan startup

**Architecture decisions locked:**
- `paraphrase-multilingual-mpnet-base-v2` (768-dim, Bahasa Indonesia native, ONNX CPU)
- `fastembed==0.5.0` — no `lazy_load` param
- HNSW `full_scan_threshold=10000` — brute-force exact search for small collections
- Score threshold 0.55 — noise filter
- Semaphore(2) — limits concurrent CPU embed ops

### Day 13 — Letta Tier 3 (PASSIVE STORAGE ONLY)
**CRITICAL CONSTRAINT:** Qwen2.5-7B Q4 tidak cukup untuk Letta tool calls.
Letta HANYA boleh digunakan sebagai storage (blocks.retrieve / blocks.update).
JANGAN invoke `agents.messages.create()`.

Letta sudah running di port 8083. Next: wire ke API untuk persona block persistence.

---

## BLOCKERS

Tidak ada blocker saat ini.

---

## KNOWN BUGS & TECH DEBT

| ID | Severity | Description | Fix |
|----|----------|-------------|-----|
| Q1 | FIXED (Day 16) | Qdrant "Too many open files" — RocksDB colpai 1024 fd limit saat create collection | `ulimits.nofile: 65536` di docker-compose.yml |
| H4 | MEDIUM | `.venv` masih di-track git | `git rm -r --cached api/.venv` + `.gitignore` |
| H2 | LOW | Alembic belum setup, migrations raw SQL | Setup sebelum beta |
| H6 | LOW | `agent_tool_grants` tidak ada ORM model | Buat `models/agent_tool_grant.py` |
| C2 | LOW | `reasoning_trace` tidak ada di `ChatResponse` schema | Add field ke `schemas/chat.py` |
| C8 | LOW | JWT key rotation belum ada strategi | Defer sampai user base > 0 |
| T1 | LOW | `models/base.py` punya `get_db()` duplikat dari `deps/db.py` | Hapus dari base.py |
| M1 | INFO | Chat rate limit pakai IP, bukan JWT sub | Fix: pakai `request.state.user_id` |
| M4 | INFO | `_get_director()` global state potensial race condition | Add threading.Lock() |

---

## ARCHITECTURE DECISIONS (FINAL)

| Decision | Choice | Alasan |
|----------|--------|--------|
| Celery | DISABLED | RAM terlalu mahal untuk seed stage. asyncio.create_task cukup. |
| Letta | PASSIVE STORAGE ONLY | Qwen2.5-7B Q4 tidak support Letta tool calls. Use blocks API only. |
| Knowledge extraction | Qwen2.5-0.5B | Fast, low RAM, structured output task — no need for 7B |
| CAI judge model | Qwen2.5-7B | Research (arxiv 2509.13332): 0.5B fails Chat Hard (<50% accuracy), 7B achieves ~75% |
| CAI sampling | 50% of turns | CPU resource management — critique + revise = 2 sequential 7B calls |
| Training algorithm | SimPO (NOT DPO) for first run | Noise-tolerant, no reference model, +6.4pts AlpacaEval 2 (arxiv 2405.14734) — CAI pairs will have label noise |
| DPO pipeline | Accumulate pairs now, train Week 3-4 | RunPod RTX 4090, $2-4/run; need 1000+ pairs minimum (arxiv 2502.14560) |
| Synthetic seed source | MighanTech3D NPCs + SIDIX taxonomy (framing only) | Realistic archetypes + diverse framing; no hallucination transfer |
| Synthetic generation cadence | Re-run /synthetic/start as needed | Each run adds ~50-60 pairs; stop/start anytime |
| `num_ctx` | 4096 (explicit) at all Ollama call sites | Ollama default ~2048 causes silent truncation on long chats |
| Context history budget | MAX_HISTORY_TOKENS=1500, MAX_MSG_CONTENT_CHARS=800 | Leaves room for system prompt + response within 4096 |
| Qdrant timeout (tool executor) | 2.0s asyncio.wait_for → Redis fallback | Tool loop must not block; Redis is immediate fallback |
| Knowledge scope | Sync chat only | Stream endpoint: async persist pattern makes nested task complex. Defer. |
| Langfuse | DEFERRED (Week 3) | Belum ada yang perlu diobservasi. structlog sudah cukup. |
| Memory Tier 1 | Redis K-V | Fast, simple, TTL built-in |
| Memory Tier 2 | Qdrant + fastembed (Day 12) | Semantic similarity, multilingual |
| Memory Tier 3 | Letta blocks (Day 13) | Persona persistence only |
| Embedding model | paraphrase-multilingual-mpnet-base-v2 | Bahasa Indonesia native, 768-dim |
| Sparse model | Qdrant/bm42-all-minilm-l6-v2-attentions | +30-50% recall for proper nouns/names/dates |
| Hybrid fusion | RRF (Reciprocal Rank Fusion) | Best known fusion method; Qdrant native |
| BM42 degradation | Optional — dense-only fallback | Never crash search if BM42 unavailable |
| MCP Transport | Streamable HTTP (spec 2025-03-26) | BUKAN HTTP+SSE (deprecated) |
| Training | DPO | Data ledger dulu (min 500 pairs), RunPod RTX 4090 $0.34/hr |
| Streaming | SSE via StreamingResponse | Simple, cukup untuk MVP |
| Tool Protocol | MCP-compatible schemas | Future-proof, declared di skills.json |
| Orchestration | LangGraph StateGraph | Controllable, stateful, circuit breaker |
| Python REPL sandbox | subprocess.run + import blacklist | subprocess = real process boundary |
| Tool calling | stream=False | Ollama tool calling tidak support streaming |

---

## WHAT NEXT AGENT MUST NOT DO

- ❌ Jangan aktifkan Celery — disabled intentionally, Week 4
- ❌ Jangan invoke `letta.agents.messages.create()` — Qwen2.5 Q4 tidak support
- ❌ Jangan tambah Langfuse ke default profile — defer Week 3
- ❌ Jangan commit `.venv/` ke git
- ❌ Jangan duplicate `get_db` — pakai `deps.db.get_db` exclusively
- ❌ Jangan skip `set_tenant_context` sebelum query tenant-scoped tables
- ❌ Jangan pakai BGE-small-en untuk embeddings — English only, salah pilihan
- ❌ Jangan gunakan HTTP+SSE untuk MCP transport — gunakan Streamable HTTP
- ❌ Jangan pakai 0.5B sebagai CAI judge — fails on Chat Hard tasks (research: <50% accuracy)
- ❌ Jangan block HTTP response untuk critique/revise — adds 30-60s latency; always fire-and-forget
- ❌ Jangan store ALL preference pairs tanpa quality filter — DPO degrades dengan noisy data
- ❌ Jangan sort episodic retrieval by timestamp — sort by relevance score; recency-sort degrades accuracy 30%
- ❌ Jangan inject >3 episodic chunks — 7B model overwhelmed; use TOP_K_INJECT=3
- ❌ Jangan gunakan score_threshold <0.65 untuk RAG injection — noise masuk ke prompt = worse responses
- ❌ Jangan launch training run sebelum /v1/admin/stats menunjukkan ≥1000 unused_pairs — minimum dataset threshold
- ❌ Jangan gunakan DPO untuk first training run — gunakan SimPO (noise-tolerant, no reference model, +6.4pts)
- ❌ Jangan implementasi HyDE/query rewriting — CPU latency penalty terlalu besar pada 7B inference
- ❌ Jangan downgrade Qdrant di bawah v1.10.0 — hybrid Query API butuh ≥1.10.0
- ❌ Jangan pakai `embed()` untuk BM42 queries — WAJIB `query_embed()` (asymmetric embedding, silent wrong results)
- ❌ Jangan hapus `fastembed_cache` named volume tanpa alasan — ini menyimpan 90MB BM42 ONNX model
- ❌ Jangan set score_threshold pada BM42 prefetch leg — BM42 scores bukan cosine, range berbeda
- ❌ Jangan hapus `chunk_text` dari payload saat indexing — ini adalah migration escape hatch untuk re-embedding
- ❌ Jangan import SIDIX QA answers / corpus_qa / finetune_sft.jsonl sebagai seed data — hallucination transfer risk ke MiganCore model
- ❌ Jangan jalankan dua synthetic generation task sekaligus — asyncio.Lock sudah ada, gunakan /stop dulu
- ❌ Jangan filter semua synthetic pairs dari training set secara default — synthetic data valid, bedakan dengan source_method jika diperlukan
- ❌ Jangan hilangkan `num_ctx` dari Ollama call options — Ollama default ~2048 = silent context overflow (F-10)
- ❌ Jangan set `num_ctx` terlalu besar (>8192) tanpa benchmark — CPU inference O(n²) dengan context length
- ❌ Jangan skip `_trim_history_to_budget()` saat menambah history — token budget tidak otomatis dikelola oleh Ollama
- ❌ Jangan percaya notes lama tentang "upgrade needed" tanpa baca code actual — bisa jadi sudah diimplementasikan (F-11)
- ❌ Jangan restart auto-rerun dengan target_pairs berbeda tanpa /stop dulu — asyncio.Lock mencegah dua task, tapi Redis state perlu bersih
- ❌ Jangan set target_pairs terlalu kecil (< current DB count) — sistem akan exit immediately di round pertama setelah target check

---

## VPS ECOSYSTEM (JANGAN OVERLAP)

| Project | Path | Ports | Tujuan |
|---------|------|-------|--------|
| MiganCore (ADO) | `/opt/ado/` | 18000 | THIS PROJECT — Core Brain |
| SIDIX | `/opt/sidix/` | (separate) | Research Lab consumer, sidixlab.com |
| Ixonomic | `/var/www/ixonomic/` | 3000-3010+ | Business platform |
| nginx aaPanel | — | 80/443 | Routing semua domain |

**RAM Budget (dari 32GB):**
- Ollama 7B: ~6GB
- Postgres: ~500MB
- Qdrant: ~200MB
- Redis: ~100MB
- API: ~200MB
- Letta: ~500MB
- **Total ADO: ~7.5GB** dari 32GB — aman

---

## METRICS

| Metric | Value |
|--------|-------|
| API endpoints | 20 (5 auth + 4 agents + 3 chat + 3 conversations + 6 admin: 3 monitoring + 3 synthetic) |
| Frontend | https://app.migancore.com (Chat UI, Let's Encrypt SSL) — Day 22 ✅ |
| DB tables | 20 (includes papers, kg_entities, preference_pairs untuk Week 3-4) |
| Memory tier | Tier 1: Redis K-V ✅ | Tier 2: Qdrant (Day 12) | Tier 3: Letta blocks (Day 13) |
| Test coverage | E2E: 14/14 endpoints + 10/10 safety gates |
| Stack services | 6 running (postgres, redis, qdrant, ollama, api, letta) |
| External URL | API: https://api.migancore.com · App: https://app.migancore.com |
| RunPod budget | $0 spent of $50 allocated |
| Knowledge extraction | Qwen2.5-0.5B, fire-and-forget, Day 14 ✅ |
| CAI pipeline | Qwen2.5-7B judge, 50% sample rate, preference pairs, Day 15 ✅ |
| DPO pairs accumulated | real (CAI) + synthetic (synthetic_seed_v1) — target: 1000+ before training |
| Admin monitoring | /v1/admin/stats + /preference-pairs + /export (JSONL), Day 17 ✅ |
| Synthetic generator | auto-rerun with target_pairs=1000, running in background, Day 21 ✅ |
| Episodic RAG | Qdrant retrieval wired, score=0.65, top-k=3, sort-by-relevance, Day 16 ✅ |
| Hybrid search | BM42 sparse + dense RRF, Qdrant v1.12.0, 7 collections migrated, Day 18 ✅ |
| Context window | num_ctx=4096 explicit, token budget trimming, Day 20 ✅ |
| Tool executor timeout | memory_search: asyncio.wait_for(2.0s) → Redis fallback, Day 20 ✅ |
| Chat UI | app.migancore.com, SSE streaming, login/register, Day 22 ✅ |
| Git (Day 22) | VPS ↔ GitHub ↔ Local = SYNCED @ a8538d5 |

---

## HANDOFF LOG

| Date | Agent | Session Summary |
|------|-------|-----------------|
| 2026-05-02 (Day 0) | Kimi | Buat 8 master docs, schema, architecture, sprint plan |
| 2026-05-02 (Day 1) | Kimi | VPS provisioning, Docker, swap, SSH, JWT keys |
| 2026-05-02 (Day 2) | Kimi | DNS + nginx reverse proxy, SSL |
| 2026-05-02 (Day 3) | Kimi | Ollama container, Qwen2.5-7B + 0.5B pulled, 7-14 tok/s |
| 2026-05-02 (Day 4) | Kimi | Auth system: RS256, Argon2id, refresh rotation, 5 endpoints |
| 2026-05-02 (Day 5) | Kimi | RLS, cross-tenant tests, audit logging, ado_app non-superuser |
| 2026-05-02 (Day 6) | Kimi | Agent CRUD, chat endpoint, SOUL.md injection, config system |
| 2026-05-03 (Day 7) | Claude Sonnet 4.6 | Memory service (Redis K-V), SSE streaming, conversation endpoints |
| 2026-05-03 (Day 8) | Claude Sonnet 4.6 | Tool executor (4 tools), ReAct agentic loop, OllamaClient tool calling |
| 2026-05-03 (Day 7-9) | Kimi Code CLI | Audit + fix Day 7-9, wire director.py, deploy v0.3.0, E2E all pass |
| 2026-05-03 (Day 10) | Kimi Code CLI | Schema sync, agent spawning endpoint, v0.3.1, E2E all pass |
| 2026-05-03 (Day 11) | Kimi Code CLI | Safety gates: tool policy 6-class, max_agents, spawn depth, persona lock, REPL blacklist, tenant quota, Redis rate limiter. v0.3.2. E2E 10/10 |
| 2026-05-03 (Day 12) | Claude Sonnet 4.6 | Full audit + handoff: sync all repos, fix version, setup HTTPS. Ready for Qdrant RAG. |
| 2026-05-03 (Day 13) | Claude Sonnet 4.6 | Letta Tier 3: fact_extractor.py, persona blocks, 3-block architecture, E2E verified. v0.3.3. |
| 2026-05-03 (Day 14) | Claude Sonnet 4.6 | Knowledge auto-extraction: fact_extractor.py (0.5B model), wired in chat.py. v0.3.4. No DB migration. |
| 2026-05-03 (Day 15) | Claude Sonnet 4.6 | Constitutional AI pipeline: cai_pipeline.py (7B judge, critique+revise), CONSTITUTION.md (10 principles), 3rd create_task in chat.py. DPO flywheel started. v0.3.5. No DB migration. |
| 2026-05-03 (Day 16) | Claude Sonnet 4.6 | Episodic RAG retrieval: vector_retrieval.py (retrieve+format), wired sync in chat.py before run_director(), injected as last system prompt section. Score 0.65, top-k=3, sort by relevance. Research-backed (Mem0, LangMem, arxiv). v0.3.6. No DB migration. |
| 2026-05-03 (Day 17) | Claude Sonnet 4.6 | Admin monitoring: routers/admin.py (stats+list+export JSONL), PreferencePair ORM, ADMIN_SECRET_KEY config. 3 real CAI pairs discovered. Training readiness assessment built-in. Research: SimPO>DPO for first run. v0.3.7. No DB migration. |
| 2026-05-03 (Day 18) | Claude Sonnet 4.6 | Hybrid search BM42: embedding.py BM42 sparse model (get_sparse_model/embed_sparse_document/embed_sparse_query), vector_memory.py full rewrite (schema detection, zero-loss migration, Prefetch+RRF hybrid search, dense fallback). Qdrant v1.9→v1.12.0. 7 collections auto-migrated. fastembed_cache named volume. v0.3.8. No DB migration. |
| 2026-05-03 (Day 19) | Claude Sonnet 4.6 | Synthetic DPO generator: seed_bank.py (120 seeds, 7 domains, Triple-Source), synthetic_pipeline.py (generate→critique→revise, Redis tracking, graceful cancel), admin.py 3 new endpoints (start/status/stop), cai_pipeline.py source_method param + nullable source_message_id. v0.3.9. No DB migration. |
| 2026-05-03 (Day 20) | Claude Sonnet 4.6 | Context window management: num_ctx=4096 explicit in all Ollama calls (chat.py + director.py), token budget trimming in chat.py (_estimate_tokens, _trim_history_to_budget, MAX_HISTORY_LOAD=10). Tool executor timeout: asyncio.wait_for(2.0s) in _memory_search → Redis fallback; corrected source label qdrant_hybrid. v0.4.0. No DB migration. |
| 2026-05-03 (Day 21) | Claude Sonnet 4.6 | Auto-rerun synthetic generation: synthetic_pipeline.py multi-round loop with DB target check (_count_synthetic_pairs), new Redis keys (round/cumulative_stored/target_pairs), zero_yield safety abort. admin.py SyntheticStartRequest body. v0.4.1. No DB migration. |
| 2026-05-03 (Day 22) | Claude Sonnet 4.6 | Chat UI: frontend/chat.html (React 18 CDN, SSE streaming, login/register, agent auto-create, conversation persistence). Deployed to app.migancore.com (nginx + Let's Encrypt SSL). docs/USER_GUIDE.md (credentials + tutorial). No API change, no DB migration. Commit a8538d5. |
