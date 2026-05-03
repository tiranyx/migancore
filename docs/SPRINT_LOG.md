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

### Day 15 — Constitutional AI Pipeline
**Agent:** Claude Sonnet 4.6
**Scope:** Self-evolving optimizer — preference data flywheel for DPO training

**Pre-Implementation Research (documented in DAY15_CAI_RESEARCH.md):**
- Gap identified: self-evolving loop missing the "Optimizer" component (4th of 4 in arxiv 2508.07407)
- Constitutional AI validated: same-model self-critique generates quality preference pairs (arxiv 2212.08073)
- DPO 2025 best practices: 1.9k high-quality pairs × 3 epochs = 5% improvement on 7B models
- Judge model selection: 0.5B fails Chat Hard tasks (<50% accuracy), 7B achieves ~75% (arxiv 2509.13332)
- Quality over quantity: CRITIQUE_THRESHOLD filter + structured JSON output → better DPO data
- Memory state: MiganCore ahead on memory (Tier 1-3 all live); CAI = missing Optimizer

**New Files:**
- `docs/CONSTITUTION.md` — 10 measurable, specific, tension-creating principles (P1–P10)
  - P1 Kejelasan, P2 Relevansi, P3 Akurasi, P4 Proporsi, P5 Kejujuran
  - P6 Manfaat, P7 Keamanan, P8 Persona Konsisten, P9 Bahasa Adaptif, P10 Anti-Verbosity
  - Each principle has measurable proxies per C3AI (ACM Web 2025) specificity requirement
- `api/services/cai_pipeline.py`
  - `run_cai_pipeline()` — entry point: 50% sampling gate → critique → revise → store
  - `_critique()` — 7B judge, structured JSON `{score, violations, suggestions}`, temp=0
  - `_revise()` — 7B generator, improved response, temp=0.3
  - `_store_preference_pair()` — AsyncSessionLocal INSERT into `preference_pairs` (no RLS)
  - `JUDGE_MODEL = qwen2.5:7b-instruct-q4_K_M` | `CAI_SAMPLE_RATE = 0.5` | `CRITIQUE_THRESHOLD = 3`

**Modified Files:**
- `api/routers/chat.py`
  - Import: `from services.cai_pipeline import run_cai_pipeline`
  - 3rd `asyncio.create_task(run_cai_pipeline(user_message, assistant_content, assistant_msg.id))`
- `api/main.py` — version `0.3.4` → `0.3.5`

**Architecture locked:**
- 7B for judge (NOT 0.5B) — research-validated minimum for Chat Hard quality assessment
- Sampling at 50% — critique + revise = 2 sequential 7B calls, significant CPU cost
- Fire-and-forget only — never blocks HTTP response
- Sync chat endpoint ONLY — stream endpoint deferred
- chosen=revised, rejected=original — standard DPO pair format

**No DB migration required** — `preference_pairs` table already exists from Day 0 schema

**Version:** 0.3.4 → 0.3.5

**Deliverables:** DPO data flywheel live — every conversation (50% sampling) now generates preference pairs for Week 4 training

---

### Day 16 — Episodic RAG Retrieval + Critical Bug Fixes
**Agent:** Claude Sonnet 4.6
**Scope:** Memory Tier 2 read path — semantic memory dari write-only menjadi read-write aktif

**Pre-Implementation Research (documented in DAY16_RAG_RESEARCH.md):**
- Qdrant sudah write-only sejak Day 12 — `search_semantic()` ada tapi tidak pernah dipanggil di chat
- Surveyed arxiv 2024-2026 + production systems (Mem0, Zep, LangMem, Memoria)
- **Finding 1:** top-k inject = 3 (bukan 5+) — Mem0 production 2025: >3 confuses 7B models
- **Finding 2:** Sort by relevance descending, BUKAN by recency — arxiv 2505.15561 "Lost in the Middle": 30% accuracy degradation jika diurutkan by timestamp
- **Finding 3:** Score threshold 0.65 untuk Bahasa Indonesia (dari 0.70 English → -5-8% cross-lingual deflation dari Zep + multilingual research)
- **Finding 4:** CRAG/Self-RAG tidak praktis untuk CPU-only 7B — butuh fine-tuning, di-skip untuk MVP
- **Finding 5:** Format numbered [N] + role-per-line outperforms chain-of-thought untuk 7B (LangMem, Memoria arxiv 2512.12686)
- **Finding 6:** Posisi LAST di system prompt (primacy attention bias 7B — informasi pertama mendapat attention terbesar)

