# MIGANCORE — AGENT HANDOFF MASTER
**Versi Dokumen:** 2026-05-05 (Day 47 start)
**Dibuat oleh:** Claude Sonnet 4.6 — QA Sprint 1 session
**Status API:** v0.5.14 (last deployed Day 46)
**Tujuan:** Dokumen tunggal yang boleh dibaca agent/engineer mana pun tanpa kehilangan konteks. Update tiap sesi signifikan.

> ⚠️ **DOKUMEN INI STALE — TERAKHIR UPDATE DAY 47 (v0.5.14)**
> Untuk state terbaru (Day 60+, v0.5.18, migancore:0.3), baca urutan ini:
> 1. **`docs/PRODUCT_BRIEF_ALIGNMENT.md`** — visi founder + alignment matrix + gap analysis + roadmap Day 61-90 (WAJIB BACA PERTAMA)
> 2. **`docs/DAY60_MANDATORY_PROTOCOL.md`** — state Day 60, findings, 118 lessons, Cycle 3 results
> 3. **`docs/ENVIRONMENT_MAP.md`** — VPS topology, container map, jangan salah path
> Baru baca dokumen ini untuk konteks history Day 1–47.

> **WAJIB BACA SEBELUM KERJA.** Jika ada konflik antara dokumen ini dan kode aktual: **percayai kode, update dokumen ini**.
> Dokumen terkait: `CONTEXT.md` (detail per-day, stale di v0.5.0) · `BULAN2_PLAN.md` · `QA_FULLREVIEW_2026-05-05.md` · `CHANGELOG.md`

---

## RINGKASAN EKSEKUTIF

MiganCore adalah **Autonomous Digital Organism (ADO)** — sistem AI self-evolving yang berjalan di VPS sendiri, bukan cloud proxy ke model besar. Otak utama adalah Qwen2.5-7B yang berjalan via Ollama, disupport oleh FastAPI + PostgreSQL + Redis + Qdrant. Pemilik proyek: **Fahmi Ghani** (Founder & Owner, PT Tiranyx Digitalis Nusantara — brand: Tiranyx, non-technical visioner).

**Saat ini (Day 47 start):**
- API v0.5.14 live di `api.migancore.com`
- Chat UI live di `app.migancore.com` (multimodal: text + image attach + mic)
- 23 tools aktif via tool executor
- DPO flywheel: ±455 pairs (target 500 untuk trigger SimPO Cycle 1)
- Smithery.ai listing live: `smithery.ai/server/fahmiwol/migancore`
- Sprint 1 QA fixes: 6 critical/high security bugs sudah dipatch
- 50 lessons learned kumulatif

---

## CURRENT STATE SNAPSHOT

| Field | Value |
|-------|-------|
| API Version | **v0.5.14** |
| Phase | Bulan 2 Week 6 → Week 7 |
| Sprint Day | **Day 47** |
| DPO Pool | **~455 pairs** (synthetic ±430, CAI ±25) — target 500 untuk Cycle 1 |
| Bulan 2 Budget | **$1.44 / $30** (4.8% spent) |
| Tools | **23 tools** aktif (tool_cache Redis, ONAMIX MCP singleton) |
| Domains | `migancore.com` (landing) · `api.migancore.com` · `app.migancore.com` |
| Smithery | ✅ LIVE PUBLIC `smithery.ai/server/fahmiwol/migancore` |
| QA Sprint 1 | ✅ DONE (6 fixes, committed `31acdea`) |
| QA Sprint 2 | 🟡 PENDING (training pipeline fixes before Cycle 1) |
| QA Sprint 3 | 🔴 PENDING (beta onboarding fixes) |
| Lessons Kumulatif | **50** |

---

## STACK ARSITEKTUR

```
Internet → nginx (aaPanel, Let's Encrypt SSL)
              ↓ api.migancore.com:443 → port 18000
              ↓ app.migancore.com:443 → /opt/ado/frontend/ (static)
              ↓ migancore.com:443 → /www/wwwroot/migancore.com/ (landing)

API (FastAPI, Python 3.11)
  ├── LangGraph StateGraph director (ReAct loop, MAX_TOOL_ITERATIONS=5)
  ├── OllamaClient → Ollama (port 11434) → Qwen2.5-7B Q4_K_M (7-14 tok/s CPU)
  ├── Tool Executor (23 tools, policy check, Redis cache TTL)
  ├── ONAMIX MCP Client (stdio singleton, subprocess, /opt/sidix/tools/)
  ├── CAI Pipeline (critique+revise, 50% sample rate, Kimi+Gemini quorum judge)
  ├── Synthetic Pipeline (120 seeds/round, auto-rerun to target)
  ├── Distillation Pipeline (4 teachers: Kimi/Claude/GPT/Gemini — 0 pairs, CPU bottleneck)
  └── Conv Summarizer (2900-tok trigger, local Qwen 7B)

Storage:
  ├── PostgreSQL 16 + pgvector (+ RLS row-level security per tenant)
  ├── Redis (memory K-V, tool cache, rate limit, synthetic status, JWT revocation)
  ├── Qdrant v1.12.0 (hybrid BM42 sparse + dense 768-dim + RRF fusion)
  └── Letta 0.6.0 (PASSIVE STORAGE ONLY — persona/mission/knowledge blocks)

Training (not yet triggered):
  ├── training/export_dataset.py → JSONL (Unsloth/TRL format)
  ├── training/train_simpo.py (SimPO, APO identity loss λ=0.1, QLoRA 4-bit)
  └── training/convert_gguf.py → Q4_K_M GGUF for Ollama hot-swap

VPS: Ubuntu 22.04, 32GB RAM, 8 core, 400GB, IP: [REDACTED — lihat credentials_private.md]
```

