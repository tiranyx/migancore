# MIGANCORE — CHANGELOG.md

All notable changes to the MiganCore API.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.4.6] — 2026-05-04 (Day 28) — Distillation Pipeline + Admin Dashboard

### Added
- **Multi-Provider Teacher API Wrapper** — `services/teacher_api.py`
  - 4 LLM providers: Anthropic Claude, Moonshot Kimi K2.6, OpenAI GPT-4o, Google Gemini 2.5 Flash
  - Unified async interface with cost tracking + retry x3 + exponential backoff
  - PRICING table single source of truth (12 model variants)
  - `is_teacher_available()` / `list_available_teachers()` for env-aware UX
- **Distillation Pipeline** — `services/distillation.py` (476 lines)
  - student (MiganCore-7B) vs teacher LLM with independent judge
  - Margin filter `DISTILL_MARGIN_THRESHOLD=2.0` (judge_diff >= 2.0)
  - Budget cap `DISTILL_BUDGET_USD_HARD_CAP=10.0`
  - SOUL.md injected as teacher system prompt → persona preserved
  - Independent judge enforced (teacher==judge → swap to alt teacher)
  - Source method: `distill_<teacher>_v1`
  - Background asyncio task with Redis state tracking
- **Admin REST endpoints** in `routers/admin.py`
  - `POST /v1/admin/distill/start` — kick off distillation run
  - `GET /v1/admin/distill/status` — live state
  - `POST /v1/admin/distill/stop` — cancel in-flight run
  - `GET /v1/admin/distill/summary` — aggregate stats per teacher
- **Admin Dashboard** — `frontend/dashboard.html` (814 lines, standalone React)
  - Live at `https://app.migancore.com/admin/`
  - Auth gate: X-Admin-Key
  - Top stats: total pairs, unused, last 24h, training_readiness
  - Source breakdown bars (cai/synthetic/distill/manual color-coded)
  - Distill panel: teacher/judge/target/budget controls, live progress, history table
  - Synthetic panel: status, target, start/stop
  - Auto-refresh 4s

### Changed
- `api/config.py`: ANTHROPIC_API_KEY, OPENAI_API_KEY, KIMI_API_KEY, GEMINI_API_KEY, DISTILL_*
  - ELEVENLABS_VOICE_ID default updated to user's voice (`pIdeS8l1cmJzzqqt7NRc`)
- `api/main.py`: version 0.4.5 → 0.4.6
- `docker-compose.yml`: pass all 4 teacher API keys + voice ID env
- Source method convention extended: `distill_*` for teacher-derived pairs

### Fixed
- Kimi model name: switched from researched `kimi-k2-0905-preview` to actual valid `kimi-k2.6`
- Kimi K2 thinking mode: explicitly disabled for distillation (cleaner content response)
- Kimi K2 temperature: 0.6 with thinking-disabled (server enforces strictly)
- Gemini truncation: `max_tokens >= 256` minimum + safety filters BLOCK_NONE + finishReason check
- Container rebuild: documented `--build` flag (force-recreate alone reuses old image)

### Verified E2E
```
4 teacher smoke tests:    PASS  (Claude $0.0009, Kimi $0.0001, GPT $0.0004, Gemini $0.000004)
Distillation start:       HTTP 200 — kimi teacher, claude judge, 30 target, $0.5 cap
Synthetic resume:         HTTP 200 — picking up at 228 pairs
Dashboard external:       HTTP 200 — https://app.migancore.com/admin/
Dashboard auth gate:      X-Admin-Key required, validates against /v1/admin/stats
```

### Lessons
1. Always probe model availability via `/v1/models` before hardcoding (Kimi name was wrong)
2. Read vendor docs CAREFULLY — Kimi thinking mode + temperature constraints + reasoning_content field undocumented in research summary
3. Gemini safety filters aggressive — must explicitly set BLOCK_NONE for legit distillation use
4. `docker compose up -d --force-recreate` ≠ rebuild — always use `--build` for code changes
5. Hallucination without context = teaching wrong things → SOUL.md injection MANDATORY in distillation

---

## [0.4.5] — 2026-05-04 (Day 27) — API Keys + migan CLI + MCP Resources + TTS + Memory Pruning

