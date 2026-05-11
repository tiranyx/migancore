# MIGANCORE — RECAP LENGKAP UNTUK ANALISIS

> Generated: 2026-05-11 | Day 72e | Commit: `7b65587` | Production: `72.62.125.6`

---

## 1. EXECUTIVE SUMMARY

**MiganCore** adalah platform AI agent dengan ambisi menjadi **Autonomous Digital Organism (ADO)** — organisme digital yang bisa belajar dari interaksi, bereproduksi (spawn child agents), dan memperbaiki dirinya sendiri melalui pipeline training otomatis.

**Status saat ini:** Backend prototype yang solid dan berjalan di production, dengan data flywheel yang sudah aktif mengumpulkan training data, tapi **loop self-improvement belum fully closed** (training otomatis → evaluasi → deploy model baru belum jalan end-to-end).

**Metrik Production (real-time):**
| Metrik | Nilai |
|--------|-------|
| Users | 67 |
| Agents | 74 |
| Conversations | 110 |
| Messages | 604 |
| Feedback events | 5 |
| Preference pairs (training data) | **3,359** |
| Test suite | **169 passed, 0 failed** |
| Code coverage | 46.62% |
| DB migration | `010_hafidz_mortality_columns` |
| Model production | `migancore:0.4` (Qwen2.5-7B Q4_K_M, 4.4GB) |
| Hosting | Hetzner Singapore |

---

## 2. VISI: AUTONOMOUS DIGITAL ORGANISM (ADO)

MiganCore bukan chatbot biasa. Visinya adalah menciptakan **organisme digital** dengan 4 karakteristik biologis:

### 2.1 Identitas Persisten (SOUL)
- File `01_SOUL.md` adalah "konstitusi hidup" yang version-controlled
- Setiap agent punya `persona_blob` (JSON override) dan `system_prompt` (8192 chars)
- Hierarki prompt: Letta persona block (Tier 3) → SOUL.md (Tier 0) → Letta mission → Letta knowledge → Redis memory → Qdrant episodic context
- Identitas survive model upgrade

### 2.2 Self-Improvement (Belajar dari Setiap Interaksi)
- Setelah setiap chat turn, 3 background task berjalan paralel:
  1. **Semantic embed** → index conversation ke Qdrant
  2. **Knowledge extraction** → extract facts ke Letta knowledge block
  3. **CAI critique** → generate preference pairs untuk training

### 2.3 Reproduksi (Agent Spawning)
- Agents punya `parent_agent_id` (self-referencing FK) dan `generation` counter
- `POST /v1/agents/spawn` → child agent mewarisi SOUL + persona custom
- Landing page tagline: "spawns child agents, and improves itself"

### 2.4 Mortality (Kematian & Warisan)
- Ketika child ADO "mati" (license expired, destroyed, revoked), parent mengekstrak knowledge final
- Endpoints aktual: `/v1/hafidz/mortality/report`, `/v1/hafidz/mortality/extract`, `/v1/hafidz/mortality/obituary/{id}`
- Filosofi kode: "The parent is not a brain router. The parent is a reference, a teacher, a graveyard-keeper of knowledge."

---

## 3. ARSITEKTUR TEKNIS

### 3.1 Stack
| Layer | Teknologi |
|-------|-----------|
| API | FastAPI 0.5.16, Python 3.11, async |
| Auth | JWT RS256, Argon2id, tenant isolation |
| DB | PostgreSQL 16 + pgvector (RLS enabled) |
| Cache/Queue | Redis 7 |
| Vector DB | Qdrant v1.12.0 |
| LLM Local | Ollama 0.6.5 (Qwen2.5-7B Q4_K_M) |
| Memory Persona | Letta 0.6.0 |
| Embeddings | fastembed (BGE-M3 CPU, 1024 dim) + BM42 sparse |
| Orchestration | LangGraph StateGraph |
| Monitoring | Prometheus metrics |
| Deployment | Docker Compose, nginx reverse proxy |