---

## KOMPONEN TERVERIFIKASI (E2E TESTED)

### Layer 1 — Auth System (Day 1–5)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /v1/auth/register` | ✅ | Argon2id, tenant auto-create |
| `POST /v1/auth/login` | ✅ | RS256 JWT, access 15m + refresh 7d |
| `POST /v1/auth/refresh` | ✅ | **JWT silent refresh v0.5.12** — auto-retry on 401, single-flight lock |
| `POST /v1/auth/logout` | ✅ | Token revocation |
| `GET /v1/auth/me` | ✅ | Current user info |
| Rate limiting | ✅ | 5/min login, 10/min register, RedisStorage multi-worker |

### Layer 2 — Agent System (Day 6, 10–11, 29–31)
| Feature | Status | Notes |
|---------|--------|-------|
| `POST /v1/agents` | ✅ | Create agent, tenant-scoped |
| `POST /v1/agents/{id}/spawn` | ✅ | Genealogy tree, MAX_GENERATION_DEPTH=5 |
| `GET /v1/agents/{id}/children` | ✅ | Direct children |
| Spawn UI | ✅ | chat.html sidebar — Level 5 visible! |
| Genealogy D3.js | ✅ | `/admin/` Lineage tab, force-directed graph |
| 3 Mode Templates | ✅ | customer_success / research_companion / code_pair |

### Layer 3 — Chat System (Day 6–11, 20, 36, 39–40)
| Feature | Status | Notes |
|---------|--------|-------|
| `POST /v1/agents/{id}/chat` | ✅ | Sync, LangGraph director, quota check |
| `POST /v1/agents/{id}/chat/stream` | ✅ | SSE, heartbeat 15s, tool execution hybrid (v0.5.6 Day 39 fix) |
| SSE nginx config | ✅ | `proxy_read_timeout 600s`, buffering off (Day 36 fix) |
| Retry button + friendly errors | ✅ | Day 36 — 4 error types mapped |
| 3-state status hierarchy | ✅ | Connecting → Thinking → Generating (Day 36) |
| Cancel propagation | ✅ | asyncio.CancelledError → Ollama abort (Day 36) |
| **[H8 FIXED]** Stream quota check | ✅ | Sprint 1 — stream sekarang enforce daily limit |
| **[H10 FIXED]** OllamaClient leak | ✅ | Sprint 1 — `async with OllamaClient()` di Phase B |
| Context window | ✅ | `num_ctx=4096`, `MAX_HISTORY_TOKENS=1500`, `MAX_MSG_CONTENT_CHARS=800` |
| Conv summarizer | ✅ | v0.5.14 Day 45 — 2900-tok trigger, Redis cache, sleep-time |

### Layer 4 — Memory System
| Component | Status | Notes |
|-----------|--------|-------|
| Redis K-V (Tier 1) | ✅ | `mem:{tenant}:{agent}:{namespace}:{key}`, 30d TTL |
| Qdrant hybrid (Tier 2) | ✅ | BM42 + dense 768-dim + RRF, v1.12.0, per-agent collections |
| Letta blocks (Tier 3) | ✅ | persona/mission/knowledge — PASSIVE STORAGE ONLY |
| Tool cache | ✅ | v0.5.12 Day 43 — Redis TTL per-tool, 1400x speedup empirical |
| Memory pruner | ✅ | Daily daemon |

### Layer 5 — Tools (23 total, Day 8–46)
| Tool | Status | Source | Notes |
|------|--------|--------|-------|
| `memory_write` | ✅ | Internal | Redis K-V |
| `memory_search` | ✅ | Internal | Qdrant hybrid → Redis fallback |
| `web_search` | ⚠️ DEPRECATED | Internal | → gunakan `onamix_search` |
| `python_repl` | ✅ | Internal | subprocess sandbox, **[C4 FIXED]** eval/exec sekarang blocked |
| `spawn_agent` | ✅ | Internal | Genealogy-aware |
| `http_get` | ✅ | Internal | Raw HTTP fetch |
| `read_file` | ✅ | Internal | Sandboxed |
| `write_file` | ✅ | Internal | Sandboxed |
| `generate_image` | ✅ | fal.ai | Image generation |
| `text_to_speech` | ✅ | ElevenLabs | TTS v0.4.5 |
| `analyze_image` | ✅ | Gemini Vision | v0.5.4 Day 38 |
| `stt` (speech-to-text) | ✅ | Scribe/ElevenLabs | v0.5.4 Day 38 |
| `web_read` | ✅ | Jina.ai | Full page fetch — v0.5.9 Day 41 |
| `export_pdf` | ✅ | WeasyPrint | HTML → PDF — v0.5.9 Day 41 |
| `export_slides` | ✅ | Marp → PPTX | Markdown → slides — v0.5.9 Day 41 |
| `onamix_search` | ✅ | ONAMIX MCP | Multi-engine: ddg/brave/bing/wikipedia/multi (DEFAULT) |
| `onamix_get` | ✅ | ONAMIX MCP | Fetch URL via proxy |
| `onamix_scrape` | ✅ | ONAMIX MCP | Scrape structured data |
| `onamix_post` | ✅ | ONAMIX MCP | POST request |
| `onamix_crawl` | ✅ | ONAMIX MCP | Site crawl |
| `onamix_links` | ✅ | ONAMIX MCP | Extract links |
| `onamix_history` | ✅ | ONAMIX MCP | Browse history |
| `onamix_multi` | ✅ | ONAMIX MCP | Parallel fetch |