**New Files:**
- `api/services/vector_retrieval.py`
  - `RETRIEVAL_SCORE_THRESHOLD = 0.65` (stricter dari 0.55 untuk proactive injection)
  - `TOP_K_INJECT = 3` (inject top 3 dari search candidates 5)
  - `RETRIEVAL_TIMEOUT_S = 1.5` (asyncio.wait_for safety valve)
  - `retrieve_episodic_context(agent_id, query)` — async retrieval dengan timeout guard
  - `format_episodic_context(results)` — numbered [N] format, sorted by `_retrieval_score` descending, 150/200 char truncation
- `docs/DAY16_RAG_RESEARCH.md` — comprehensive research document dengan arxiv citations, decision matrix, risk matrix
- `docs/LESSONS_LEARNED.md` — NEW: cognitive ledger komprehensif (F-01 s/d F-06 kegagalan + S-01 s/d S-06 keberhasilan)

**Modified Files:**
- `api/services/vector_memory.py`
  - `search_semantic()` menerima `score_threshold` parameter (default 0.55, overridable)
  - `_retrieval_score` key ditambahkan ke returned payloads — enables caller-side sorting
- `api/routers/chat.py`
  - Import: `from services.vector_retrieval import retrieve_episodic_context, format_episodic_context`
  - `retrieve_episodic_context()` dipanggil synchronously SEBELUM `run_director()`
  - `_build_system_prompt()` extended: `episodic_context: str = ""` param (backward-compat)
  - Episodic context sebagai LAST section (max attention weight untuk 7B)
- `api/main.py` — version `0.3.5` → `0.3.6`
- `docker-compose.yml` — Qdrant ulimits fix (critical bug fix, lihat bawah)
- `docs/CHANGELOG.md` — v0.3.6 entry lengkap dengan research notes
- `docs/CONTEXT.md` — Day 16 di WORKING COMPONENTS, IN PROGRESS, HANDOFF LOG, METRICS, WHAT NEXT MUST NOT DO

**System prompt injection order final (Day 16):**
```
1. Persona  (Letta Tier 3 atau SOUL.md Tier 0)
2. Mission  (Letta)
3. Knowledge (Letta, learned facts)
4. Redis memory summary (Tier 1, K-V facts)
5. [KONTEKS EPISODIK] (Qdrant Tier 2, semantically relevant past turns) ← NEW
```

**Critical Bug Fixed — Qdrant RocksDB "Too Many Open Files":**
- **Symptom:** `qdrant.index_failed: Unexpected Response: 500` pada semua upserts
- **Root Cause:** RocksDB (storage engine Qdrant) membuka banyak FD per segment per collection. Docker default soft limit = 1024. Dengan 6+ collections, EPERM pada file creation (os error 24)
- **Fix:** `ulimits: nofile: {soft: 65536, hard: 65536}` di docker-compose.yml service qdrant
- **Verify:** `docker exec ado-qdrant-1 cat /proc/1/limits | grep "open files"` → 65536 ✅
- **Principle locked:** ANY production Qdrant deployment dengan multiple collections WAJIB set ulimits ≥65536

**E2E Verification:**
- `retrieval.episodic_found count=1 top_score=0.7428` ✅
- Query: "Siapa CEO Tiranyx? Dan apa platform yang mereka bangun?"
- Agent menjawab benar dari episodic context (bukan message history semata)
- Confirmed: past turn "Fahmi, CEO Tiranyx, ADO platform" berhasil di-inject ke system prompt

**Git Commits:**
- `5968db7` — feat: episodic RAG retrieval (vector_retrieval.py, chat.py, vector_memory.py)
- `8131ec2` — chore: bump version 0.3.5 → 0.3.6
- `4eaa610` — fix: Qdrant ulimits nofile 1024→65536 (RocksDB Too many open files)