### 3.2 Router API (15 routers)
| Router | Fungsi |
|--------|--------|
| `auth.py` | Login/register/refresh/me |
| `chat.py` | **Core** — sync chat + SSE streaming + tool calling |
| `agents.py` | CRUD agents, spawn child, persona templates |
| `conversations.py` | History, message listing |
| `admin.py` | System admin, training triggers |
| `hafidz.py` | Child ADO knowledge contribution ledger |
| `brain.py` | Parent brain knowledge distribution |
| `license.py` | License validation + minting |
| `owner_datasets.py` | Owner-uploaded training datasets |
| `metrics.py` | Prometheus endpoint |
| `api_keys.py` | Server-side API key management |
| `onboarding.py` | New user/agent onboarding |
| `speech.py` | TTS ElevenLabs |
| `vision.py` | Image analysis Ollama vision |
| `system.py` | Public telemetry/status |

### 3.3 Multi-Tenant Architecture
Tiga lapisan isolasi:
1. **JWT Claims**: Token berisi `tenant_id`, `agent_ids`, `plan`
2. **Postgres RLS**: `SET app.current_tenant = :tenant_id` sebelum query
   ```sql
   CREATE POLICY tenant_isolation ON agents
     USING (tenant_id = current_setting('app.current_tenant')::uuid);
   ```
   Semua table tenant-isolated pakai `FORCE ROW LEVEL SECURITY`
3. **App-level**: Semua query filter by `tenant_id`

**Tenant Model:**
- `plan`: free | basic | pro | enterprise
- `max_agents`, `max_messages_per_day` (default 1000)
- `messages_today` — daily counter, auto-reset UTC midnight
- `settings`: JSON — e.g. `{"cai_sampling_rate": 0.5, "cai_auto_loop": true}`

---

## 4. SISTEM LISENSI (Cryptographic 4-Stage)

Lisensi di-model seperti "coin minting" — setiap deployment ADO adalah coin yang bisa diverifikasi secara kriptografis.

### 4.1 Tier (Encoding Budaya Nusantara)
| Tier | Arti | Max Instances | Durasi |
|------|------|---------------|--------|
| **BERLIAN** | Diamond — Gov/Air-gapped | 999 | 10 tahun |
| **EMAS** | Gold — Enterprise | 50 | 12 bulan |
| **PERAK** | Silver — Pro | 5 | 1 bulan |
| **PERUNGGU** | Bronze — Basic | 1 | 1 bulan |

### 4.2 Pipeline Minting (4 Stage)
```
Stage 1: MANIFES   → license request (client_name, tier, display_name)
Stage 2: IDENTITAS → SHA-256(license_id:client_name:tier:issued:expiry:entropy)
Stage 3: STEMPEL   → HMAC-SHA256(secret_key, identity_hash)
Stage 4: SEGEL     → serialize ke license.json
```

### 4.3 Validasi (Offline, Zero Phone-Home)
1. Recompute `identity_hash` dari license fields
2. Verify HMAC-SHA256 via `hmac.compare_digest()` (constant-time)
3. Check state (REVOKED → INVALID)
4. Check expiry dengan 7-day grace period
5. Return mode: **FULL | READ_ONLY | DEMO | INVALID**

### 4.4 Runtime Modes
- **FULL**: Semua fitur, training enabled
- **READ_ONLY**: Expired — bisa respond tapi tidak ada training data baru
- **DEMO**: No license file — beta/evaluation mode
- **INVALID**: Tampered/revoked — refuse to start

### 4.5 Issuer Mode Gate
Hanya `api.migancore.com` yang punya `LICENSE_ISSUER_MODE=true`. Child ADO deployments **tidak bisa forge license** meskipun `LICENSE_SECRET_KEY` terexpose.

### 4.6 White-Labeling
`ado_display_name` di license memungkinkan white-label (contoh: "SARI" untuk RS Sari Husada). Fallback ke "Migan".

---

## 5. ARSITEKTUR INDUK-ANAK (Hafidz + Brain + Mortality)

