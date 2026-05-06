# PRODUCT BRIEF ALIGNMENT — MiganCore
**Tanggal:** 2026-05-07 | **Dibuat oleh:** Claude Code | **Versi API:** v0.5.18
**Sumber Brief:** `MIGANCORE-PROJECT-BRIEF.md` (Fahmi Ghani × Claude, Mei 2026)

> **DOKUMEN INI WAJIB DIBACA SEBELUM KERJA.** Ini adalah mapping antara **visi founder** (brief) dan **realita yang sudah dibangun** (Day 1–60). Agent apapun yang masuk ke proyek ini harus mulai dari sini.
>
> Aturan: JANGAN PIVOT dari brief. Kalau ada konflik dokumen lama vs brief → **brief menang**.

---

## 1. RINGKASAN BRIEF (VISI FOUNDER)

### Apa itu MiganCore?
Platform untuk membangun, mendistribusikan, dan men-deploy **ADO (Autonomous Digital Organism)** — unit AI yang berfungsi sebagai **otak + syaraf + jiwa** dari organisasi digital.

ADO = 3 lapisan:
| Layer | Nama | Fungsi |
|-------|------|--------|
| Otak | Cognitive Core | Reasoning, analisis, sintesis, self-learning loop |
| Syaraf | Integration Layer | MCP tools, API, workflow, memory pipeline |
| Jiwa | Identity Layer | Persona, value alignment, tujuan organisasi |

### Satu Kalimat Positioning
**"Satu-satunya AI organisme yang bisa di-clone per organisasi, di-retrain dengan data internal, dan di-self-host sepenuhnya — tanpa data bocor ke mana pun."**

### 9 Prinsip Non-Negotiable dari Brief
| # | Prinsip | Status |
|---|---------|--------|
| P1 | **Zero Data Leak** — tidak ada telemetry, tidak ada cloud sync | ✅ BUILT (self-hosted, no external data call) |
| P2 | **Self-Hosted di Infrastruktur Client** — deploy di VPS client | ✅ ARCHITECTURE OK — docker template needed |
| P3 | **Modular Clone** — setiap ADO instance independen | ⚠️ NOT YET — single instance only |
| P4 | **Retrain by Owner** — pemilik bisa melatih ulang modelnya | ✅ PROVEN — 3 training cycles complete |
| P5 | **Base Skills Pre-loaded** — setiap ADO baru sudah bisa langsung | ✅ BUILT — 23 tools, MCP, memory, tools ready |
| P6 | **White-label Naming** — client bebas menamakan ADO mereka | ⚠️ NOT YET — nama hardcoded "Migan" |
| P7 | **Licensed — Migancore × Tiranyx** — setiap instance berlisensi | ❌ NOT BUILT — license system belum ada |
| P8 | **Anti Vendor Lock-in** — core engine open, migratable | ✅ BUILT — Ollama + GGUF = open format |
| P9 | **Trilingual by Design** — ID (primary), EN (secondary), ZH (tertiary) | ⚠️ PARTIAL — ID ✅, EN partial, ZH ❌ |

---

## 2. STATE AKTUAL — DAY 60 (APA YANG SUDAH ADA)

### Platform Infrastructure ✅
```
Production URL     : app.migancore.com (Chat UI)
API                : api.migancore.com (FastAPI)
Admin Dashboard    : app.migancore.com/admin
MCP Server         : api.migancore.com/mcp/ (Streamable HTTP, JWT auth)
Smithery           : smithery.ai/server/fahmiwol/migancore (public)
VPS                : 72.62.125.6 (32GB RAM, aaPanel, Docker stack)
Containers         : api, ollama, postgres, qdrant, redis, letta (6 up)
```

### ADO Brain ✅
```
Production Model   : migancore:0.3 (Qwen2.5-7B + GGUF LoRA)
HuggingFace        : Tiranyx/migancore-7b-soul-v0.3
Identity Score     : 0.953 (threshold 0.80 ✅)
Voice Score        : 0.817 (↑ dari 0.715)
Weighted Avg       : 0.9082 (threshold 0.80 ✅)
Training Cycles    : 3 completed (Cycle 1-3 ORPO)
Training Pairs     : 685 identity-anchored pairs
Training Cost      : ~$0.16/cycle (proven efficient)
```

### 3 Lapisan ADO yang Sudah Dibangun
```
JIWA (Identity Layer)     : ✅ Persona "Migan", identity score 0.953, value alignment
SYARAF (Integration)      : ✅ 23 tools, MCP server live, episodic+semantic memory
OTAK (Cognitive Core)     : ✅ Qwen2.5-7B brain, ReAct loop, self-learning ORPO loop
```