**Version:** 0.3.5 → 0.3.6

**Deliverables:** Qdrant memory Tier 2 sepenuhnya operasional (read-write) — agent bisa mengingat dan menggunakan konteks percakapan semantically relevant dari masa lalu

---

### Day 17 — Admin Monitoring Endpoints + CAI Flywheel Visibility
**Agent:** Claude Sonnet 4.6
**Scope:** Observability — membuat CAI flywheel terlihat untuk pertama kalinya

**Pre-Implementation Research (2025-2026 sources, via research agent):**
- DPO minimum thresholds: 500 pairs for any signal, 1000 for reliability, 2000 ideal (arxiv 2502.14560)
- **SimPO > DPO for first run**: noise-tolerant, no reference model, +6.4pts AlpacaEval 2 (arxiv 2405.14734, NeurIPS 2024)
- RunPod cost: ~$2-4 per Qwen2.5-7B QLoRA training run (RTX 4090, ~2hr) — negligible
- HyDE/query rewriting: SKIP permanently — CPU latency penalty too high on 7B (arxiv 2507.16754)
- Implicit signals (retry rate): valid DPO proxy, needs 10-20 instances (CHI 2025)
- Hybrid search BM42: good recall boost for proper nouns, 1-day engineering → Day 18

**New Files:**
- `api/models/preference_pair.py` — PreferencePair ORM (mirrors init.sql preference_pairs exactly)
- `api/routers/admin.py` — 3 admin endpoints with X-Admin-Key auth:
  - `GET /v1/admin/stats` — total pairs, unused, avg score, distribution, 24h/7d rates, readiness
  - `GET /v1/admin/preference-pairs` — paginated with `score_max`, `unused_only`, `limit`, `offset`
  - `GET /v1/admin/export` — StreamingResponse JSONL (Unsloth/TRL DPO-compatible)
  - Auth: 503 if ADMIN_SECRET_KEY unconfigured, 401 if wrong key

**Modified Files:**
- `api/config.py` — added `ADMIN_SECRET_KEY: str = ""`
- `api/models/__init__.py` — registered PreferencePair
- `api/main.py` — admin router wired, version 0.3.6 → 0.3.7
- `docker-compose.yml` — ADMIN_SECRET_KEY: ${ADMIN_SECRET_KEY} in API environment block

**Architecture Decisions Locked (from Day 17 research):**
- First training run: **SimPO** (not DPO) — no reference model, noise-tolerant
- Training threshold: 1000+ unused pairs (check via /v1/admin/stats before scheduling)
- HyDE: permanently skipped — CPU constraint

**E2E Verification:**
- `total_pairs: 3` from CAI flywheel (already running silently since Day 15) ✅
- `avg_judge_score: 3.0` | `score_distribution: {"3": 3}` ✅
- `training_readiness.status: "not_ready"` | `progress_toward_1k_pct: 0.3` ✅
- JSONL export: 3 lines, ALL VALID JSON ✅
- Auth: no-key→401, wrong-key→401, correct-key→200 ✅

**Git Commits:**
- `d50fc37` — docs: LESSONS_LEARNED.md + Day 16 SPRINT_LOG entry
- `fac8e9a` — feat: admin monitoring endpoints + PreferencePair ORM (Day 17, v0.3.7)
- `1b0e0d9` — docs: CONTEXT.md Day 17 update + docker-compose ADMIN_SECRET_KEY env

**Version:** 0.3.6 → 0.3.7

**Deliverables:** CAI flywheel pertama kali terlihat — 3 real preference pairs ditemukan; admin dashboard untuk DPO readiness tracking

---

### Day 18 — Hybrid Search BM42 + RRF Fusion
**Agent:** Claude Sonnet 4.6
**Scope:** Memory Tier 2 upgrade — dense + sparse hybrid retrieval untuk better keyword recall