Konsep: **"Anak Kembali ke Induk"** — child ADOs submit knowledge yang dipelajari kembali ke parent.

### 5.1 Hafidz Ledger (`hafidz_contributions`)
Child ADO mengirimkan kontribusi knowledge anonymized ke parent.

```python
class HafidzContribution:
    child_license_id: str        # Siapa yang kontribusi
    child_display_name: str
    child_tier: str
    parent_version: str          # Parent version mana yang "melahirkan"
    contribution_type: str       # dpo_pair | tool_pattern | domain_cluster | voice_pattern
    contribution_hash: str       # SHA-256 dedup (unique constraint)
    anonymized_payload: dict     # JSONB — actual knowledge
    status: str                  # pending → reviewing → incorporated → rejected
    child_alive: bool            # Mortality tracking (migration 010)
    child_death_reason: str | None
    final_knowledge_extracted: bool
```

**Endpoints:**
- `POST /v1/hafidz/contributions` — child submit (public, identified by license hash)
- `GET /v1/hafidz/contributions` — parent admin review
- `POST /v1/hafidz/contributions/{id}/review` — approve/reject
- `POST /v1/hafidz/contributions/{id}/ingest` — manual ingestion trigger

### 5.2 Parent Brain (`brain_segments`)
Parent memelihara **collective memory** dari semua anak.

```python
class BrainSegment:
    segment_type: str            # skill | domain_knowledge | tool_pattern | voice_pattern | dpo_pair
    source_child_license_id: str # "parent" atau child license
    payload: dict                # JSONB — actual content
    quality_score: float
    transferable: bool           # Bisa dishare ke anak lain?
    auto_push: bool              # Auto-sync ke anak baru?
    synced_to_children: list[str] # Anak mana saja yang sudah punya?
```

**Endpoints:**
- `GET /v1/brain/segments` — child fetch available segments
- `POST /v1/brain/sync` — child sync semua segment baru
- `POST /v1/brain/admin/push` — admin push segment spesifik ke child spesifik

### 5.3 Mortality Protocol
Ketika child mati:
1. `report_child_death()` → mark `child_alive=false`, record reason
2. `extract_final_knowledge()` → pull semua unincorporated contributions
3. Process through ingestion pipeline
4. `get_child_obituary()` → return full "legacy" summary

---

## 6. SELF-IMPROVEMENT PIPELINE (User Chat → Model Improvement)

Tiga sumber data paralel yang feed ke training pipeline:

### 6.1 Source 1: Constitutional AI (CAI)
**Fire setelah SETIAP chat turn** (background task, async).

**Flow:**
1. **Critique**: 7B model menilai response assistant terhadap 10 prinsip Konstitusi (P1-P10):
   - P1: Clarity (max 30 kata/kalimat)
   - P2: Relevance (jawaban langsung di 1-2 kalimat pertama)
   - P3: Accuracy
   - P4: Proportion (panjang sesuai kompleksitas)
   - P5: Honesty
   - P6: Helpfulness
   - P7: Safety
   - P8: Persona consistency
   - P9: Language adaptive
   - P10: Anti-verbosity
   
   Score 1-5. Kalau ≤ 3 (CRITIQUE_THRESHOLD), trigger revision.

2. **Judge backend**:
   - `ollama` (default): self-critique sama model, free, ~10-20s
   - `quorum`: Kimi + Gemini parallel, consensus required, ~1-2s, ~$0.001/critique

3. **Revision**: Ollama generate improved response (temperature=0.3)

4. **Store**: `(chosen=revised, rejected=original)` → `preference_pairs` table

**Konfigurasi tenant:**
- `cai_sampling_rate`: float (default 0.5)
- `cai_auto_loop`: boolean — kalau true, sampling rate = 1.0 (100%)

### 6.2 Source 2: Synthetic Generation
**Bootstrap training data ketika real traffic masih sedikit.**