### Tools Aktif (23 Tools)
- **ONAMIX** (8): get, search, scrape, post, crawl, history, links, multi
- **Media**: generate_image (fal.ai), analyze_image (Gemini Vision), text_to_speech, speech_to_text
- **Files**: read_file, write_file, export_pdf (WeasyPrint), export_slides (Marp PPTX)
- **Web**: web_read (Jina), web_search
- **Code**: execute_code (sandboxed)
- **Memory**: knowledge retrieval, episodic recall

### Memory Architecture ✅
- **Semantic**: Qdrant v1.12.0 (hybrid BM42 + dense 768-dim, RRF fusion)
- **Episodic**: PostgreSQL 16 + pgvector (per-conversation context)
- **Cache**: Redis (JWT, tool cache 1400x speedup, rate limiting)
- **Blocks**: Letta 0.6.0 (persona/mission/knowledge blocks — passive storage)

---

## 3. ALIGNMENT MATRIX — BRIEF vs REALITA

### Section 7: Architecture (Brief)
| Komponen Brief | Status | Catatan |
|---------------|--------|---------|
| ADO Builder (web UI konfigurasi persona, domain, tools) | ❌ NOT BUILT | Phase 3 brief |
| Base Model Layer (pretrained LLM, swappable) | ✅ BUILT | Ollama + GGUF hot-swap proven |
| Clone & Deploy (Docker per org, self-hosted client) | ⚠️ PARTIAL | Docker ada, clone mechanism belum |
| Training Interface (upload data → fine-tune/RAG) | ⚠️ PARTIAL | Pipeline ada, UI belum client-facing |
| MCP Integration (connect ke tools, sistem, database) | ✅ BUILT | 23 tools + MCP server public |
| Privacy Vault (encrypted, zero external call) | ✅ ARCHITECTURE | Implementasi enkripsi at rest belum explicit |

### Section 7.2: Tech Stack (Brief)
| Brief Spec | Aktual | Gap |
|-----------|--------|-----|
| Base LLM: **Qwen3-8B** (self-hosted, trilingual) | Qwen2.5-7B | Upgrade path planned (Cycle 5+) |
| RAG/Memory: ChromaDB atau Qdrant (local) | **Qdrant** ✅ | Exact match |
| API Layer: **FastAPI (Python)** | **FastAPI** ✅ | Exact match |
| Frontend: **Next.js 14 + TypeScript** | HTML/CSS/JS (chat.html) | Phase 3 — beta UI cukup untuk sekarang |
| Deployment: **Docker + Coolify / aaPanel** | Docker + **aaPanel** ✅ | Coolify untuk per-client deploy (Phase 2) |
| MCP: Custom MCP server (Node.js atau Python) | **Python** ✅ | Exact match |
| Database: **PostgreSQL + SQLite** | **PostgreSQL** ✅ | SQLite belum (per-instance butuh ini) |
| Auth: **NextAuth v5 / JWT** | **JWT** ✅ | Partial match |
| i18n: **next-intl (ID/EN/ZH)** | Tidak ada i18n system | Phase 3 — saat build Next.js |

### Section 8: Build Roadmap (Brief) — Kita Ada di Mana?
```
Phase 1 — Foundation (Sprint 1–4):          ✅ COMPLETE (Day 1–30)
  ✅ ADO base config schema
  ✅ Basic MCP integration layer
  ✅ Memory pipeline (episodic + semantic, Qdrant)
  ⚠️ Trilingual base prompt: ID ✅ EN partial ❌ ZH
  ❌ License file schema + HMAC-SHA256 validator

Phase 2 — Clone, Identity & Training (Sprint 5–8):  ⚠️ IN PROGRESS (Day 31–90)
  ❌ Clone mechanism: base ADO → org-specific instance
  ❌ White-label identity layer
  ❌ "Powered by Migancore × Tiranyx" admin panel text
  ⚠️ Privacy Vault: architecture OK, encryption at rest pending
  ⚠️ Business data training: pipeline exists, client-facing UI belum
  ❌ License enforcement system
  ❌ Language preference config per instance

Phase 3 — Migancore.com Platform (Sprint 9–14):     ❌ NOT STARTED
  ❌ Web UI untuk ADO Builder
  ❌ Deploy wizard
  ❌ Dashboard monitoring
  ❌ Billing system (Rupiah + USD + CNY)
  ❌ Trilingual UI (next-intl)

Phase 4 — Go-to-Market (Sprint 15+):                ⚠️ PARTIAL
  ⚠️ Landing page migancore.com (ada tapi bukan trilingual)
  ❌ Reseller portal
  ❌ Documentation trilingual
  ⚠️ First 7 paying clients (beta soft-launched Day 51, 0 paid yet)
```