**KRITIS:** `core_brain.default_tools` di `config/agents.json` WAJIB sinkron dengan tools di atas. Day 46: fixed drift yang menyebabkan empty bubble.

### Layer 6 — CAI + Training Pipeline
| Component | Status | Notes |
|-----------|--------|-------|
| CAI pipeline | ✅ | critique+revise, 50% sample, Kimi+Gemini quorum judge (Day 37) |
| Synthetic generator | ✅ | 120 seeds/round, auto-rerun target_pairs=1000 |
| Magpie 300K seed pool | ✅ | v0.5.4 Day 38 — selectable via `SEED_SOURCE=magpie_300k` |
| APO identity loss pre-wire | ✅ | v0.5.4 — λ=0.1, NOT yet triggered (waiting Cycle 1) |
| export_dataset.py | ✅ | JSONL export, DPO/SimPO format |
| train_simpo.py | ✅ | QLoRA 4-bit, SimPO, beta=2.5, apo_zero loss, save_steps=50 |
| convert_gguf.py | ✅ | Q4_K_M output for Ollama hot-swap |
| Identity eval | ✅ | 20 prompts, cosine sim ≥0.85 gate |
| DPO pool | 🟡 ~455 pairs | **Target: 500 untuk trigger Cycle 1** |

### Layer 7 — Admin & Monitoring
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /v1/admin/stats` | ✅ | Pair count, readiness, 24h/7d rate |
| `GET /v1/admin/preference-pairs` | ✅ | Paginated, filters |
| `GET /v1/admin/export` | ✅ | JSONL stream |
| `POST /v1/admin/synthetic/start` | ✅ | Single/auto-rerun mode |
| `GET /v1/admin/synthetic/status` | ✅ | **[M5 FIXED]** stale "running" auto-corrected |
| `POST /v1/admin/synthetic/stop` | ✅ | Cancel |
| `POST /v1/admin/distill/start` | ✅ | 4 teachers, **[H18 PENDING]** no asyncio.Lock |
| `GET /v1/admin/genealogy` | ✅ | System-wide agent tree |
| Admin auth | ✅ | **[H1 FIXED]** `secrets.compare_digest()` |

### Layer 8 — Teacher API (Day 28)
| Teacher | Model | Status | Pricing |
|---------|-------|--------|---------|
| Anthropic Claude | claude-sonnet-4-5 | ✅ | $3/$15 /1M tok |
| Moonshot Kimi | kimi-k2.6 | ✅ | $0.60/$2.50 /1M tok |
| OpenAI GPT | gpt-4o | ✅ | $2.50/$10 /1M tok |
| Google Gemini | gemini-2.5-flash | ✅ **[C3 FIXED]** | $0.075/$0.30 /1M tok |
| Distillation pairs | **0 pairs produced** | ⚠️ | Ollama CPU bottleneck = student step terlalu lambat |

### Layer 9 — MCP Server (Day 26–27)
- ✅ Streamable HTTP transport (spec 2025-03-26) di `api.migancore.com/mcp/`
- ✅ JWT auth
- ✅ 23 tools + 4 resources (templates)
- ✅ Smithery.ai listing LIVE

---

## QA STATUS — DARI FULLREVIEW 2026-05-05

**Full report:** `docs/QA_FULLREVIEW_2026-05-05.md` (65 issues total)

### ✅ Sprint 1 — SELESAI (commit `31acdea`, 2026-05-05)
| ID | Fix | File |
|----|-----|------|
| C4 | `eval()`/`exec()`/`compile()` sekarang raise PolicyViolation | `api/services/tool_policy.py:201` |
| H1 | Admin key: `secrets.compare_digest()` gantikan `==` | `api/routers/admin.py:72` |
| C3 | Gemini API key dipindah ke header `x-goog-api-key` | `api/services/teacher_api.py:292` |
| H10 | Phase B OllamaClient: `async with` — tidak ada httpx leak lagi | `api/routers/chat.py:483` |
| H8 | `chat_stream` sekarang enforce tenant daily quota | `api/routers/chat.py:329` |
| M5 | Redis stale "running" auto-correct ke "error" saat restart | `api/services/synthetic_pipeline.py:464` |

### 🟡 Sprint 2 — SEBELUM CYCLE 1 TRAINING (Day 47-49, target ~Day 39-40)
| ID | Severity | Issue | File |
|----|----------|-------|------|
| H15 | HIGH | 50 identity anchors belum lengkap (baru 5/50) | `training/export_dataset.py` |
| H16 | HIGH | Tidak ada dataset format validation sebelum SimPO | `training/train_simpo.py` |
| H17 | HIGH | APO label masking: prompt tokens tidak di-mask | `training/train_simpo.py` |
| H18 | HIGH | Race condition di `start_distillation` — tidak ada asyncio.Lock | `api/services/distillation.py` |
| H19 | HIGH | Judge cost tidak dihitung ke budget cap distillation | `api/services/distillation.py` |
| M13 | MEDIUM | Warning jika dataset < target di training | `training/train_simpo.py` |
| M14 | MEDIUM | Dead code `distill_query` | `api/services/distillation.py` |

### 🔴 Sprint 3 — SEBELUM BETA ONBOARDING (Day 50+)
| ID | Severity | Issue | File |
|----|----------|-------|------|
| C1 | CRITICAL | VPS IP hardcoded di `convert_gguf.py:125` — di git history | `training/convert_gguf.py` |
| C2 | CRITICAL | Password `changeme` di `migrations/007_create_app_user.sql` — di git | `migrations/007_create_app_user.sql` |
| H3 | HIGH | JWT refresh token harus HttpOnly cookie | `api/routers/auth.py` |
| H7 | HIGH | Default credentials `changeme` / `test-secret-key` di config.py | `api/config.py` |
| H13 | HIGH | RLS tidak diaktifkan di `api_keys` table | `migrations/` |
| H14 | HIGH | Migration numbering conflict (ada dua migration bernomor sama) | `migrations/` |
| M1 | MEDIUM | Pagination tanpa `max_limit` constraint | routers |
| M7 | MEDIUM | UUID parsing tidak konsisten antar router — buat helper | routers |
| M23 | MEDIUM | Conversation history tersimpan di localStorage (data sensitivity) | `frontend/chat.html` |

### Sprint 4 — BULAN 2 WEEK 7-8
Lihat `docs/QA_FULLREVIEW_2026-05-05.md` Section 7 Sprint 4 untuk full list.

---

## ARCHITECTURE DECISIONS (FINAL — JANGAN UBAH TANPA DELIBERASI)

| Decision | Pilihan | Alasan |
|----------|---------|--------|
| Primary LLM | Qwen2.5-7B Q4_K_M via Ollama | CPU-only VPS, ADO vision (self-hosted brain) |
| Training algorithm | SimPO (BUKAN DPO) | Noise-tolerant, no reference model, +6.4pts AlpacaEval 2 (arxiv 2405.14734) |
| Identity preservation | APO loss λ=0.1 + 50 anchor prompts | Cegah persona drift saat fine-tuning (arxiv 2408.06266) |
| CAI judge | Kimi K2.6 + Gemini Flash **quorum** | Reduce self-bias 30%, lebih murah dari Claude judge |
| Synthetic seeds | Magpie 300K (via `SEED_SOURCE=magpie_300k`) | In-distribution, diverse, better quality gap vs hardcoded seeds |
| Memory: Tier 1 | Redis K-V | Fast, TTL built-in |
| Memory: Tier 2 | Qdrant v1.12.0 BM42+dense+RRF | +30-50% recall proper nouns/names (hybrid > dense-only) |
| Memory: Tier 3 | Letta blocks | Persona persistence — PASSIVE STORAGE ONLY |
| Letta usage | HANYA blocks API | Qwen2.5-7B Q4 TIDAK support Letta tool calls — jangan panggil `agents.messages.create()` |
| Orchestration | LangGraph StateGraph | Controllable, stateful, circuit breaker MAX_TOOL_ITERATIONS=5 |
| Context window | num_ctx=4096 explicit | Ollama default ~2048 = silent truncation |
| History budget | MAX_HISTORY_TOKENS=1500 | Sisakan ruang untuk system prompt + response |
| Tool calling Ollama | stream=False hardcoded | Ollama tool calling TIDAK support streaming |
| REPL sandbox | subprocess + import blacklist | subprocess = real process boundary |
| Judge architecture | Kimi+Gemini quorum (BUKAN Ollama self-judge) | 30% less bias, 10x faster, $0.10 per 500 pairs |
| Distillation path | Secondary path saja | Ollama CPU bottleneck pada student step (10-90s/call) — gunakan synthetic generator sebagai primary |
| CAI sample rate | 50% | CPU resource management |
| Score threshold RAG | 0.65 (BUKAN 0.55) | Optimal untuk Bahasa Indonesia pada multilingual MPNet |
| Top-k inject | 3 (BUKAN 5) | >3 chunks confuses 7B models (Mem0 production finding) |
| Episodic sort | By relevance score | Recency-sorted degrades accuracy 30% |
| MCP transport | Streamable HTTP (spec 2025-03-26) | BUKAN HTTP+SSE deprecated |
| Onboarding UX | Two-question + dynamic starter cards | Multi-template picker DEPRECATED Q1 2026 (Cursor/Claude killed it) |
| Tool registration | skills.json (global) + agents.json (per-agent) | Drift antara dua file = empty bubble (Lesson #48) |

---

## ANTI-PATTERNS (DILARANG)

- ❌ **Replace Ollama dengan cloud LLM** untuk chat utama — melanggar ADO vision "self-hosted brain"
- ❌ **Invoke `letta.agents.messages.create()`** — Qwen2.5-7B Q4 tidak support
- ❌ Aktifkan Celery — disabled intentionally (RAM terlalu mahal, asyncio.create_task cukup)
- ❌ Tambah Langfuse ke default profile — defer (structlog sudah cukup)
- ❌ Commit `.venv/` ke git
- ❌ Duplicate `get_db` — pakai `deps.db.get_db` EXCLUSIVELY, hapus dari `models/base.py`
- ❌ Skip `set_tenant_context` sebelum query tenant-scoped tables
- ❌ Gunakan `x != secret_key` untuk auth check — WAJIB `secrets.compare_digest()`
- ❌ Taruh API key di URL parameter — selalu gunakan header
- ❌ Buat OllamaClient tanpa `async with` di streaming path — httpx leak
- ❌ Skip quota check di streaming endpoint — security bypass
- ❌ Gunakan BGE-small-en untuk embeddings — English only
- ❌ Gunakan HTTP+SSE untuk MCP transport — gunakan Streamable HTTP
- ❌ Gunakan Qwen2.5-0.5B sebagai CAI judge — fails Chat Hard tasks (<50% accuracy)
- ❌ Block HTTP response untuk critique/revise — always fire-and-forget
- ❌ Sort episodic retrieval by timestamp — sort by relevance
- ❌ Inject >3 episodic chunks — 7B overwhelmed
- ❌ Gunakan score_threshold <0.65 untuk RAG injection
- ❌ Trigger training sebelum /v1/admin/stats menunjukkan ≥500 unused_pairs
- ❌ Downgrade Qdrant di bawah v1.10.0 — hybrid Query API butuh ≥v1.10.0
- ❌ Gunakan `embed()` untuk BM42 queries — WAJIB `query_embed()` (asymmetric)
- ❌ Hapus `chunk_text` dari Qdrant payload — ini migration escape hatch
- ❌ Update skills.json tapi lupa update agents.json — drift = empty bubble (Lesson #48)
- ❌ Gunakan `web_search` tool — DEPRECATED, gunakan `onamix_search`
- ❌ Set `num_ctx` > 8192 tanpa benchmark — CPU inference O(n²)
- ❌ Import SIDIX QA corpus sebagai seed data — hallucination transfer risk
- ❌ Jalankan distillation `target_pairs=200+` sebelum verify small batch (10 pairs dulu)
- ❌ Deploy tanpa `docker-compose build --build` — cache miss menyebabkan stale image
- ❌ Describe tool action tanpa panggil tool — brain HARUS call tool, bukan narasi
- ❌ Tool description referensikan tool yang tidak tersedia — brain akan emit nothing (Lesson #50)

---

## HANDOFF LOG (Day 1–46)

| Day | Agent | Versi | Summary |
|-----|-------|-------|---------|
| 0 | Kimi | — | Master docs, schema, architecture, sprint plan |
| 1 | Kimi | — | VPS provisioning, Docker, swap, SSH, JWT keys |
| 2 | Kimi | — | DNS + nginx reverse proxy, SSL |
| 3 | Kimi | — | Ollama container, Qwen2.5-7B + 0.5B pulled |
| 4 | Kimi | — | Auth: RS256, Argon2id, refresh rotation, 5 endpoints |
| 5 | Kimi | — | RLS, cross-tenant tests, audit logging |
| 6 | Kimi | — | Agent CRUD, chat endpoint, SOUL.md injection, config |
| 7 | Claude | — | Memory service (Redis K-V), SSE streaming, conversation endpoints |
| 8 | Claude | — | Tool executor (4 tools), ReAct loop, OllamaClient tool calling |
| 7–9 | Kimi CLI | v0.3.0 | Audit + fix, wire director.py, deploy E2E all pass |
| 10 | Kimi CLI | v0.3.1 | Schema sync, agent spawning endpoint |
| 11 | Kimi CLI | v0.3.2 | Safety gates: tool policy 6-class, spawn depth, persona lock, tenant quota, Redis rate limiter |
| 12 | Claude | v0.3.2 | Full audit + handoff, sync repos, fix version, HTTPS |
| 13 | Claude | v0.3.3 | Letta Tier 3: persona blocks, 3-block architecture |
| 14 | Claude | v0.3.4 | Knowledge auto-extraction (Qwen2.5-0.5B, fact_extractor.py) |
| 15 | Claude | v0.3.5 | Constitutional AI pipeline (cai_pipeline.py, 10 principles, DPO flywheel started) |
| 16 | Claude | v0.3.6 | Episodic RAG retrieval (vector_retrieval.py, score=0.65, top-k=3) |
| 17 | Claude | v0.3.7 | Admin monitoring (stats+list+export JSONL), 3 real CAI pairs ditemukan |
| 18 | Claude | v0.3.8 | Hybrid search BM42 + RRF, Qdrant v1.9→v1.12.0, 7 collections migrated |
| 19 | Claude | v0.3.9 | Synthetic DPO generator (seed_bank.py, 120 seeds, generate→critique→revise) |
| 20 | Claude | v0.4.0 | Context window management (num_ctx=4096, token budget trimming) |
| 21 | Claude | v0.4.1 | Auto-rerun synthetic generation (target_pairs=1000, multi-round loop) |
| 22 | Claude | v0.4.1 | Chat UI live (app.migancore.com, React 18, SSE, login/register) |
| 24 | Claude | v0.4.2 | Tool expansion: fal.ai image gen + sandboxed read/write_file |
| 25 | Claude | v0.4.3 | SSE heartbeat fix, generate_image LLM compliance, ALL tools E2E PASS |
| 26 | Claude | v0.4.4 | MCP Streamable HTTP server (api.migancore.com/mcp/), JWT auth, 7 tools |
| 27 | Claude | v0.4.5 | API keys (mgn_live_*), migan CLI, MCP Resources (4 templates), TTS, memory pruner |
| 28 | Claude | v0.4.6 | 4-teacher distillation pipeline + Admin Dashboard (app.migancore.com/admin) |
| 29–35 | Claude Opus | v0.5.0 ⭐ | Spawn UI + Genealogy D3.js + 3 Mode Templates + SimPO scripts + Identity Eval + migancore.com landing LIVE |
| 36 | Claude | v0.5.2 | **Chat UX Sprint**: nginx SSE 60s→600s, Retry button, 3-state status, Cancel propagation |
| 37 | Claude | v0.5.3 | **Teacher API**: CAI Kimi+Gemini quorum judge, Two-Question Onboarding research |
| 38 | Claude | v0.5.4 | **Multimodal input**: analyze_image (Gemini Vision) + STT (Scribe) + Magpie 300K seed loader + APO pre-wire |
| 39 | Claude | v0.5.6 | **Stream tool exec FIX** (hybrid pattern) + chat continuity FIX (Day 38 NameError) + SimPO Q2-2026 hyperparams + Smithery config |
| 40 | Claude | v0.5.8 ⭐ | **MULTIMODAL LIVE**: image attach CompressorJS + mic toggle + tool chips + Smithery PUBLIC listing |
| 41 | Claude | v0.5.9 | **3 new tools**: web_read (Jina) + export_pdf (WeasyPrint) + export_slides (Marp→PPTX). 12 tools. Beta soft-launch ready |
| 42 | Claude | v0.5.10 | **ONAMIX 3 tools** (get/search/scrape) + SimPO Day-42 update (apo_zero + beta=2.5). 15 tools. 5 live patches |
| 43 | Claude | v0.5.12 | **JWT silent refresh** (user-blocking 401 FIXED) + **tool_cache.py** Redis TTL (1400x speedup verified) |
| 44 | Claude | v0.5.13 | **ONAMIX MCP stdio singleton** (subprocess→mcp.ClientSession, 8x speedup) + 6 NEW tools. 23 tools total |
| 45 | Claude | v0.5.14 | **conv_summarizer.py** (2900-tok trigger) + VISION_DISTINCTIVENESS_2026.md strategic compass |
| 46 | Claude | v0.5.14 | **Empty bubble bug FIXED** end-to-end (4 root causes: agents.json drift + HYPERX dispatcher + Wikipedia missing + valid_engines narrow). Wikipedia search NEW |
| **47** | Claude | v0.5.14 | **QA Sprint 1 DONE** (6 security/reliability fixes, commit `31acdea`). Dokumen ini dibuat. |
| **47b** | Claude (parallel session) | v0.5.15 | **Design by Contract for LLM Agents** (`services/contracts.py`): boot validator + safe_task + TaskRegistry watchdog + output contracts. Caught 2 real issues + 1 false-positive in <1s on first deploy. 5-dim QA sweep + full E2E user pipeline VALIDATED. |
| **48** | Claude | v0.5.16 | **QA close-out — all 6 known bugs FIXED**: (1) Cloudflare ENETUNREACH (hyperx dns ipv4first), (2+3) drop 4 stale schemas/handlers (skills.json 23→19), (4) [H2] admin Redis rate limit 10/min, (5) [H5] analyze_image SSRF block, (6) [H7] config.py fail-safe on default creds. 4-test E2E sweep all PASS. **Production SEAMLESS.** |
| **49** | Claude | v0.5.16 | **Cycle 1 SimPO STAGED** + pre-flight ALL GREEN. Critical finding: original 30-day blueprint promised "Seed + Self-Improving v1" but Cycle 1 NEVER triggered. 596 DPO pairs exported (TRL-compatible JSONL). 3 hyperparam refinements (lr 5e-7, padding_free, use_liger_kernel). **AWAITING USER GO** for $0.15-0.50 RunPod trigger. |

---

## ⚡ DAY 49 BREAK STATE (CURRENT — read this first if resuming)

**Single source of truth for resume:** `docs/RESUME_DAY49_TO_DAY50.md` (5-min read).

**Production state:** API v0.5.16 healthy, contracts.boot.ok handlers=19 schemas=19, DPO **601** (and growing).

**Single immediate next action:** User GO/NO-GO for A2 RunPod Cycle 1 trigger.
- Cost: $0.15-0.50 (well under $7 hard cap)
- Time: 15-25 min wall-clock
- Output: First MiganCore-branded adapter `migancore-7b-soul-v0.1`
- Validates: "Self-Improving" half of original 30-day vision

**If user replies "go":** trigger autonomously per `RESUME_DAY49_TO_DAY50.md` § "Trigger command (when GO)".
**If user replies "wait":** standby preserved; pick from Branch C alternative work.

**Key new docs added Day 47-49:**
- `docs/VISION_DISTINCTIVENESS_2026.md` — strategic compass (3 moats, STOP/DOUBLE DOWN, Dream Cycle bold move)
- `docs/QA_FULLREVIEW_2026-05-05.md` — 65-issue catalog (Sprint 1 done, Sprint 2/3 backlog)
- `docs/DAY47_PLAN.md` + `DAY47_RETRO.md` — meta-pattern Contract Assertions
- `docs/DAY48_QA_CLOSEOUT.md` — 6 fixes for production SEAMLESS
- `docs/DAY49_PLAN.md` + `DAY49_PREFLIGHT_RETRO.md` — Cycle 1 staged
- `docs/RESUME_DAY49_TO_DAY50.md` — break-state checkpoint (THIS RESUME ANCHOR)

**Lessons added Day 47-49 (50 → 53 cumulative):**
- #51: Design by Contract for LLM Agents
- #52: 5-dimension QA discipline (backend/frontend/db/tools/integration)
- #53: Parallel sessions are emerging coordination challenge — `git pull` + scan recent commits at session start

**Critical lessons to internalize before any code change:** #45, #48, #50, #51 (see `RESUME_DAY49_TO_DAY50.md` § "Critical Lessons")

---

## BULAN 2 ROADMAP (SISA — revised post-Day-49)

### IMMEDIATE — Day 49 close (USER GATE)
1. ✅ Pre-flight A1 ALL GREEN (this session)
2. 🟡 **USER GO/NO-GO** on A2 Cycle 1 RunPod trigger
3. (If GO) Trigger Cycle 1 → identity eval → hot-swap if PROMOTE
4. (If WAIT) Pick from Branch C alternative work

### Day 50 — Branch A (Cycle 1 PROMOTED)
1. GGUF convert + Ollama hot-swap to `migancore:0.1`
2. A/B 10% traffic split via FastAPI header `X-Model-Variant`
3. Monitor 24h win-rate, error rate, identity drift

### Day 47–49 — Cycle 1 Training Trigger
1. Verifikasi `/v1/admin/stats` → `unused_pairs ≥ 500`
2. Run `export_dataset.py` → `training_data.jsonl`
3. Fix Sprint 2 issues di training scripts
4. Trigger RunPod SimPO ($5.50 budget)
5. Monitor training (A100/H100, QLoRA 4-bit, ~2-4 jam)
6. Convert → Q4_K_M GGUF
7. Run identity eval (cosine ≥0.85)
8. Hot-swap via Ollama API

### Day 50–56 — Beta Onboarding (5 users)
1. Sprint 3 QA fixes (JWT cookie, default creds, RLS api_keys)
2. BFG Repo Cleaner: hapus VPS IP + password dari git history
3. Two-question onboarding UI (live di chat.html)
4. Dynamic starter cards via Gemini Flash
5. Invite 5 beta users

### Day 57–65 — Open Source Prep
1. README + LICENSE polish
2. Docs cleanup untuk public consumption
3. GitHub repo public
4. 10 beta users target

---

## INFRASTRUKTUR

### VPS Layout
```
/opt/ado/          → MiganCore (docker-compose, semua containers)
/opt/sidix/        → SIDIX lab (ONAMIX MCP server di .../tools/)
/opt/sidix/tools/hyperx-browser/   → ONAMIX/HYPERX MCP server
/www/wwwroot/migancore.com/        → Landing page static
/www/wwwroot/app.migancore.com/    → Chat frontend static
/www/server/panel/vhost/nginx/     → nginx vhosts aaPanel
```

### Docker Services
| Service | Port | Status |
|---------|------|--------|
| PostgreSQL 16 + pgvector | 5432 | ✅ running |
| Redis | 6379 | ✅ running |
| Qdrant v1.12.0 | 6333 | ✅ running |
| Ollama | 11434 | ✅ running (Qwen2.5-7B Q4_K_M + 0.5B) |
| API (FastAPI) | 18000 | ✅ running |
| Letta 0.6.0 | 8283 | ✅ running (passive storage only) |
| Celery | — | DISABLED (intentional) |
| Langfuse | — | DISABLED (intentional) |

### RAM Budget (32GB VPS)
- Ollama 7B: ~6GB
- Postgres: ~500MB
- Qdrant: ~200MB
- Redis: ~100MB
- API: ~200MB
- Letta: ~500MB
- **Total ADO: ~7.5GB** dari 32GB ✅

### Domains
| Domain | Target | SSL |
|--------|--------|-----|
| `migancore.com` | `/www/wwwroot/migancore.com/` | ✅ Let's Encrypt |
| `api.migancore.com` | → port 18000 | ✅ Let's Encrypt |
| `app.migancore.com` | `/www/wwwroot/app.migancore.com/` | ✅ Let's Encrypt |

---

## VISION & IDENTITY

### ADO — 5 Level Evolution
| Level | Nama | Status |
|-------|------|--------|
| L1 | Seed — basic chat + memory | ✅ LIVE |
| L2 | Learner — CAI + synthetic training data | ✅ LIVE (flywheel running) |
| L3 | Adaptor — multimodal + 23 tools | ✅ LIVE |
| L4 | Self-Improver — SimPO self-training cycles | 🟡 READY, waiting 500+ pairs |
| L5 | Director — spawn children agents | ✅ LIVE (UI + genealogy) |

### Northstar Vision
> "Setiap manusia yang punya visi berhak punya organisme digital yang tumbuh bersamanya."

### Quarterly Targets (dari Kickoff Doc)
- Q2 2026: seed alive + 5 beta users ← **SEKARANG INI**
- Q3 2026: mighan.com beta + 50 clones
- Q4 2026: marketplace + 200 agents
- Q1 2027: 1000 agents + open source

### SOUL.md (Identity Core)
- File: `Master doc/01_SOUL.md`
- Diinjeksi sebagai system prompt setiap chat
- 7 Core Values · 4 Agentic Operating Principles · 12 Constitutional Guardrails
- Identity Eval: 20 fingerprint prompts, cosine sim ≥0.85 required untuk promote model baru

---

## BUDGET TRACKING (BULAN 2)

| Kategori | Cap | Spent | Sisa |
|----------|-----|-------|------|
| API keys (Anthropic+Kimi+OpenAI+Gemini) | $23 | ~$1.44 | ~$21.56 |
| RunPod (Cycle 1 training) | $7 | $0 | $7 |
| Total Bulan 2 | $30 | **$1.44** | **$28.56** |

---

## 50 LESSONS KUMULATIF (SELECTED KEY LESSONS)

1. Default nginx config hostile ke SSE — setiap server butuh SSE-specific location block
2. Retry > Regenerate — user intent tidak berubah
3. `asyncio.CancelledError` propagates through httpx context managers naturally
4. `num_ctx` WAJIB explicit — Ollama default 2048 = silent truncation
5. Qdrant hybrid: BM42 query WAJIB pakai `query_embed()`, BUKAN `embed()`
6. `fastembed_cache` named volume = instant reload, JANGAN dihapus
7. Hybrid BM42+dense+RRF butuh Qdrant ≥v1.10.0
8. SimPO > DPO untuk dataset kecil/noisy (arxiv 2405.14734)
9. CAI sample 50% — critique + revise = 2 sequential 7B calls, CPU bottleneck
10. Distillation pipeline = wired tapi 0 pairs — Ollama CPU student step bottleneck
11. Multi-template picker = deprecated Q1 2026 — jangan build yang sudah di-kill industri
12. Kimi+Gemini quorum judge > single Ollama self-judge (30% less bias)
13. Tool registration sync antara skills.json + agents.json WAJIB dijaga (Lesson #48)
14. Tool description referencing unavailable tool = brain emits NOTHING (Lesson #50)
15. `async with OllamaClient()` WAJIB di streaming path (httpx leak prevention)
16. JWT silent refresh lock = prevents rotation race condition
17. tool_cache Redis TTL = 1400x speedup empirical (337ms → 0ms warm)
18. ONAMIX MCP stdio singleton (subprocess → mcp.ClientSession, 8x speedup)
19. conv_summarizer di sleep-time, bukan mid-stream
20. API key di URL = bocor ke logs — selalu gunakan header
21. `secrets.compare_digest()` WAJIB untuk timing-sensitive auth check
22. `eval()`/`exec()` WAJIB raise, bukan `pass`
23. BFG Repo Cleaner sebelum repo public (VPS IP + password di git history)
24. Stale Redis "running" status WAJIB auto-corrected saat process restart
25. Container deploy `--build` mandatory — cache miss = stale image

---

## NEXT TASKS (PRIORITIZED)

### Immediate (Day 47)
```bash
# 1. Cek DPO pool current count
curl -H "X-Admin-Key: $ADMIN_KEY" https://api.migancore.com/v1/admin/stats | jq '.training_readiness'