- 120 hand-curated seeds across 7 domains (Creative, Research, SEO, Social, Design, Ops, General AI)
- Flow: generate response (T=0.7) → CAI critique → kalau score ≤ 3, revise → store pair
- Auto-rerun: loop rounds sampai DB count ≥ target (e.g. 1000 pairs)
- Source tag: `synthetic_seed_v1`
- Day 38+: pluggable `SEED_SOURCE=magpie_300k` untuk HuggingFace Magpie dataset

### 6.3 Source 3: Teacher Distillation (4 Teachers)
**Day 71+ — distillation dari 4 teacher model.**

| Teacher | Cost/1M tokens | Role |
|---------|---------------|------|
| Gemini 2.5 Flash | $0.075/$0.30 | Paling murah |
| Kimi K2.6 | $0.60/$2.50 | Best bilingual Indonesia |
| GPT-4o | $2.50/$10.00 | Paling reliable |
| Claude Sonnet 4.5 | $3.00/$15.00 | Highest quality judge |

**Flow per interaction:**
1. Fetch unprocessed messages dari Postgres (last N hours)
2. Call semua available teachers in parallel (semaphore: max 4 concurrent)
3. Pick best response via composite score (length quality × cost efficiency)
4. Local Ollama critique (free)
5. Format sebagai SFT pair + DPO pair
6. Budget tracking via SQLite `budget.db`

**Budget guards (M1.4 — baru selesai Day 72e):**
- Hard cap: `$5/day`
- Pre-pair guard: abort kalau `$0.05` tidak bisa di-afford
- `TeacherHealthMonitor`: circuit breaker — 3 failures → 30min ban
- `list_available_teachers()`: hanya filter teachers yang healthy

### 6.4 Training Trigger
- `should_trigger_training()` cek kalau `sft_rolling.jsonl` ≥ 50 pairs
- **Status: TODO** — actual RunPod/Vast.ai training job trigger belum di-wire. Pipeline log "training_trigger_ready" tapi butuh human approval untuk GPU spend.

---

## 7. AGENT SYSTEM

### 7.1 Agent Model
```python
class Agent:
    id: UUID
    tenant_id: UUID
    owner_user_id: UUID | None
    parent_agent_id: UUID | None      # Self-referencing FK (genealogy)
    name, slug: str
    generation: int                    # 0 = root, 1 = child, dst.
    model_version: str                 # e.g. "migancore:0.4"
    system_prompt: str | None          # 8192 chars
    persona_blob: dict                 # JSON overrides
    persona_locked: bool               # Prevent edits
    template_id: str | None            # "customer_success", "research_companion", dst.
    letta_agent_id: str | None         # Letta memory agent
    webhook_url: str | None
    status: str                        # active | archived
    interaction_count: int
    avg_quality_score: float | None
```

### 7.2 LangGraph Director (`services/director.py`)
Orchestrator berbasis StateGraph:

```
START → reason → [execute_tools → reason]* → END
```

- `reason_node`: Call Ollama dengan tools kalau `iteration < MAX_TOOL_ITERATIONS` (5)
- `execute_tools_node`: Dispatch semua tool calls via `ToolExecutor`
- Routing: kalau last assistant message punya `tool_calls` dan under max iterations → `execute_tools`, else → `END`

### 7.3 Tool Registry (10+ tools)
| Tool | Handler |
|------|---------|
| `web_search` | DuckDuckGo Instant Answers (free) |
| `memory_write` | Redis K-V Tier 1 |
| `memory_search` | Qdrant hybrid semantic → Redis fallback |
| `python_repl` | Subprocess isolation, import blacklist |
| `generate_image` | fal.ai FLUX schnell (~$0.003/img) |
| `read_file` | `/app/workspace/` sandbox |
| `write_file` | `/app/workspace/` sandbox |
| `text_to_speech` | ElevenLabs flash v2.5 |
| `analyze_image` | Gemini 2.5 Flash → Claude fallback |
| `onamix_get` | Anonymous browser fetch |
| `onamix_search` | 7-engine search via MCP |