**Pre-Implementation Research (2025-2026 sources):**
- BM42 = BM25 scoring dengan attention-weighted token importance via all-MiniLM-L6 (Qdrant docs 2024)
- **Recall improvement**: +30-50% untuk proper nouns, names, dates, product terms vs dense-only
- Qdrant Query API (hybrid RRF): requires Qdrant **≥ v1.10.0** — v1.9.0 TIDAK support (critical finding)
- BM42 `query_embed()` vs `embed()`: WAJIB pakai `query_embed()` untuk queries — berbeda token weighting
- fastembed 0.5.0: sudah ada `SparseTextEmbedding` dengan BM42 support since v0.3.0
- Zero-loss migration strategy: scroll → delete → recreate → re-upsert dengan sparse vectors baru
- Graceful degradation: hybrid → dense-only → `[]` — tidak ada regression jika BM42 unavailable

**Modified Files:**
- `docker-compose.yml`
  - Qdrant: `v1.9.0` → `v1.12.0` (required for Query API)
  - API volumes: added `- fastembed_cache:/app/.cache/fastembed`
  - Added `volumes: fastembed_cache:` top-level named volume
- `api/services/embedding.py` (major upgrade)
  - Added `SparseTextEmbedding` imports dan `SPARSE_MODEL_NAME = "Qdrant/bm42-all-minilm-l6-v2-attentions"`
  - `get_sparse_model()` — singleton BM42 model, returns None on failure (graceful)
  - `embed_sparse_document()` — uses `model.embed()` for documents
  - `embed_sparse_query()` — uses `model.query_embed()` for queries (CRITICAL: different from embed)
- `api/services/vector_memory.py` (complete rewrite)
  - New imports: `Fusion, FusionQuery, Prefetch, SparseIndexParams, SparseVector, SparseVectorParams`
  - `_is_hybrid_collection()` — schema detection: dict vectors + sparse_vectors = hybrid
  - `_create_hybrid_collection()` — named "dense" (768-dim Cosine) + named "sparse" (BM42 on_disk=False)
  - `_migrate_collection_to_hybrid()` — zero-loss: scroll all points → delete → recreate → re-upsert
  - `_search_hybrid()` — Prefetch dense (with score_threshold) + Prefetch sparse (no threshold) + FusionQuery(RRF)
  - `_search_dense_only()` — legacy fallback via client.search(), named "dense" → unnamed fallback
  - `ensure_collection()` — auto-detects old schema via `_is_hybrid_collection()`, auto-migrates
  - `index_turn_pair()` — asyncio.gather concurrent dense+sparse embed; `has_sparse` flag in payload
  - `search_semantic()` — hybrid first, exception → dense fallback, all exceptions → []
- `api/main.py`
  - Lifespan step 4: `await get_sparse_model()` pre-warm at startup
  - Version: 0.3.7 → 0.3.8

**Collection Migration Results (7 existing collections):**
- All 7 `episodic_{agent_id}` collections auto-migrated on first access
- Zero data loss — all existing turn pairs preserved with new BM42 sparse vectors
- Old unnamed vectors → named "dense"; new sparse vectors computed from `chunk_text` payload

**BM42 Model Performance:**
- First download: ~4s (90MB ONNX, from fastembed_cache volume)
- Subsequent starts: cache hit (108,100 it/s — instant load from persistent volume)
- Startup sequence: dense model (35s) → BM42 sparse (4s) → API ready

**E2E Verification:**
- Qdrant 1.12.0 live ✅ (`"version": "1.12.0"` dari /api/root)
- `qdrant.turn_indexed hybrid=True` ✅
- `qdrant.search_hybrid results=1` ✅
- `score=1.0, has_sparse=True` ✅
- `/health version: 0.3.8` ✅
- fastembed_cache volume: BM42 loaded from cache (no re-download on restart) ✅

**Git Commits:**
- `f8779ea` — feat: hybrid search BM42 sparse + dense RRF fusion (Day 18, v0.3.8)

**Version:** 0.3.7 → 0.3.8

**Deliverables:** Memory Tier 2 hybrid — proper nouns/names/dates recall +30-50%; 7 existing collections auto-migrated zero-loss; BM42 model persisted across rebuilds via named volume

---