---

## 4. KEPUTUSAN STRATEGIS — LOCK (JANGAN PIVOT)

### K01: Qwen2.5-7B tetap sampai Cycle 5+ (TIDAK upgrade sekarang)
**Reasoning:**
- 685 identity-anchored training pairs sudah di-optimize untuk Qwen2.5-7B tokenizer
- 3 cycles ORPO proven: identity 0.953, weighted 0.9082
- Qwen3-8B memerlukan baseline ulang dari nol (identity eval akan reset)
- Brief menyebut Qwen3-8B karena native trilingual — itu kebutuhan ZH market
- ZH market = Phase 3/4, bukan sekarang
- **Action:** Research Qwen3-8B upgrade path di Cycle 5 (Day 90+), bukan sebelumnya
- Semua training pairs (685) format-compatible → bisa dipakai lagi di Qwen3-8B

### K02: Frontend HTML/CSS/JS tetap untuk beta (Next.js 14 = Phase 3)
**Reasoning:**
- app.migancore.com live, beta users sudah ada
- Next.js 14 rebuild = besar, disruptif, tidak menambah value untuk beta
- Brief sendiri menempatkan Next.js di Phase 3 (Platform Builder)
- **Action:** Build Next.js hanya ketika membangun ADO Builder (Phase 3)

### K03: aaPanel tetap untuk VPS migancore.com (Coolify = client deploy template)
**Reasoning:**
- aaPanel sudah running stabil dengan semua containers
- Coolify yang dimaksud brief = untuk **template deploy di VPS client**
- **Action:** Buat Docker Compose template (Coolify-compatible) di Phase 2 untuk per-client deployment

### K04: Self-learning loop = CORE DIFFERENTIATOR (Jangan stop)
**Reasoning:**
- Brief: "Retrain by Owner" = prinsip P4
- Kita sudah PROVE ini 3x dengan biaya efektif ($0.09-0.16/cycle)
- Ini adalah unfair advantage nyata vs semua kompetitor
- **Action:** Teruskan Cycle 4, 5, dst. Ini bukan "nice to have" — ini adalah DNA ADO

### K05: Teacher APIs (Kimi/Claude/GPT/Gemini) = MENTOR, bukan brain
**Reasoning:**
- VISION LOCKED (Day 52): Teacher API = OFFLINE synthetic data generation
- ADO respond dengan own brain (migancore:0.x), TIDAK live-forward ke teacher
- **Action:** Jangan pernah propose "hybrid brain" atau "live teacher routing"

---

## 5. GAP ANALYSIS — PRIORITAS UNTUK PHASE 2

### CRITICAL (Revenue-blocking)

**GAP-01: Clone Mechanism**
- Brief: "setiap ADO adalah instance independen, beda nama, beda persona, beda knowledge"
- Aktual: Single ADO instance bernama Migan, tidak ada clone system
- Implikasi: Tidak bisa onboard client pertama sampai ini ada
- Effort: Medium (1–2 sprint)
- Priority: **P0 — Phase 2 blocker**

**GAP-02: Per-Org Docker Compose Template**
- Brief: "ADO di-deploy di VPS milik client atau on-premise client"
- Aktual: Docker ada tapi tidak ada template untuk client deploy sendiri
- Effort: Low (1 sprint) — sebagian besar tinggal extract + parameterize
- Priority: **P0 — Phase 2 blocker**

**GAP-03: License System (HMAC-SHA256)**
- Brief: License file per instance, startup validator, expired → read-only
- Aktual: Tidak ada license system
- Effort: Medium (1-2 sprint) — kriptografi + enforcement logic
- Priority: **P1 — needed before first paying client**

### HIGH (Quality/Market)

**GAP-04: White-label Identity Layer**
- Brief: Client bisa menamakan ADO mereka (SARI, LEX, NOVA, dll)
- Aktual: Nama "Migan" hardcoded di config dan training data
- Effort: Low-Medium — `display_name` config + system prompt injection
- Priority: **P1 — needed untuk client onboarding**

**GAP-05: Mandarin (ZH) Language Support**
- Brief: Trilingual ID/EN/ZH by design
- Aktual: ID first, EN partial, ZH tidak ada
- Note: Qwen2.5-7B punya ZH capability native, hanya perlu training pairs ZH
- Priority: **P2 — Phase 3 target (ZH market = later)**