### Added
- **Long-lived API Keys** (`mgn_live_<id>_<secret>` format)
  - `migrations/025_day27_api_keys.sql`: `api_keys` table with hashed lookup
  - `services/api_keys.py`: HMAC-SHA256(pepper, key) — Stripe/OpenAI pattern
  - `routers/api_keys.py`: POST/GET/DELETE `/v1/api-keys`
  - `models/api_key.py`: ORM
  - 256-bit secret entropy, hash indexed for sub-1s revoke propagation
  - Default scopes: `tools:exec`, `chat:read`, `chat:write`
- **`migan` CLI Setup Script**
  - `scripts/migan-setup.sh` (Linux/Mac/WSL) + `migan-setup.ps1` (Windows)
  - One-liner: `curl -sL .../migan-setup.sh | bash` — login, create API key, `claude mcp add`
- **MCP Resources** (4 templates in `mcp_server.py`)
  - `migancore://workspace/{path}` — sandboxed file read
  - `migancore://workspace` — workspace root listing
  - `migancore://soul` — Mighan-Core persona
  - `migancore://memory/help` — memory tier reference
  - Used in Claude Code via `@migancore:<uri>` syntax
- **TTS Tool** — `text_to_speech` via ElevenLabs `eleven_flash_v2_5`
  - 7th tool added to TOOL_REGISTRY (now 8 total)
  - Returns base64-encoded mp3 + size + chars used
  - Caps: 2500 chars/call, 2MB audio response
  - Free tier: 10k chars/month
- **Memory Pruning Daemon** — `services/memory_pruner.py`
  - Background asyncio task, daily run (24h interval, 5min initial delay)
  - Filter: `timestamp < now-30d AND importance < 0.7` (importance defaults to NULL = pinned)
  - Auto-creates payload indexes on `timestamp` + `importance`
  - Exception-wrapped — silent death prevention
- **`docs/DAY27_PLAN.md`** — full sprint plan with hypothesis/risk/benefit/adaptation

### Changed
- `api/deps/auth.py` — `get_current_user()` accepts BOTH JWT and API key
- `api/mcp_server.py` — middleware accepts both auth schemes; +4 resources; +1 tool (TTS)
- `api/services/tool_executor.py` — `_text_to_speech()` handler + ELEVENLABS_TTS_ENDPOINT constant
- `api/main.py` — pruner task + version 0.4.4 → 0.4.5
- `api/config.py` — ELEVENLABS_*, API_KEY_PEPPER, MEMORY_PRUNE_* settings
- `config/skills.json` — text_to_speech registration
- `config/agents.json` — text_to_speech in core_brain default_tools
- `docker-compose.yml` — ELEVENLABS_KEY + API_KEY_PEPPER env vars

### Verified E2E (11 tests)
```
1. JWT login                  PASS
2. Create API key             PASS — mgn_live_659906db... format OK
3. List API keys              PASS — 1 found
4. MCP init via API key       PASS — protocolVersion 2025-06-18
5. tools/list                 PASS — 8 tools
6. resources/templates/list   PASS
7. resources/list concrete    PASS — 3 resources
8. resources/read workspace   PASS — file listing returned
9. TTS without key            PASS — graceful error
10. Revoke API key            PASS — HTTP 204
11. Revoked key blocked       PASS — HTTP 401 within 1s
```

### Lessons
1. PostgreSQL `text[]` arrays vs JSON in DEFAULT clause — use `ARRAY[...]::text[]`
2. ElevenLabs uses `xi-api-key` header, NOT `Authorization: Bearer`
3. Memory pruner asyncio task MUST be wrapped in try/except — silent death otherwise

---

## [0.4.4] — 2026-05-04 (Day 26) — MCP Streamable HTTP Server + Episodic Memory Poisoning Filter

### Added
- **`api/mcp_server.py`** — MCP Streamable HTTP server using official Anthropic SDK (`mcp>=1.27.0`)
  - 7 tools exposed: `web_search`, `generate_image`, `write_file`, `read_file`, `memory_write`, `memory_search`, `python_repl`
  - Mounted at `/mcp/` on the existing FastAPI app via Starlette ASGI sub-mount
  - `stateless_http=True` — no session bookkeeping, simpler ops
  - JWT auth enforced via pure ASGI middleware (NOT `BaseHTTPMiddleware` — that breaks SSE)
  - Auth reuses existing RS256 JWT keys (`services/jwt.py`)
  - Endpoint live at `https://api.migancore.com/mcp/`