# 2. Cek synthetic generator status
curl -H "X-Admin-Key: $ADMIN_KEY" https://api.migancore.com/v1/admin/synthetic/status

# 3. Jika pool belum 500, pastikan synthetic running
# Jika status=idle: curl -X POST ... /v1/admin/synthetic/start -d '{"target_pairs":1000}'
```

### Setelah DPO ≥ 500 (Cycle 1 trigger)
1. Fix Sprint 2 issues (H15, H16, H17 — ~3 jam) SEBELUM training
2. `python training/export_dataset.py` → verify JSONL valid
3. Buat RunPod pod (RTX A100 atau H100)
4. Upload JSONL + jalankan `train_simpo.py`
5. Monitor training loss + eval cosine
6. Convert ke GGUF: `python training/convert_gguf.py`
7. Hot-swap: `ollama create migancore-v0.1 -f Modelfile`
8. Verify identity eval ≥ 0.85

### Day 50+ (Beta)
1. Sprint 3 QA fixes (C1, C2, H3, H7, H13)
2. BFG Repo Cleaner (SEBELUM invite beta users)
3. Two-question onboarding UI
4. Invite 5 beta users

---

*Dokumen ini dibuat 2026-05-05 (Day 47 start) oleh Claude Sonnet 4.6.*
*Update berikutnya: setelah Cycle 1 training selesai, atau setelah sprint major berikutnya.*
*Untuk detail per-day: lihat `memory/day*_progress.md` dan `docs/logs/daily/`.*