**GAP-06: Business Data Upload UI (Client-facing)**
- Brief: "Upload data → Chunking & indexing → Vector embedding → RAG pipeline"
- Aktual: Pipeline ada (Qdrant + knowledge ingestion), tapi UI untuk client belum
- Effort: Medium — API endpoint sudah ada, perlu UI
- Priority: **P2 — needed untuk client training service**

### MEDIUM (Platform)

**GAP-07: AES-256 Encryption at Rest**
- Brief: Privacy Vault — "semua data encrypted at rest"
- Aktual: Data tidak diencrypt at rest (Qdrant, PostgreSQL, Redis plain)
- Priority: **P2 — untuk enterprise/government segment**

**GAP-08: SQLite per Instance**
- Brief: "PostgreSQL + SQLite (per instance)"
- Aktual: PostgreSQL only (shared, multi-tenant RLS)
- Note: Per-instance SQLite = isolated storage per client ADO
- Priority: **P3 — arsitektur platform Phase 3**

---

## 6. NEXT STEPS — DAY 61-90 (ALIGNED WITH BRIEF)

### Sprint A — Day 61-66: Cycle 4 (Training Excellence)
*Aligns: Brief P4 "Retrain by Owner", K04 Core Differentiator*
- [ ] Expand seeds: 150+ per kategori (dari avg 10)
- [ ] Fix evolution-aware regression (0.568 → target 0.85)
- [ ] Add creative category (20-30 pairs)
- [ ] Cycle 4 training: 950+ pairs, target weighted ≥ 0.92
- Budget: ~$0.10-0.12 Vast.ai

### Sprint B — Day 67-70: Agentic Task Layer
*Aligns: Brief "ADO punya ReAct loop, self-learning, synthesis" + Brief Section 7.1*
- [ ] Task decomposition module: multi-step request → sub-tasks
- [ ] Plan → Execute → Verify pattern
- [ ] Demo: "Buatkan laporan kompetitor AI Indonesia" → search → analyze → PDF
- [ ] 10 manual eval prompts

### Sprint C — Day 71-75: Clone & White-label Foundation (GAP-01, GAP-04)
*Aligns: Brief P3 "Modular Clone", P6 "White-label Naming", Phase 2 Roadmap*
- [ ] `ado_config.json` schema: persona, display_name, tools, model, language
- [ ] Config-driven identity injection ke system prompt
- [ ] Docker Compose template untuk per-client deployment (parameterized)
- [ ] "Powered by Migancore × Tiranyx" di admin config (non-removable)

### Sprint D — Day 76-80: License System (GAP-03)
*Aligns: Brief P7 "Licensed", Section 2A White-label & License*
- [ ] License schema (UUID, client_name, display_name, tier, expiry, signature)
- [ ] HMAC-SHA256 generator + validator (offline-capable)
- [ ] Startup enforcement: valid → run, expired → read-only
- [ ] License file embed ke Docker config

### Sprint E — Day 81-90: MCP Orchestration + Business Data UI (GAP-06)
*Aligns: Brief MCP Integration, Training Interface*
- [ ] Migan sebagai MCP orchestrator (bukan hanya server)
- [ ] Connect ke Brave Search MCP, GitHub MCP
- [ ] Simple business data upload endpoint + RAG indexing
- [ ] Test: client upload SOP PDF → ADO "mengerti" dokumen tersebut

---

## 7. CATATAN UNTUK AGENT LAIN

### Quick Orientation (baca 3 menit, paham full project)
1. **Brief = North Star.** Jangan pivot dari 9 prinsip non-negotiable.
2. **Kita di Phase 2** dari 4-phase roadmap. Foundation sudah selesai.
3. **ADO = 3 lapisan** yang sudah dibangun: Jiwa (identity 0.953) + Syaraf (23 tools) + Otak (Qwen2.5-7B, migancore:0.3)
4. **Training loop proven.** Cycle 3 = $0.16, 8 menit, weighted 0.9082. Jangan hentikan.
5. **Gap terbesar = Clone + License.** Tanpa ini, tidak bisa onboard client pertama.

### File Wajib Baca (urutan prioritas)
```
1. docs/PRODUCT_BRIEF_ALIGNMENT.md        ← dokumen ini (baca dulu)
2. docs/DAY60_MANDATORY_PROTOCOL.md       ← state Day 60, findings, lessons
3. docs/ENVIRONMENT_MAP.md                ← VPS topology, jangan salah container
4. docs/AGENT_ONBOARDING.md               ← anti-recurrence protocol
5. docs/VISION_PRINCIPLES_LOCKED.md      ← 5 prinsip visi, 5-check sanity test
6. docs/LESSONS_LEARNED.md                ← 118 lessons kumulatif
```