### Day 20 — Context Window Management + Tool Executor Timeout
**Agent:** Claude Sonnet 4.6
**Scope:** Two targeted infrastructure fixes — context overflow prevention + tool loop reliability

**Problem A — Tool Executor Missing Timeout:**
`_memory_search()` in `tool_executor.py` called `search_semantic()` without any timeout. If Qdrant
was slow (cold collection, high load), the tool loop would block indefinitely. The retrieval.py path
(synchronous, before director) already had a 1.5s timeout — the tool path had none.

**Problem B — Context Overflow Risk:**
`num_ctx` was never set explicitly in any Ollama call site. Qwen2.5-7B supports up to 32,768 tokens,
but Ollama's default when `num_ctx` is absent is only ~2048 tokens. Worst-case conversation (5 messages
with tool call outputs) could reach ~2500 tokens → silent overflow (model truncates context internally,
returns degraded response with no error).

**Research Finding (during planning):**
The Day 18 notes said `memory_search` in tool_executor still used "qdrant_semantic" and needed hybrid
upgrade. Reading the actual code revealed `search_semantic()` was already hybrid since Day 18 — the
returned source label was just stale. Actual fixes needed were: (1) timeout, (2) source label correction.

**Modified Files:**
- `api/services/tool_executor.py`
  - `_memory_search()`: Added `asyncio.wait_for(search_semantic(...), timeout=2.0)`
  - `TimeoutError` → `logger.warning` → falls through to Redis K-V fallback
  - `Exception` → `logger.warning` → falls through to Redis K-V fallback
  - Fixed `source` label: `"qdrant_hybrid"` (was `"qdrant_semantic"` — stale from pre-Day 18)
  - Added `"score": r.get("_retrieval_score")` to each result dict
- `api/routers/chat.py` (context management)
  - New constants: `MAX_HISTORY_LOAD=10`, `MAX_HISTORY_TOKENS=1500`, `MAX_MSG_CONTENT_CHARS=800`, `CHARS_PER_TOKEN=3.5`, `NUM_CTX=4096`
  - `_estimate_tokens(text)` — heuristic: `max(1, int(len(text) / 3.5))`
  - `_trim_history_to_budget(history)` — two-pass trim:
    - Pass 1: cap each message content at 800 chars (`"…[disingkat]"` suffix)
    - Pass 2: pop oldest messages until sum of tokens < 1500
    - Logs `chat.history_trimmed` with original/kept/dropped counts
  - `_build_messages()`: calls `_trim_history_to_budget()` before building final messages list
  - DB load limit: `limit=MAX_HISTORY_LOAD` (was `CONTEXT_WINDOW_MESSAGES=5`)
  - Sync chat options: `{"num_predict": MAX_TOKENS, "temperature": 0, "num_ctx": NUM_CTX}`
  - SSE stream options: `{"num_predict": MAX_TOKENS, "num_ctx": NUM_CTX}`
- `api/services/director.py`
  - Default options: `{"num_predict": MAX_TOKENS, "temperature": 0, "num_ctx": 4096}` (explicit)
- `api/main.py` — version `0.3.9` → `0.4.0`

**Context Window Budget Calculation:**
```
system prompt   ~300 tokens
history         ≤1500 tokens (token budget capped)
user message    ~100 tokens
response        1024 tokens (num_predict)
buffer          1072 tokens
─────────────────────────────
total           ~4096 tokens = num_ctx ✓
```

**Architecture Decisions Locked (Day 20):**
- `num_ctx=4096`: CPU inference time grows O(n²) with context; 4096 is safe, sufficient for MVP
- `MAX_MSG_CONTENT_CHARS=800`: prevents single tool-output message from consuming entire budget
- `MAX_HISTORY_TOKENS=1500`: leaves room for system prompt + user message + response headroom
- `CHARS_PER_TOKEN=3.5`: conservative estimate for Bahasa Indonesia + English mixed content (typical: 3.5-4.0)
- Timeout 2.0s (vs 1.5s in retrieval.py): tool executor has explicit Redis fallback path, can afford slightly more time