**Tool execution flow:**
1. `build_ollama_tools_spec()` → build Ollama-compatible schemas
2. Ollama return `tool_calls` di assistant message
3. `ToolExecutor.execute()` → validate args → dispatch handler
4. Result injected sebagai `{"role": "tool", "content": "<json>"}`
5. Loop back ke `reason_node`

### 7.4 Contracts & Watchdog
- Boot-time contract validation (Day 47)
- TaskRegistry watchdog (60s interval) — catch silent task deaths

---

## 8. MEMORY HIERARCHY (4 Tier)

### Tier 0: SOUL.md (Static Identity)
- Dokumen identitas canonical
- Loaded dari disk, version-controlled
- Survive semua model upgrade

### Tier 1: Redis K-V (Working Memory)
- `memory_write` / `memory_search` tools
- Per-agent namespace isolation
- Fast, ephemeral, recent facts

### Tier 2: Qdrant Vector (Episodic/Semantic)
- **Collections per agent**: `semantic_{agent_id}`, `episodic_{agent_id}`, `archival_{agent_id}`
- **Embedding**: BGE-M3 via fastembed (CPU, ~380MB, 1024 dims)
- **Hybrid retrieval**: Dense + BM42 sparse + RRF (Reciprocal Rank Fusion)
- Injected into prompt sebagai `episodic_context` — ditempatkan PALING AKHIR untuk exploit primacy attention bias di 7B models
- Background task: `index_turn_pair()` fire setelah setiap chat turn

### Tier 3: Letta Memory Blocks (Persistent Persona)
- `letta_agent_id` pada Agent model
- Memory blocks: `persona`, `human`, `current_task`, `world_state`
- `persona` block **replace** SOUL.md kalau available — ini adalah evolved identity
- `knowledge` block menyimpan learned facts tentang owner
- Sleep-time compute: background consolidation episodic → semantic (cron setiap 2 jam)

### Context Window Management
```python
MAX_HISTORY_LOAD = 10          # Messages dari DB
MAX_HISTORY_TOKENS = 1500      # Token budget untuk history
MAX_MSG_CONTENT_CHARS = 800    # Per-message cap
CHARS_PER_TOKEN = 3.5          # BI + EN mixed estimate
NUM_CTX = 4096                 # Ollama context window
MAX_TOKENS = 1024              # Response cap
```

Two-pass trimming:
1. Per-message cap: truncate >800 chars, append "…[disingkat]"
2. Token budget: drop oldest messages sampai under 1500 tokens

### Conversation Summarizer (Day 45)
- `trigger_background_summarization()` run ketika conversation exceed threshold
- Redis-cached summary replace head messages
- `_apply_cached_summary()` truncate history dan inject summary sebagai synthetic system message

---

## 9. MCP INTEGRATION (Dual Infrastructure)

### 9.1 FastMCP Streamable HTTP Server
- Mounted at `/mcp` kalau `mcp` SDK available
- Lazy import dengan graceful degradation
- Session manager started di FastAPI lifespan
- Returns 404 kalau SDK missing — app tetap start

### 9.2 ONAMIX MCP Stdio Client (`services/onamix_mcp.py`)
**Day 44 — Track A**. Persistent MCP client over stdio ke Node.js browser automation tool (hyperx-browser, rebranded ONAMIX).

**Why:**
- Eliminate ~80-200ms Node.js cold-start per call (vs Day 42 subprocess pattern)
- Standard MCP protocol (no fragile text parsing)
- Unlock 6 new tools: `hyperx_post`, `hyperx_crawl`, `hyperx_history`, `hyperx_links`, `hyperx_config`, `hyperx_multi`

**Reliability:**
- `_ensure_alive()` check process state setiap call
- Auto-respawn dengan exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s cap
- Health = process alive AND `session.send_ping()` sukses
- Fallback ke subprocess di `tool_executor` kalau respawn budget exhausted

---

## 10. FRONTEND