### Trigger Phrases Owner (Fahmi Ghani)
- `gas` / `lanjut` = execute sekarang, jangan tanya lagi
- `ngaco` / `kurang` = arah salah, stop dan recalibrate
- `catat` = dokumentasikan ke ARCHITECTURE.md atau LIVING_LOG
- `betul` / `match` = aligned, lanjut
- `loh` = owner butuh klarifikasi

### Architecture Layers (sesuai brief)
```
Layer 4 [PROPAGATION]  — clone per org, genealogy tree (IN PROGRESS)
Layer 3 [ORCHESTRATION]— MCP gateway, multi-agent routing  (✅ BUILT)
Layer 2 [COGNITION]    — migancore:0.3 brain, self-improvement loop (✅ BUILT)
Layer 1 [FOUNDATION]   — Qwen2.5-7B base, GGUF LoRA adapter (✅ BUILT)
Layer 0 [PLATFORM]     — VPS, Docker, PostgreSQL, Qdrant, Redis, Ollama (✅ BUILT)
```

### Yang TIDAK Boleh Dilakukan
- ❌ Jangan propose "forward live query ke Claude/GPT/Kimi sebagai brain"
- ❌ Jangan upgrade Qwen3-8B sebelum Cycle 5 selesai
- ❌ Jangan rebuild frontend ke Next.js sebelum Phase 3
- ❌ Jangan beli VPS baru tanpa persetujuan Fahmi
- ❌ Jangan push biaya training >$0.20/cycle tanpa approval
- ❌ Jangan add tools baru sebelum evaluasi dampak (Lesson #57)
- ❌ Jangan hardcode credentials di kode

### Infrastructure Map (singkat)
```
VPS /opt/ado/          = MiganCore stack (JANGAN sentuh /opt/sidix/)
Container Ollama       = docker exec ado-ollama-1 (BUKAN curl localhost:11434)
Training GPU           = Vast.ai (fahmiwol@gmail.com, A40 46GB, cap $0.65/hr)
Git remote             = github.com:tiranyx/migancore
Deploy                 = docker cp config.py → container → restart api (no rebuild)
```

---

## 8. BUSINESS MODEL TRACKING

### Brief Target vs Aktual
| Stream | Brief Target | Aktual |
|--------|-------------|--------|
| ADO License Fee | Rp 3-5 jt/bln (Basic) | Belum ada paying client |
| Setup & Deploy Fee | Rp 5-25 jt (one-time) | Belum |
| Training Service | Rp 2-8 jt/sesi | Belum |
| White-label Reseller | 30-40% revenue share | Belum (program belum ada) |
| Marketplace Tools | 20% komisi | Phase 4+ |

### Break-even Target
```
7 klien × Rp 5 jt = Rp 35 jt/bln → BREAK EVEN
20 klien aktif    = Rp 100-150 jt/bln (MRR Year 1)
```

### Blockers to First Paid Client
1. **Clone mechanism** (GAP-01) — client perlu instance sendiri
2. **License system** (GAP-03) — legal enforcement
3. **Per-org Docker template** (GAP-02) — client bisa deploy sendiri
4. **White-label** (GAP-04) — client mau namakan AI mereka sendiri

*Catatan: Beta soft-launched Day 51. Platform sudah bisa dipakai. Tapi onboarding paying client butuh items di atas.*

---

## 9. RESEARCH FINDINGS 2026 (RELEVAN UNTUK ROADMAP)

*(Dari research session Day 60 — cross-referenced dengan brief)*

| Finding | Relevansi ke Brief |
|---------|-------------------|
| **AIOS "kernel + SDK"** = paradigma AI OS sedang mainstream | Validates ADO architecture — Layer 0-4 persis ini |
| **MCP + A2A** = two-layer protocol standard 2026 | MCP sudah built ✅, A2A (agent-to-agent) = roadmap |
| **RLVR** (Reinforcement Learning with Verifiable Rewards) | Next evolution dari ORPO — tool-call success sebagai reward signal |
| **Graph memory** > vector untuk multi-session coherence | Qdrant bagus untuk single-session, graph layer needed untuk long-term |
| **Indonesia** = 3M AI talent shortage, no native Bahasa AI brain | Validates target market dan differentiation |
| **QeRL** = 40-50% cost reduction vs standard LoRA | Bisa diaplikasikan Cycle 5+ |

---

*Dokumen ini dibuat Day 61 (2026-05-07) berdasarkan MIGANCORE-PROJECT-BRIEF.md + DAY60_MANDATORY_PROTOCOL.md.*
*Update dokumen ini setiap ada direction change disetujui owner, atau setiap phase transition.*
*Next checkpoint: Day 61 Cycle 4 dataset design.*