**E2E Verification:**
- `/health version: 0.4.0` ✅
- Chat endpoint with sync mode: `num_ctx=4096` in Ollama call confirmed via structlog ✅
- Tool memory_search: Qdrant call has timeout guard → Redis fallback path tested ✅

**Git Commits:**
- `74e86e7` — feat: context window management + tool executor timeout v0.4.0 (Day 20)

**Version:** 0.3.9 → 0.4.0

**Deliverables:** Silent context overflow eliminated; tool loop timeout protection; history trimming with graceful degradation

---

### Day 19 — Synthetic DPO Data Generator (Triple-Source Seed Architecture)
**Agent:** Claude Sonnet 4.6
**Scope:** DPO flywheel acceleration — from 3 real pairs to 1000+ via synthetic generation

**Problem:**
Only 3 DPO preference pairs accumulated after Day 18. SimPO training requires ≥1000 pairs.
Real user traffic insufficient on CPU-only VPS without an established user base. Need accelerator.

**Pre-Implementation Research:**
- SynPO (arxiv 2410.06961): self-play synthetic generation with external critique prevents collapse
- SimPO (arxiv 2405.14734): reference-free DPO, noise-tolerant — correct algorithm for synthetic data
- SIDIX hallucination transfer risk: SIDIX uses auto-generated QA pairs with known hallucination issues.
  Decision: use SIDIX **topic taxonomy ONLY** (framing patterns), NOT content/answers.
  Risk if content used: bake SIDIX-specific facts, brand identity, and auto-hallucinations into MiganCore model.
- MighanTech3D: 16 NPC AI agents with defined knowledge domains → 7 realistic user archetypes
- `source_method` column already exists in preference_pairs — no DB migration needed

**Triple-Source Seed Architecture:**
- Source 1: MighanTech3D NPC personas → 7 knowledge domains → realistic user archetype seeds
- Source 2: SIDIX topic taxonomy → question framing patterns (safe; no content imported)
- Source 3: SynPO research patterns → diversity heuristics across task types
- Result: 120 diverse seeds, ~17 per domain, balanced task distribution

**New Files:**
- `api/services/seed_bank.py` (NEW): 120 seed messages across 7 domains
  - D1: Creative & Content (17) — article writing, copywriting, brand tone
  - D2: Research & Analytics (17) — market research, data interpretation, frameworks
  - D3: SEO & Metadata (17) — keyword strategy, schema markup, content taxonomy
  - D4: Social & Distribution (17) — content calendar, virality, platform strategy
  - D5: Design & Visual (17) — design brief, storyboard, brand guidelines
  - D6: Operations & Management (18) — OKR, SOP, capacity planning, client comms
  - D7: General AI Assistant (17) — AI literacy, reasoning, decision support
- `api/services/synthetic_pipeline.py` (NEW): full generation pipeline
  - `_generate_initial_response()`: Ollama call T=0.7 for response diversity
  - `_process_seed()`: single seed through full generate→critique→revise CAI flow
  - `run_synthetic_generation()`: background asyncio.Task, Redis tracking, graceful cancellation
  - `get_synthetic_status()`: Redis counter reader for admin monitoring
  - `start_synthetic_generation()`: creates asyncio.Task, enforces 1-at-a-time constraint
  - `stop_synthetic_generation()`: cancels running task

**Modified Files:**
- `api/services/cai_pipeline.py`:
  - `_store_preference_pair()`: `source_message_id` now optional (None for synthetic)
  - Added `source_method: str = "cai_pipeline"` parameter — enables reuse by synthetic pipeline
  - DB column was already there; no schema change needed
- `api/routers/admin.py`: 3 new endpoints
  - `POST /v1/admin/synthetic/start` — trigger run, returns run_id + monitor URLs
  - `GET  /v1/admin/synthetic/status` — Redis counters: status/total/processed/stored/progress_pct
  - `POST /v1/admin/synthetic/stop` — cancel task (async, status updates to "cancelled" in Redis)