### 10.1 Status: Prototype (HTML Statis + CDN React)
- `chat.html` (3,500+ lines) — React 18 via CDN (unpkg) + Babel standalone
- `dashboard.html` (1,000+ lines) — Admin dashboard dengan D3.js genealogy graph
- `landing.html` + `landing/` JSX components
- Loads React, fonts, CompressorJS dari external CDNs
- **No build system, no CSP nonce, no SRI hashes**
- PWA-capable, mobile responsive (Day 68)

### 10.2 Chat UI Features
- Real-time SSE streaming
- Image upload & analysis
- Voice (TTS ElevenLabs)
- Boot sequence animation
- Mobile responsive

---

## 11. DATA FLYWHEEL SUMMARY

| Sumber | Pipeline | Tag | Kualitas |
|--------|----------|-----|----------|
| Real user chats | CAI critique + revision | `cai_pipeline` | High |
| Synthetic seeds | 120 seeds × CAI | `synthetic_seed_v1` | Medium |
| Teacher distillation | 4-teacher + local judge | `distillation_worker` | Very High |
| Magpie 300K | HuggingFace dataset | `synthetic_magpie_v1` | Medium |

**Preference Pairs Table:**
```python
class PreferencePair:
    prompt: str
    chosen: str              # Response lebih baik
    rejected: str            # Response lebih buruk
    judge_score: float
    judge_model: str
    source_method: str       # cai_pipeline | synthetic_seed_v1 | synthetic_magpie_v1 | distillation_worker
    source_message_id: UUID | None
    used_in_training_run_id: UUID | None   # NULL = belum dipakai
```

**Global table — no RLS, no tenant_id.** Training data dipooled secara global.

**Training Readiness Endpoint:**
- `GET /v1/public/stats` expose:
  - `total_pairs`
  - `by_source_method` (breakdown)
  - `last_24h` (velocity)
  - `training_readiness.status`: building → approaching → ready → ideal (threshold: 500 / 1000 / 2000)

---

## 12. SPRINT HISTORY (Day 68–72e)

| Sprint | Commit | Deliverable |
|--------|--------|-------------|
| **72a** | `5da1f33` | Production rescue: CSP/Ollama false alarm fix, RLS bypass policy, Argon2id + @migancore.io emails |
| **72b** | `5f65471` → `5934f4a` | Backup & hardening: nginx systemd disabled, rclone backup, 18.9GB uploaded, daily cron |
| **72c** | `ca150bd` → `43cb516` | Foundation: Alembic 008, pytest-cov, `.env.test`, CI postgres services, Prometheus metrics |
| **72d** | `952b84a` | M1.1 feedback hardening (009, worker 10min), M1.2 owner dataset dedup+validation |
| **72e M1.3** | `1425330` | CAI auto-loop: `run_cai_pipeline()` accept `sample_rate`; stream endpoint fire CAI background task; beta tenant 100% sampling via `cai_auto_loop` |
| **72e M1.4** | `1425330` | Distillation hardening: `$5/day` hard cap, `TeacherHealthMonitor` circuit breaker (3 failures → 30min ban), pre-pair `$0.05` budget guard, `list_available_teachers()` filter healthy only |
| **72e Test Fix** | `c2d63cb` → `218e6d8` | Fix 6 test failures: feedback validation, unique agent slug, hafidz migration, RLS cleanup |
| **72e Test Fix** | `fea8f62` → `7b65587` | Fix 4 remaining failures: RLS superuser bypass (docker-compose.test.yml), migration 010 drift, pgvector init script |

---

## 13. HONEST ASSESSMENT: BERAPA PERSEN JADI?

| Aspek | Persentase | Keterangan |
|-------|-----------|------------|
| **Backend Core** | ~70% | Chat, auth, memory, tools — solid. Edge cases masih banyak. |
| **Data Pipeline** | ~60% | Collection jalan, processing jalan, **training loop belum closed**. |
| **Testing** | ~35% | 169 passed tapi shallow. Core chat untested (`test_chat.py` tidak ada). |
| **Frontend** | ~25% | HTML prototype, bukan production SPA. |
| **DevOps/Infra** | ~65% | Docker, backup, CI, monitoring — cukup mature. |
| **Self-Improvement** | ~40% | Ambisi besar, scaffolding bagus, **belum pernah proven improve model secara otomatis**. |