- **`docs/DAY26_PLAN.md`** — full implementation plan with hypothesis/risk/benefit/adaptation
- **`api/services/vector_memory.py::_is_tool_error_response()`** — pattern detection for tool-error
  responses ("policy block", "encountered an issue", "operation was blocked", "requires plan", etc.)
- **`api/services/vector_memory.py::index_turn_pair()`** — skip indexing if response is a tool error
  (prevents episodic memory poisoning where the model regurgitates past failures on similar prompts)

### Changed
- `api/main.py`: lazy import + mount MCP at `/mcp` + start `mcp.session_manager.run()` in lifespan
  (mounted Starlette sub-apps DON'T inherit parent lifespan — caused 500 "Task group not initialized")
- `api/requirements.txt`: bumped `httpx>=0.27.2`, `pydantic-settings>=2.5.2`, `pydantic>=2.11`,
  `pyjwt>=2.10.1` for `mcp` SDK compatibility. Added `mcp>=1.27.0`.
- `api/main.py`: version 0.4.3 → 0.4.4
- `.gitignore`: fixed UTF-16 BOM (PowerShell encoding) → UTF-8, added `*.tar.gz` rule

### Verified E2E
```
[Internal HTTP at 127.0.0.1:18000/mcp/]
  auth check (no token):       HTTP 401 PASS
  auth check (invalid token):  HTTP 401 PASS
  initialize handshake:        HTTP 200 PASS — protocolVersion 2025-06-18
  initialized notification:    HTTP 202 PASS
  tools/list:                  7 tools returned PASS
  tools/call write_file:       file persisted at /opt/ado/data/workspace/ PASS
  tools/call generate_image:   fal.ai URL returned PASS

[External HTTPS at api.migancore.com/mcp/]
  initialize handshake:        PASS — serverInfo {name:'migancore', version:'1.27.0'}

[Episodic memory poisoning filter]
  8 pattern tests: 8 PASS, 0 FAIL
```
Image generated via MCP: `https://v3b.fal.media/files/b/0a98c63d/Yga1T4Oz8cFvzAAifdAQd.jpg`

### Lessons Documented
1. `BaseHTTPMiddleware` incompatible with SSE — use pure ASGI middleware function
2. Mounted Starlette sub-apps DON'T inherit parent lifespan — must explicitly start
3. FastMCP `streamable_http_path` defaults to `/mcp` — set `"/"` to avoid double-mount
4. FastMCP `token_verifier` requires full `auth_settings` (OAuth 2.1) — bypass with custom middleware
5. FastMCP rejects foreign Host headers (DNS rebinding protection) — explicit `TransportSecuritySettings` allowlist required behind nginx

---

## [0.4.3] — 2026-05-04 (Day 25) — Sprint Fixes: SSE heartbeat, generate_image LLM compliance, tool DB migration

### Fixed
- **SSE "TypeError: network error"** (visible at app.migancore.com): added 15s heartbeat ping
  in `chat_stream`. Wraps async iterator with `asyncio.wait_for(timeout=15)` and emits
  `data: {"type":"ping"}` on silence so nginx/Cloudflare don't close the connection during
  long Ollama compute periods. Frontend ignores `ping` events silently.
- **`generate_image` not invoked by qwen2.5:7b**: model wrote Python pseudocode (`image_data = generate_image(...)`)
  instead of native function-calling. Fix: imperative MANDATORY descriptions in `skills.json` +
  explicit intent→tool mapping table in `_build_system_prompt` system prompt.
- **Frontend SSE error UX**: `TypeError: network error` was shown raw to user. Now displays
  `"Koneksi terputus. Server butuh waktu lama merespon — coba kirim ulang."`.
- **Episodic memory poisoning**: failed tool-call responses were indexed into Qdrant and the
  retrieval system regurgitated them on similar prompts. Manual cleanup performed (14 points
  deleted). TODO Day 26+: filter `tool_error` responses from indexing pipeline.
- **DB tool policy stale**: `read_file` had `[pro,enterprise] + requires_approval=true` from
  Day 11 migration, blocking Day 24 free-tier tool. Migration `024_day24_tool_expansion.sql`
  resets to `[free,pro,enterprise] + auto-approved`, max 200 calls/day.
- **`tools.name` no UNIQUE constraint**: migration's `ON CONFLICT (name)` failed. Switched to
  idempotent `WHERE NOT EXISTS` + `UPDATE` pattern.

### Added
- **`migrations/024_day24_tool_expansion.sql`** — idempotent migration: fix `read_file` policy,
  insert `write_file` and `generate_image` tools with `[free,pro,enterprise]` policies.

### Changed
- `api/services/ollama.py`: `DEFAULT_TIMEOUT` read 30s → 90s, `STREAM_TIMEOUT` read 30s → 60s
  (qwen2.5:7b on CPU needs longer reasoning window with 9-tool spec).
- `api/main.py`: version 0.4.2 → 0.4.3.

### Verified E2E
```
Direct executor (no LLM):
  write_file:     PASS — 54 bytes written, file on disk
  read_file:      PASS — content read back correctly
  generate_image: PASS — fal.ai URL returned in 0.14s

Via LLM (qwen2.5:7b CPU, fresh agent + clean memory):
  write_file:     PASS — 1 tool call, file persisted
  read_file:      PASS — 1 tool call, content shown to user
  generate_image: PASS — 1 tool call, image rendered in chat
```
Image: `https://v3b.fal.media/files/b/0a98c587/u3AboBYTbIjV-ARxPmVF0.jpg`

---

## [0.4.2] — 2026-05-04 (Day 24) — Tool Expansion: fal.ai + sandboxed file system

### Added
- **`generate_image` tool** — fal.ai FLUX schnell integration
  - Endpoint: `POST https://fal.run/fal-ai/flux/schnell`
  - ~$0.003/image, ~3-8s latency, returns hosted URL (v3b.fal.media)
  - Schema: `prompt` (required), `image_size` (enum 6 sizes), `num_images` (1-4)
  - Free tier: max 100 calls/day per tenant
- **`read_file` tool** — sandboxed file read from `/app/workspace`
  - Path traversal blocked via `Path.resolve()` + `relative_to(WORKSPACE_DIR)`
  - 50KB content cap, supports directory listing
- **`write_file` tool** — sandboxed file write to `/app/workspace`
  - Same path traversal protection, 200KB content cap
  - Auto-creates parent directories
- **`api/config.py`**: `FAL_KEY` (Optional[str]) + `WORKSPACE_DIR` (default `/app/workspace`)
- **`docker-compose.yml`**: `FAL_KEY: ${FAL_KEY}` env + `./data/workspace:/app/workspace` volume

### Fixed
- **Version drift**: `/health` and `/` endpoints hardcoded `"0.4.1"` despite `app.version="0.4.2"`.
  Both now read from `app.version` (single source of truth).
- **Tools invisible to LLM**: new tools were in `TOOL_REGISTRY` + `skills.json` but absent from
  `agents.json` `core_brain.default_tools`. Fixed by adding all 3.

### Changed
- `api/services/tool_executor.py`: 3 new handler functions, `_resolve_workspace_path()` helper,
  `FAL_FLUX_ENDPOINT` + `FAL_VALID_SIZES` constants.
- `config/skills.json`: 3 new MCP-compatible skill registrations.
- `config/agents.json`: `core_brain.default_tools` now includes all 8 tools.
- `api/main.py`: version 0.4.1 → 0.4.2.

---

## [0.4.1-chat] — 2026-05-03 (Day 22) — Chat UI

### Added
- **`frontend/chat.html`** — Standalone React 18 Chat UI (no build step, single HTML file)
  - Dark sci-fi design system: `--bg-0: #07100e`, `--orange: #ff8a24`, `--green: #2fe39a`
  - Fonts: Orbitron (display/brand) + Inter (body) + JetBrains Mono (mono/labels)
  - Boot sequence animation with sessionStorage guard (skip after first visit)
  - Login/Register tabs — auto-generates `tenant_slug` from workspace name
  - Auto-create default agent on first login (stored in `localStorage`)
  - SSE streaming chat: handles `type: start/chunk/done/error` events via `fetch` + `ReadableStream`
  - AbortController-based stop button during streaming
  - Conversation persistence in `localStorage` (last 60 messages)
  - Conversation history sidebar (last 20 sessions)
  - Responsive — sidebar hidden on mobile (<640px)
  - Logout with full `localStorage` cleanup
- **`docs/USER_GUIDE.md`** — Private user guide + credentials reference for Fahmi
  - Quick reference table: URLs, SSH, Admin Key, GitHub
  - Step-by-step: register → login → chat
  - curl examples for all key API endpoints
  - Admin monitoring commands
  - VPS SSH + Docker commands
  - Week 3 roadmap + API keys to set up
  - Troubleshooting table
- **`docs/nginx_app_migancore.conf`** — nginx vhost config for `app.migancore.com`

### Deployed
- `https://app.migancore.com` — Live ✅
  - nginx vhost: `/www/server/panel/vhost/nginx/app.migancore.com.conf`
  - SSL: Let's Encrypt (certbot webroot), valid until 2026-08-01
  - Static files: `/opt/ado/frontend/chat.html` (40KB)
  - HTTP → HTTPS 301 redirect
  - DNS A record: `app.migancore.com → 72.62.125.6` ✅

### No API changes, no DB migration

---

## [0.4.1] — 2026-05-03 (Day 21)

### Added
- **Auto-rerun Synthetic Generation** (`services/synthetic_pipeline.py`)
  - `start_synthetic_generation(target_pairs=None)` — new optional parameter
  - `run_synthetic_generation(run_id, auto_target=None)` — loops multiple rounds until
    DB total synthetic pairs >= `auto_target`. Backward compatible: `None` = single run.
  - `_count_synthetic_pairs()` — `SELECT COUNT(*) FROM preference_pairs WHERE source_method LIKE 'synthetic%'`; counts across all runs including previous sessions
  - New Redis keys: `synthetic:round`, `synthetic:cumulative_stored`, `synthetic:target_pairs`
  - Safety: `zero_yield_abort` — if a full round stores 0 pairs (Ollama down?), stops with `status="error"` instead of looping forever
  - New `status` value: `"done_target_reached"` — distinguishes auto-rerun completion from single-run completion
  - New run_id per round for traceability in logs

### Changed
- **`GET /v1/admin/synthetic/status`** response now includes:
  - `round` — current round number (1-based)
  - `cumulative_stored` — total pairs stored across all rounds this session
  - `target_pairs` — auto-rerun target (null in single-run mode)
- **`POST /v1/admin/synthetic/start`** (`routers/admin.py`):
  - Accepts optional JSON body: `{"target_pairs": 1000}`
  - Response includes `mode` ("auto_rerun" | "single_run") and `target_pairs`
  - No body = single-run mode (original behavior, backward compatible)
- Version bumped: `0.4.0` → `0.4.1`

### Usage
```bash
# Auto-rerun until 1000 pairs (set and forget):
curl -X POST -H "X-Admin-Key: <key>" -H "Content-Type: application/json" \
     -d '{"target_pairs": 1000}' https://api.migancore.com/v1/admin/synthetic/start

# Single run (original behavior):
curl -X POST -H "X-Admin-Key: <key>" https://api.migancore.com/v1/admin/synthetic/start

# Stop anytime:
curl -X POST -H "X-Admin-Key: <key>" https://api.migancore.com/v1/admin/synthetic/stop
```

---

## [0.4.0] — 2026-05-03 (Day 20)

### Added
- **Context Window Management** (`routers/chat.py`) — token-budget trimming before Ollama call
  - `MAX_HISTORY_LOAD = 10` — load 10 messages from DB (was 5)
  - `MAX_HISTORY_TOKENS = 1500` — history token budget cap
  - `MAX_MSG_CONTENT_CHARS = 800` — per-message content cap before token counting
  - `CHARS_PER_TOKEN = 3.5` — conservative estimate for Bahasa Indonesia + English mixed
  - `_estimate_tokens(text)` — heuristic token counter (no tokenizer dependency)
  - `_trim_history_to_budget(history)` — Pass 1: cap each message at 800 chars; Pass 2: drop oldest until total history < 1500 tokens
  - Logs `chat.history_trimmed` with original/kept/dropped counts

### Changed
- **Explicit `num_ctx=4096`** in all Ollama call sites:
  - `routers/chat.py` — sync chat options: `{"num_predict": 1024, "temperature": 0, "num_ctx": 4096}`
  - `routers/chat.py` — SSE stream options: `{"num_predict": 1024, "num_ctx": 4096}`
  - `services/director.py` — default options: `{"num_predict": 1024, "temperature": 0, "num_ctx": 4096}`
  - *Previously unset → Ollama default ~2048 → silent overflow risk with tool outputs*
- **`_memory_search()` timeout** (`services/tool_executor.py`):
  - Added `asyncio.wait_for(search_semantic(...), timeout=2.0)` — prevents tool loop blocking
  - `TimeoutError` → falls through to Redis K-V fallback (no error response to LLM)
  - `source` field now returns `"qdrant_hybrid"` (was `"qdrant_semantic"`) to reflect Day 18 hybrid upgrade
  - Added `"score"` field to each result for transparency
- Version bumped: `0.3.9` → `0.4.0`

### Fixed
- **Tool executor Qdrant timeout**: `memory_search` tool could block indefinitely if Qdrant was slow.
  Now has 2.0s timeout with graceful Redis fallback — matches retrieval.py timeout behavior (1.5s).
- **Silent context overflow**: `num_ctx` was never set explicitly. Ollama default (likely 2048) could be exceeded
  by conversations with tool outputs (~2500 tokens worst case). Now explicit `num_ctx=4096` at all call sites.
- **History load limit inconsistency**: DB was loading 5 messages but router processed 10 worth of context.
  Unified to `MAX_HISTORY_LOAD = 10` with token budget trimming as safety valve.

### Architecture Notes (Day 20 decisions)
- `num_ctx=4096` chosen over larger values: CPU inference time grows quadratically; 4096 safe for MVP
  Budget: system 300 + history 1500 + user message 100 + response 1024 + buffer 1172 = 4096 ✅
- Token budget trim is conservative: if trimming occurs frequently, raise `MAX_HISTORY_TOKENS`
- 2.0s Qdrant timeout in tool executor (vs 1.5s in retrieval.py): tool loop has explicit fallback path

---

## [0.3.9] — 2026-05-03 (Day 19)

### Added
- **Synthetic DPO Generator** (`services/synthetic_pipeline.py`, `services/seed_bank.py`) — NEW FILES
  - Triple-Source Seed Architecture: MighanTech3D NPC personas + SIDIX topic taxonomy (framing only) + SynPO research patterns
  - 120 diverse seed messages across 7 domains (Creative, Research, SEO, Social, Design, Ops, General AI)
  - Full CAI-gated pipeline: generate (T=0.7) → critique → revise → store
  - Redis progress tracking: `synthetic:status/run_id/total/processed/stored/started_at`
  - Graceful cancellation: `asyncio.CancelledError` → status="cancelled" in Redis
  - Expected yield: ~50-60 pairs per run (40-50% filter rate)
  - `source_method="synthetic_seed_v1"` tag for training data provenance separation
- **Admin Synthetic Endpoints** (`routers/admin.py`)
  - `POST /v1/admin/synthetic/start` — trigger generation, returns run_id
  - `GET /v1/admin/synthetic/status` — Redis counters + progress_pct + is_running
  - `POST /v1/admin/synthetic/stop` — cancel running task (409 if nothing running)

### Changed
- Version bumped: `0.3.8` → `0.3.9`
- `_store_preference_pair()` (`services/cai_pipeline.py`):
  - `source_message_id` is now optional (`None` accepted for synthetic pairs)
  - Added `source_method: str = "cai_pipeline"` parameter — replaces hardcoded value

### Safety Notes (Day 19 research)
- SIDIX topic content NOT used as seeds — only question framing patterns extracted
  Reason: SIDIX corpus has known hallucination issues; importing answers would transfer them into MiganCore
- `source_method` tag allows filtering synthetic pairs at training time if needed
- No DB migration required — `source_method` column existed since Day 17

---

## [0.3.8] — 2026-05-03 (Day 18)

### Added
- **Hybrid Search BM42** (`services/vector_memory.py`, `services/embedding.py`)
  - Dense + BM42 sparse vectors with Reciprocal Rank Fusion (RRF) via Qdrant Query API
  - Expected recall improvement: **+30–50%** for proper nouns, names, dates, product terms
  - `_is_hybrid_collection()` — schema detection for migration gating
  - `_create_hybrid_collection()` — named "dense" (768-dim Cosine) + named "sparse" (BM42)
  - `_migrate_collection_to_hybrid()` — zero-loss auto-migration (scroll → delete → recreate → re-upsert)
  - `_search_hybrid()` — `query_points()` with dual Prefetch + `FusionQuery(Fusion.RRF)`
  - `_search_dense_only()` — legacy `client.search()` fallback (named "dense" → unnamed)
  - `has_sparse` payload flag on every indexed turn pair
- **BM42 Sparse Embedding** (`services/embedding.py`)
  - `get_sparse_model()` — singleton `SparseTextEmbedding`, returns None on failure (graceful)
  - `embed_sparse_document(text)` — uses `model.embed()` for indexing
  - `embed_sparse_query(text)` — uses `model.query_embed()` for queries (**MUST NOT** use `embed()`)
- **BM42 Pre-warm at Startup** (`main.py`)
  - `await get_sparse_model()` added as step 4 in `lifespan()` — avoids cold start on first chat
- **fastembed Named Volume** (`docker-compose.yml`)
  - `fastembed_cache:` — persists 90MB BM42 ONNX model across Docker rebuilds

### Changed
- Version bumped: `0.3.7` → `0.3.8`
- `ensure_collection()` — idempotent, auto-detects old schema, auto-migrates on first access
- `index_turn_pair()` — `asyncio.gather()` concurrent dense+sparse embed computation
- `search_semantic()` — hybrid first, exception → dense fallback, all exceptions → `[]`
- `docker-compose.yml` — Qdrant upgraded `v1.9.0` → `v1.12.0` (required for Query API)

### Research Notes (Day 18, 2025-2026 sources)
- Qdrant Query API (Prefetch + FusionQuery.RRF) requires **≥ v1.10.0** — v1.9.0 does NOT support hybrid
- BM42 `query_embed()` vs `embed()`: different token weighting — queries MUST use `query_embed()`, documents use `embed()`
- fastembed `SparseTextEmbedding` available since v0.3.0 — already in our dependency tree
- Zero-loss migration: `chunk_text` payload used to recompute sparse vectors for all existing points
- Graceful degradation chain: hybrid → dense-only → `[]` — no regression if BM42 unavailable
- Named volume `fastembed_cache`: cache hit = 108,100 it/s (instant vs ~4s re-download)

---

## [0.3.7] — 2026-05-03 (Day 17)

### Added
- **Admin Monitoring Endpoints** (`routers/admin.py`) — NEW FILE
  - `GET /v1/admin/stats` — CAI flywheel health: pair count, unused pairs, avg judge score,
    score distribution, 24h/7d collection rates, training readiness assessment with progress %
  - `GET /v1/admin/preference-pairs` — paginated pair listing with filters:
    `score_max`, `unused_only`, `limit`, `offset` + `has_more` pagination
  - `GET /v1/admin/export` — streams JSONL in Unsloth/TRL DPO-compatible format
    (`{"prompt": "...", "chosen": "...", "rejected": "..."}`), ordered by lowest score first
  - Auth: `X-Admin-Key` header → checked against `settings.ADMIN_SECRET_KEY`
    (503 if unconfigured, 401 if wrong key)
  - Training readiness thresholds (from Day 17 research, arxiv 2502.14560):
    `not_ready` < 500 pairs | `approaching` 500-999 | `ready` 1000+ | `ideal` 2000+
- **PreferencePair ORM model** (`models/preference_pair.py`) — NEW FILE
  - Mirrors `init.sql` preference_pairs schema exactly
  - Registered in `models/__init__.py`
- **`ADMIN_SECRET_KEY` setting** (`config.py`) — new optional env var

### Changed
- Version bumped: `0.3.6` → `0.3.7`
- `models/__init__.py` — exports `PreferencePair`
- `main.py` — admin router wired

### Research Notes (Day 17 research via research agent, 2025-2026 sources)
- DPO minimum: 500 pairs for any signal, 1000 for reliability, 2000 for ideal (arxiv 2502.14560)
- **SimPO > DPO for first run**: no reference model, noise-tolerant, +6.4pts AlpacaEval 2 (arxiv 2405.14734)
- RunPod cost: ~$2-4 per Qwen2.5-7B QLoRA training run (RTX 4090, ~2hr)
- Implicit signals: retry rate = strongest proxy, needs 10-20 instances to be reliable (CHI 2025)
- HyDE/query rewriting: SKIP — CPU latency penalty too high on 7B
- Hybrid search (BM42): good ROI, 1-day engineering → planned for Day 18

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