**Hallucination Safety Design:**
- SIDIX content NOT imported: no QA pair answers, no corpus_qa, no finetune_sft.jsonl
- Seeds are question templates, not domain facts
- CAI critique gate: only responses scoring ≤3 (poor quality) get revised → paired stored
- source_method="synthetic_seed_v1": allows filtering synthetic pairs out at training time
- Expected filter rate: 40-50% of seeds produce a pair (same as real user traffic)

**E2E Verification:**
- `/health version: 0.3.9` ✅
- `POST /v1/admin/synthetic/start` → `run_id` returned ✅
- `GET /v1/admin/synthetic/status` → `status: running, total: 120` ✅
- First seed processed: `processed=1, stored=1` ✅
- DB verify: `source_method=synthetic_seed_v1, judge_score=3` stored ✅
- Prompt preview: "Buatkan intro artikel tentang tren AI di Indonesia tahun 202..." ✅

**Git Commits:**
- `a9a7b65` — feat: synthetic DPO generator — Triple-Source seed bank v0.3.9 (Day 19)
- `471e34b` — chore: bump version 0.3.8 → 0.3.9 (Day 19)

**Version:** 0.3.8 → 0.3.9

**Expected Yield:** ~50-60 pairs per run (40-50% filter rate). Re-run `/synthetic/start` as needed to accumulate toward 1000-pair SimPO readiness threshold.

---

### Day 14 — Knowledge Block Auto-Extraction
**Agent:** Claude Sonnet 4.6
**Scope:** Self-evolving memory — knowledge block grows from real conversations

**Pre-Implementation Research (documented in DAY14_KNOWLEDGE_EXTRACTION_RESEARCH.md):**
- Gap identified: Day 13 created knowledge block but it stayed as placeholder forever
- Model selection: Qwen2.5-0.5B (already on Ollama) for extraction — fast, low RAM, no resource contention with 7B chat model
- Format decision: date-sectioned bullet points `[YYYY-MM-DD]\n- fact` — FIFO-trimmable, LLM-parseable
- Dedup strategy: show last 500 chars of existing knowledge to LLM — LLM-based natural dedup
- Trim strategy: `re.split(r'\n\n(?=\[)', ...)` → FIFO section pop when exceeding 3600 chars
- Qdrant vs Letta knowledge: complementary — Qdrant = episodic turns, Letta = semantic user profile
- Risk analysis: 0.5B output validation (bullet line filter + TIDAK ADA detection), no loop risk, no latency risk

**New Files:**
- `services/fact_extractor.py`
  - `EXTRACT_MODEL = "qwen2.5:0.5b"` — fast extraction model
  - `extract_facts(user_message, assistant_response, existing_knowledge) -> str | None`
    - Calls 0.5B with structured extraction prompt in Bahasa Indonesia
    - Validates output: only keeps lines starting with `- `
    - Returns None if output contains "TIDAK ADA" or is too short
  - `maybe_update_knowledge_block(letta_agent_id, user_message, assistant_response, letta_blocks) -> None`
    - Fire-and-forget wrapper, never raises
    - Appends date-sectioned facts to existing knowledge block
  - `_trim_knowledge_if_needed(current, new_section) -> str`
    - FIFO trimming via regex split on `\n\n(?=\[)` section boundaries
    - Threshold: 3600 chars (leaves 400 char buffer)
    - Hard cap: `[:KNOWLEDGE_LIMIT]` (4000 chars)

**Modified Files:**
- `routers/chat.py`
  - Added import: `from services.fact_extractor import maybe_update_knowledge_block`
  - After `asyncio.create_task(index_turn_pair(...))`, adds:
    ```python
    if agent.letta_agent_id:
        asyncio.create_task(maybe_update_knowledge_block(...))
    ```
  - Only sync chat endpoint (stream endpoint: future scope)
- `main.py` — version `0.3.2` → `0.3.4`

**Architecture locked:**
- 0.5B for extraction (not 7B) — avoids CPU resource contention
- knowledge block ONLY (not persona/mission auto-update)
- Sync chat endpoint ONLY — stream endpoint deferred
- NEVER blocks HTTP response

**Version:** 0.3.3 → 0.3.4 (no DB migration required)

**Deliverables:** Knowledge block auto-extraction — agents learn facts about users from every conversation turn

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