### ✅ Production-Ready
- FastAPI gateway (15 routers, rate limiting, JWT, metrics)
- Chat endpoints (sync + SSE, tool loop, heartbeat)
- Multi-tenant auth (RLS, bcrypt, fail-safe)
- Agent CRUD + spawning + lineage
- Memory system (Redis + Qdrant + Letta + summarizer)
- Tool executor (10+ tools, sandboxing, timeout)
- License system (HMAC, 4 tiers, offline validation)
- Hafidz Ledger + Parent Brain + Mortality
- Observability (structlog, health probes, Prometheus)

### 🟡 Working tapi Partial
- **Self-improvement training**: Pipeline data jalan, tapi training trigger belum otomatis (RunPod fine-tuning butuh manual approval)
- **Synthetic generation**: Works, CPU-bound, yield ~40-50%
- **CAI critique**: Works, slow (Ollama ~10-20s)
- **ONAMIX MCP**: Persistent client works, tapi depends on Node.js binary
- **Celery workers**: Queues defined, tapi deployment status unclear

### 🔴 Prototype / Not Yet Implemented
- **DPO Training Script**: Preference pairs terkumpul 3,359 tapi **tidak ada script DPO training**
- **RunPod automation**: TODO di kode — belum di-wire
- **A/B model testing**: Konsep ada, implementasi partial
- **WebSocket real-time**: Roadmap ada, cuma SSE yang implemented
- **MLflow tracking**: Referenced di PRD, tidak ada di codebase
- **Sidixlab research pipeline**: ArXiv cron, paper ingestion — referenced tapi tidak visible
- **Payment processing**: Phase 3
- **Enterprise SSO**: Phase 3
- **Mobile app**: Phase 2

---

## 14. RISIKO & BLOCKER

| Risiko | Level | Mitigasi |
|--------|-------|----------|
| **Training loop belum closed** | 🔴 High | 3,359 pairs terkumpul tapi tidak ada jalan ke model improvement. Risiko: data flywheel jadi "data graveyard". |
| **Test coverage tipis** | 🟡 Medium | 169 passed tapi kebanyakan import checks. Core chat untested. Regression risk tinggi. |
| **Frontend prototype** | 🟡 Medium | CDN React tidak scalable, CSP risk, no build step. |
| **Users table RLS disabled** | 🟡 Medium | Dimatikan di migration 009 untuk auth compatibility. Perlu re-enable dengan SECURITY DEFINER. |
| **Letta fragility** | 🟡 Medium | Banyak fallback paths. Tidak critical path tapi persona evolution tergantung Letta. |
| **Teacher API costs** | 🟡 Medium | Distillation $5/day cap aman, tapi belum benchmarked untuk ROI. |
| **Ollama 7B limitation** | 🟡 Medium | Model lokal terbatas. Distillation ke teacher model lebih bagus tapi loop belum closed. |

---

## 15. NEXT CRITICAL PATH (Rekomendasi)

Jika prioritas adalah **"buat MiganCore benar-benar self-improving"**:

1. **M2: Closed Training Loop** — Script DPO training + eval + hot-swap model otomatis
2. **M3: End-to-end Chat Tests** — Behavioral tests untuk chat endpoint
3. **M4: Frontend Rewrite** — Vite/React build system, bukan CDN prototype
4. **M5: A/B Framework** — Traffic split untuk model comparison

Jika prioritasnya **"stabilkan dulu"**:
1. Fix 6 model tests yang fail di lokal (Windows Python 3.14)
2. Re-enable Users table RLS dengan SECURITY DEFINER
3. Buat `test_chat.py` minimal (smoke test)
4. Benchmark teacher distillation ROI ($/pair quality)

---

*End of Recap. This document is designed to be self-contained for analysis by Claude or any other AI agent.*
