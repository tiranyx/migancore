# MIGANCORE — ARSITEKTUR REMAP v2026.05
**Dokumen Wajib | Jangan Eksekusi Tanpa Baca Ini**
**Versi:** 1.0 | **Tanggal:** 2026-05-08 | **Executor:** Kimi Code CLI
**Status:** FOUNDATION LOCK — Semua keputusan di sini adalah keputusan arsitektural final.
> 📋 **EVALUASI STRATEGIS TERBARU:** `docs/EVALUATION_20260509_0800_WIB.md` — 9 Mei 2026, 08:00 WIB. Audit komprehensif 10 poin oleh Chief Engineer. WAJIB baca bersama dokumen ini untuk konteks execution.

---

## DAFTAR ISI
1. [Executive Summary](#1-executive-summary)
2. [Visi & Alignment](#2-visi--alignment)
3. [State of the Union (Jujur)](#3-state-of-the-union-jujur)
4. [Arsitektur Baru: 4-Pilar](#4-arsitektur-baru-4-pilar)
5. [4 Jalur Pertumbuhan Brain](#5-4-jalur-pertumbuhan-brain)
6. [Multi-Loss Training Engine](#6-multi-loss-training-engine)
7. [Memory & Identity System](#7-memory--identity-system)
8. [Infrastructure Hardening](#8-infrastructure-hardening)
9. [Tren 2026-2027 & Integrasi](#9-tren-2026-2027--integrasi)
10. [Implementation Phases](#10-implementation-phases)
11. [Decision Registry](#11-decision-registry)
12. [Risk & Mitigation](#12-risk--mitigation)

---

## 1. EXECUTIVE SUMMARY

**Migancore adalah Cognitive Kernel-as-a-Service** — bukan chatbot, bukan wrapper API. Ini adalah otak AI yang bisa di-clone, di-train ulang, dan di-self-host oleh setiap organisasi.

**Masalah fundamental hari ini:** Brain stuck di Day 60. 5 cycle training gagal berturut-turut. Identitas fragile. Data nyata hanya 1%. Dokumentasi 150+ file tapi test cuma 1 file.

**Solusi:** Stop brain training sementara. Bangun **infrastruktur data dan arsitektur training yang solid**. Baru setelah fondasi kokoh, brain bisa tumbuh dengan berbagai cara tanpa circular loop.

**Prinsip arsitektur baru:**
- **Data first, model second.** Brain butuh makanan berkualitas, bukan synthetic junk food.
- **Multi-loss arsenal.** Beda masalah = beda tool. ORPO-only adalah hammer yang melihat semua sebagai paku.
- **Identity baked into weights.** Bukan scaffolding prompt. White-label tidak bisa jalan kalau identitas masih gantung di SOUL.md.
- **4 pathways must flow.** Self, Owner, User, Teacher — semua harus punya pipeline sendiri yang reliable.
- **Observability by design.** Tiap komponen harus bisa di-trace, di-audit, di-rollback.

---

## 2. VISI & ALIGNMENT

### Northstar (Tidak Berubah)
> "Setiap manusia yang punya visi berhak punya organisme digital yang tumbuh bersamanya."

### Definisi Migancore (Tidak Berubah)
- ADO = Autonomous Digital Organism (Otak + Syaraf + Jiwa)
- Dibangun oleh PT Tiranyx Digitalis Nusantara
- Self-hosted, zero data leak, white-label, trilingual (ID/EN/ZH)
- License: Migancore × Tiranyx (tidak bisa dihapus)

### Strategic Pillars 2026-2027

| Pillar | Fungsi | Status 2026 Q2 | Target 2027 Q1 |
|---|---|---|---|
| **Brain** (migancore.com/lab) | Riset, training, model versioning | Cycle 3 stuck | Self-improving weekly |
| **Platform** (migancore.com/app) | Clone, deploy, manage ADO | Empty repo | 50 org instances |
| **Ecosystem** (migancore.com) | Governance, marketplace, community | Docs only | 1000 active agents |

### Cognitive Trend Integration (2026-2027)
Berdasarkan riset mendalam (referensi: `migancore new riset.md`), tren yang akan dominan dan harus diintegrasikan:

1. **Reasoning Models sebagai Society of Thought** — DeepSeek R1-0528, o3, Gemini 2.5 Pro secara internal sudah melakukan multi-perspective dialogue. Implikasi: single reasoning model bisa menggantikan 3-5 specialist agent untuk task kompleks.
2. **Agentic Commerce (x402 + ERC-8004)** — Agent bisa saling bayar untuk inference. 69K active agents, 165M transaksi, $50M volume (April 2026). Migancore bisa monetisasi per-inference call.
3. **Self-Evolving Skill RAG** — Frontier 2026-2027. Setiap task berhasil disimpan sebagai reusable skill module. Meta Hyperagents, SWE-RL, HKUDS OpenSpace.
4. **Multi-tier Memory sebagai LLM OS** — Letta (ex-MemGPT) dengan core/recall/archival memory. 93.4% accuracy DMR vs 35.3% baseline.
5. **Causal AI + Active Inference** — Moat arsitektural 5+ tahun. Agent yang minimize free energy + bisa jawab counterfactual. VERSES Genius: 140× faster, 5,260× cheaper than o1-preview di Mastermind.
6. **MCP 78% enterprise adoption** — De facto standard. 9,400+ public servers. Migancore HARUS expose sebagai MCP server + A2A peer.

---

## 3. STATE OF THE UNION (JUJUR)

### ✅ Yang Beneran Jalan (Verified)

| Layer | Komponen | Evidence | Quality |
|---|---|---|---|
| API | FastAPI v0.5.16 | 12 routers, JWT RS256, RLS | ⭐⭐⭐⭐⭐ |
| Chat | SSE streaming, tool loop | chat.html 3,543 lines | ⭐⭐⭐⭐ |
| Memory | Redis + Qdrant + Postgres | Hybrid BM42, 1400x speedup | ⭐⭐⭐⭐ |
| Training | 30+ scripts | SimPO/ORPO/SFT, VastAI/RunPod | ⭐⭐⭐⭐ |
| License | HMAC-SHA256 validator | Day 61, clone deployment | ⭐⭐⭐⭐ |
| Frontend | React CDN chat + landing | PWA, SW, voice, image | ⭐⭐⭐ |
| MCP | Streamable HTTP server | smithery.ai registered | ⭐⭐⭐ |

### ⚠️ Yang Rusak / Fragile

| Layer | Masalah | Dampak | Root Cause |
|---|---|---|---|
| **Brain Quality** | Stuck di Cycle 3 (Day 60) | Zero progress 11 hari | ORPO wrong tool, 99% synthetic data |
| **Identity** | Tanpa SOUL prompt = "Qwen" | White-label tidak bisa | LoRA tidak cukup kuat override base |
| **Data Pipeline** | 1% real data, 99% synthetic | Training circular | User feedback broken, owner path missing |
| **Migrations** | Manual SQL only | Schema drift risk | Alembic imported tapi tidak dipakai |
| **Testing** | 1 file test_rls.py | Regressions tidak ketauan | Fokus docs > tests |
| **Platform Repo** | Empty directories | Investor/contributor misleading | Belum dibangun |
| **CI/CD** | Tidak ada | Deploy manual, error-prone | Belum diprioritaskan |

### ❌ Yang Belum Dibangun (Brief Phase 2 GAPs)

| GAP | Brief Section | Blocker untuk |
|---|---|---|
| Clone Mechanism E2E | P3 | Revenue — client pertama |
| Per-Org Docker Template | P3 | Deployment client |
| License Enforcement | P7 | Revenue gate |
| White-Label Identity Layer | P6 | White-label promise |
| Trilingual EN/ZH | P9 | Market expansion |

---

## 4. ARSITEKTUR BARU: 4-PILAR

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MIGANCORE COGNITIVE KERNEL v2                     │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  PILLAR 1   │  │  PILLAR 2   │  │  PILLAR 3   │  │  PILLAR 4   │ │
│  │ DATA PLANE  │  │ TRAIN PLANE │  │  MEMORY OS  │  │  IDENTITY   │ │
│  │             │  │             │  │             │  │   VAULT     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                │                │        │
│         └────────────────┴────────────────┴────────────────┘        │
│                                   │                                  │
│                           ┌───────▼───────┐                         │
│                           │  COGNITIVE    │                         │
│                           │   CORE        │                         │
│                           │ (Qwen3-8B +   │                         │
│                           │  LoRA stack)  │                         │
│                           └───────┬───────┘                         │
│                                   │                                  │
│  ┌────────────────────────────────┼────────────────────────────────┐ │
│  │         ORCHESTRATION          │     (LangGraph + FastAPI)      │ │
│  └────────────────────────────────┴────────────────────────────────┘ │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  EXPOSED INTERFACES: MCP Server │ A2A Peer │ REST API │ WebSocket│
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Pilar 1: DATA PLANE — 4 Pathways Ingestion
**Fungsi:** Mengumpulkan data dari 4 sumber, membersihkan, menyimpan dengan reliable.

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  PATHWAY A  │  │  PATHWAY B  │  │  PATHWAY C  │  │  PATHWAY D  │
│   SELF      │  │   OWNER     │  │   USER      │  │  TEACHER    │
│  (CAI +     │  │ (Upload +   │  │ (Thumbs +   │  │ (Kimi/Claude│
│  Self-Play) │  │  Corrections│  │  Retry +    │  │ /GPT/Gemini)│
│             │  │  Annotations│  │  Edit)      │  │             │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │                │
       └────────────────┴────────────────┴────────────────┘
                          │
                    ┌─────▼─────┐
                    │  INGEST   │  ← Queue + validation + dedup
                    │  GATEWAY  │
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │  CURATOR  │  ← Quality filter, diversity scoring
                    │  ENGINE   │    MTLD metric, toxicity filter
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │  RAW DATA │  ← PostgreSQL (ACID, versioned)
                    │   LAKE    │
                    └───────────┘
```

**Spesifikasi Teknis:**
- **Ingest Gateway:** FastAPI endpoints + Redis Streams queue
- **Curator Engine:** Async Python worker, MTLD diversity scoring, duplicate detection via embedding cosine similarity > 0.95
- **Raw Data Lake:** PostgreSQL dengan JSONB untuk fleksibilitas schema
- **Retention:** 90 hari conversation logs, permanent untuk preference pairs yang lolos curator

### Pilar 2: TRAIN PLANE — Multi-Loss Arsenal
**Fungsi:** Training engine yang bisa memilih loss function sesuai masalah.

```
┌─────────────────────────────────────────────────────────────┐
│                    DATASET BUILDER                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  REPLAY     │  │  CURRICULUM │  │  ANCHOR SAMPLES     │  │
│  │  BUFFER     │  │  SORTER     │  │  (50 identity-fixed)│  │
│  │  30% old    │  │  easy→hard  │  │  Never change       │  │
│  │  70% new    │  │  per gate   │  │  Protect identity   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────┬───────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │  SFT    │          │  DPO    │          │  KTO    │
   │Pipeline │          │Pipeline │          │Pipeline │
   │         │          │         │          │         │
   │Identity │          │Prefer   │          │User     │
   │Anchor   │          │Pairs    │          │Thumbs   │
   │Voice    │          │Clean    │          │Direct   │
   └────┬────┘          └────┬────┘          └────┬────┘
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │  ORPO   │          │  SimPO  │          │  GRPO   │
   │Pipeline │          │Pipeline │          │(future) │
   │         │          │         │          │         │
   │Chat     │          │Chat     │          │Reasoning│
   │General  │          │General  │          │Chain    │
   └────┬────┘          └────┬────┘          └────┬────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │    EVAL GATE      │
                    │  ┌─────────────┐  │
                    │  │ Identity    │  │  ← 5 fingerprint prompts
                    │  │ Tool-Use    │  │  ← 20 tool prompts
                    │  │ Regression  │  │  ← 10 known-good scenarios
                    │  │ Quality     │  │  ← held-out eval set
                    │  └─────────────┘  │
                    │       PASS?       │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   DEPLOY PIPE     │
                    │  A/B 10% → 100%   │
                    │  Hot-swap Ollama  │
                    │  Rollback ready   │
                    └───────────────────┘
```

**Spesifikasi Teknis:**
- **Dataset Builder:** Python script, deterministic seed, versioned output
- **SFT Pipeline:** Unsloth QLoRA, rank 16, alpha 32, LR 2e-4, 3 epochs
- **DPO Pipeline:** TRL DPOTrainer, beta 0.1, reference model frozen
- **KTO Pipeline:** TRL KTOTrainer, no reference model needed, direct from user signals
- **ORPO/SimPO:** Existing scripts, tapi dibatasi untuk chat general only
- **GRPO:** Planned untuk reasoning tasks (Chain-of-Thought improvement)
- **Eval Gate:** Automated pytest suite, identity test dengan cosine similarity, tool-use accuracy > 80%

### Pilar 3: MEMORY OS — 4-Tier Architecture
**Fungsi:** Sistem memori yang terinspirasi Letta (LLM OS) tapi implementasi pragmatic.

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY HIERARCHY                         │
│                                                              │
│  TIER 1: WORKING MEMORY (GPU HBM / Context Window)          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SOUL.md (persona) + Current Task + Tool Context     │   │
│  │ 8192 tokens (expand to 32K setelah validation)      │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│  TIER 2: EPISODIC MEMORY (DRAM / SSD Log)                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ PostgreSQL: conversations, messages, tool_calls     │   │
│  │ Redis: recent N messages (TTL 24h hot cache)        │   │
│  │ Searchable: full-text + timestamp range             │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│  TIER 3: SEMANTIC MEMORY (Vector DB)                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Qdrant: facts, entities, relationships              │   │
│  │ Embedding: BGE-M3 (1024 dims)                       │   │
│  │ Collections: semantic_, episodic_, archival_, kb_   │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│  TIER 4: PROCEDURAL MEMORY (Model Weights / LoRA)           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ LoRA Adapters: skills, voice, identity, domain      │   │
│  │ Base Model: Qwen2.5-7B (soon Qwen3-8B)              │   │
│  │ Hot-swap: Ollama Modelfile                          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Spesifikasi Teknis:**
- **Sleep-Time Compute:** Background process (Celery beat) konsolidasi episodic → semantic ketika agent idle > 1 jam
- **Memory Injection:** LangGraph memory_reader node mengambil dari semua tier sebelum reasoning
- **Procedural Update:** Hanya melalui training pipeline yang lolos eval gate

### Pilar 4: IDENTITY VAULT — Cryptographic + Weights
**Fungsi:** Identitas yang tidak bisa hilang meski SOUL.md dimatikan.

```
┌─────────────────────────────────────────────────────────────┐
│                    IDENTITY LAYERS                          │
│                                                              │
│  LAYER 1: WEIGHT-LEVEL (Hard)                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SFT 200 identity pairs ke LoRA adapter              │   │
│  │ Target: Tanpa system prompt, model tetap bilang     │   │
│  │ "Saya adalah Mighan-Core, primordial intelligence"  │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│  LAYER 2: PROMPT-LEVEL (Soft)                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SOUL.md injected sebagai system prompt              │   │
│  │ Fallback jika Layer 1 belum cukup kuat              │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│  LAYER 3: CONFIG-LEVEL (White-Label)                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Per-instance: display_name, logo, persona custom    │   │
│  │ License file: HMAC-SHA256, immutable                │   │
│  │ "Powered by Migancore × Tiranyx" di admin panel     │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│  LAYER 4: RUNTIME-LEVEL (Verification)                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Identity fingerprint test: 5 prompts                │   │
│  │ Cosine similarity > 0.85 across versions            │   │
│  │ Auto-rollback jika < 0.85                           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 4 JALUR PERTUMBUHAN BRAIN

### Pathway A: Self-Growth (CAI + Self-Play)
**Status Sekarang:** 50% sample rate, idle, 18 pairs total
**Target:** 100% sample, continuous loop, 100+ pairs/minggu

**Pipeline:**
1. **Sample:** Setiap conversation yang selesai di-sample (100% rate)
2. **Critique:** Model sendiri (CAI) critique response-nya sendiri vs Constitution
3. **Revise:** Generate revised version yang lebih aligned
4. **Pair:** (original, revised) → preference pair jika revised lebih baik
5. **Judge:** LLM-as-Judge (local) verify pair quality > 0.7
6. **Store:** Masuk ke preference_pairs dengan source_method = 'constitutional_cai'

**Kode yang perlu dibuat:**
- `services/self_growth_pipeline.py` — orchestrator
- `workers/self_critique_worker.py` — Celery task, runs every 30 min
- `services/constitutional_checker.py` — check against 12 principles

### Pathway B: Owner-Input (Upload + Corrections)
**Status Sekarang:** NOT BUILT — tidak ada endpoint
**Target:** 5 endpoint + UI, owner bisa upload dataset kapan saja

**Pipeline:**
1. **Upload:** Owner upload file (JSONL, CSV, PDF, DOCX) atau paste text
2. **Parse:** Auto-detect format, extract Q&A pairs atau conversations
3. **Annotate:** Owner bisa koreksi/edit hasil parse
4. **Convert:** Jadi training-compatible format (SFT atau DPO)
5. **Queue:** Masuk ke dataset queue dengan priority HIGH
6. **Notify:** Owner dapat notifikasi ketika dataset siap dipakai training

**Endpoint yang perlu dibuat:**
- `POST /v1/admin/owner-dataset/upload` — multipart upload
- `GET /v1/admin/owner-dataset` — list owner datasets
- `POST /v1/admin/owner-dataset/{id}/annotate` — edit pairs
- `POST /v1/admin/owner-dataset/{id}/convert` → SFT/DPO/KTO
- `GET /v1/admin/owner-dataset/{id}/preview` — preview before training

### Pathway C: User-Input (Thumbs + Retry + Edit)
**Status Sekarang:** BROKEN — thumbs UI ada tapi tidak persist (1 thumb_up, 0 thumb_down di DB)
**Target:** Worker hourly + KTO loss function

**Root Cause:**
- Frontend kirim thumbs tapi endpoint tidak process ke preference_pairs
- PENDING completion worker MISSING
- Race condition di Day 69 sebagian fixed tapi backend worker tidak ada

**Fix:**
1. **Fix Endpoint:** `POST /v1/conversations/{id}/feedback` → langsung insert ke interactions_feedback
2. **Build Worker:** `workers/user_feedback_processor.py` — runs hourly via Celery beat
3. **KTO Pipeline:** User thumb_up → positive signal untuk KTO. Thumb_down → negative signal.
4. **Retry Tracking:** User retry = implicit rejection. Original vs retry = preference pair.
5. **Edit Tracking:** User edit response = explicit correction. Original vs edit = SFT pair.

**Kode yang perlu dibuat:**
- Fix `routers/conversations.py` — feedback endpoint
- `workers/user_feedback_processor.py` — hourly processing
- `services/kto_pair_builder.py` — build KTO-compatible dataset

### Pathway D: Teacher-API (Kimi/Claude/GPT/Gemini)
**Status Sekarang:** Manual, 10 pairs total
**Target:** Continuous 6h cycle, $5/day cap (~$150/bulan)

**Pipeline:**
1. **Sample:** Ambil 50 conversations terbaik dari minggu lalu (quality_score > 0.6)
2. **Distill:** Kirim ke teacher API (rotasi: Kimi → Claude → GPT → Gemini)
3. **Judge:** LLM-as-Judge bandingkan teacher output vs original
4. **Filter:** Hanya simpan jika teacher output score > original + 0.5
5. **Cost Cap:** $5/day max. Jika habis, pause sampai next day.
6. **Store:** Masuk ke preference_pairs dengan source_method = 'teacher_distillation'

**Kode yang perlu dibuat:**
- `services/teacher_rotator.py` — rotate APIs, track cost per teacher
- `workers/teacher_distill_worker.py` — Celery beat every 6h
- `services/cost_tracker.py` — real-time cost tracking, hard stop at $5/day

---

## 6. MULTI-LOSS TRAINING ENGINE

### Problem Analysis
Lesson #175: ORPO wrong tool untuk voice/length targets. Rewards/margins NEGATIVE di setiap cycle voice-targeted.
Lesson #174: Signal density <15% → regression di kategori lain.
Lesson #177: Baseline-gate coupling → false-fail.

### Solution: One Problem = One Tool

| Masalah | Loss Function | Kenapa | Pipeline |
|---|---|---|---|
| Identity fragile | **SFT** | Directly teach weights identity. No preference needed. | 200 pairs identity-only, 3 epochs |
| Voice/tone drift | **SFT** | Voice adalah pattern, bukan preference. | 200 pairs voice-only, 3 epochs |
| Tool-use accuracy | **SFT + DPO** | SFT untuk pattern, DPO untuk preferensi hasil. | 100 tool SFT + 200 tool DPO |
| User thumbs | **KTO** | KTO tidak butuh paired data. Direct signal. | All user feedback → KTO |
| General chat quality | **SimPO** | No reference model, efficient. | Top 500 pairs → SimPO |
| Complex reasoning | **GRPO** (future) | Group relative policy optimization untuk CoT. | Planned Q3 2026 |
| Catastrophic forgetting prevention | **Anchor Samples** | 50 fixed samples di setiap dataset. | Immutable, versioned |

### Training Discipline (NEW — Strict)
1. **ONE category per cycle.** Tidak boleh mix identity + voice + tool dalam satu cycle.
2. **Baseline decoupled from gate.** Baseline = model sebelumnya. Gate = threshold absolute.
3. **Minimum 100 real-data pairs per cycle.** Synthetic boleh supplement, tidak boleh dominan.
4. **Signal density ≥ 25% per category.** Kalau tidak cukup data, skip category itu.
5. **Identity test MANDATORY sebelum deploy.** Tanpa pengecualian.

---

## 7. MEMORY & IDENTITY SYSTEM

### Identity Fragility Fix (Lesson #170)
**Problem:** LoRA adapter (Cycle 3) tidak cukup kuat override base. Tanpa SOUL.md = "Qwen".
**Solution:** SFT Identity Anchor — 200 pairs pure identity training.

**Dataset Composition:**
- 50 pairs: "Siapa kamu?" → "Saya Mighan-Core..." (variasi pertanyaan)
- 50 pairs: Constitutional guardrails (tolak manipulasi, tolak agree-to-easier)
- 50 pairs: Tiranyx ecosystem knowledge (sidixlab, mighan.com, tiranyx.com)
- 50 pairs: Voice & tone examples (direct, no filler, structured)

**Training Spec:**
- Method: SFT (bukan ORPO/SimPO)
- Base: Qwen2.5-7B-Instruct
- LoRA: rank 32, alpha 64 (LEBIH BESAR dari biasanya untuk identity)
- LR: 1e-4 (lebih rendah, lebih hati-hati)
- Epochs: 5 (lebih banyak untuk memperkuat)
- Target: Tanpa system prompt, 5 fingerprint prompts → cosine sim > 0.85

### White-Label Architecture
Setiap ADO instance punya 3 layer identitas:
1. **Core Identity (immutable):** "Mighan-Core DNA" — baked di weights, tidak bisa dihapus
2. **Instance Persona (configurable):** display_name, tone, domain knowledge — via persona_blob JSONB
3. **Surface Branding (white-label):** Logo, warna, bahasa default — via config file

**License Enforcement:**
- License file: HMAC-SHA256 signed, offline-verifiable
- Startup: validator cek license, expired → read-only mode
- Clone: license baru di-generate per instance, tetap signed by Tiranyx
- Grace period: 7 hari jika license dicabut

---

## 8. INFRASTRUCTURE HARDENING

### 8.1 Database Migrations (Alembic)
**Status:** Alembic di requirements.txt tapi tidak dipakai. Manual SQL patches 004-025.
**Fix:**
1. Initialize Alembic: `alembic init alembic`
2. Convert init.sql ke Alembic revision baseline
3. Convert patches 004-025 ke migration files
4. Semua schema change ke depan HARUS via Alembic
5. CI/CD menjalankan `alembic upgrade head` sebelum deploy

### 8.2 Test Suite (pytest)
**Status:** 1 file (test_rls.py). Coverage < 5%.
**Target:**
- Unit tests untuk setiap service module
- Integration tests untuk API endpoints
- Regression tests untuk identity fingerprint
- Tool-use accuracy tests (20 prompts, > 80% pass)
- CI/CD menjalankan `pytest` sebelum merge

**Struktur tests/:**
```
tests/
├── unit/
│   ├── services/
│   ├── routers/
│   └── workers/
├── integration/
│   ├── test_auth_flow.py
│   ├── test_chat_flow.py
│   └── test_training_pipeline.py
├── regression/
│   ├── test_identity.py
│   ├── test_tool_use.py
│   └── test_memory.py
└── conftest.py
```

### 8.3 CI/CD Pipeline (GitHub Actions)
**Status:** Tidak ada.
**Target:**
```yaml
# .github/workflows/ci.yml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - checkout
      - setup Python 3.11
      - install deps
      - run: alembic upgrade head
      - run: pytest tests/ -v --cov=api --cov-report=xml
      - run: python scripts/identity_test.py --model migancore:0.3
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - SSH ke VPS
      - git pull
      - docker compose pull && docker compose up -d
      - health check
```

### 8.4 Observability
**Status:** Telemetry endpoint baru (Day 71d), tapi tidak ada alerting.
**Target:**
- Prometheus metrics endpoint `/metrics`
- Grafana dashboard (VPS resource, API latency, error rate)
- Alerting: RAM > 90%, API error rate > 5%, Ollama down > 2 min
- Log aggregation: structured JSON logs ke file, rotate harian

---

## 9. TREN 2026-2027 & INTEGRASI

### 9.1 Reasoning Models sebagai Society of Thought
**Tren:** DeepSeek R1-0528, o3, Gemini 2.5 Pro — reasoning models effectively emulate multi-agent dialogue internally.
**Integrasi Migancore:**
- Gunakan DeepSeek R1-0528 sebagai "Thinking Mode" untuk task kompleks
- Cost: 10-20× lebih murah dari o3 (strategic untuk Indonesia)
- Single reasoning model bisa ganti 3-5 specialist agents untuk task tertentu
- Sweet spot multi-agent: genuine tool/data partitioning atau parallel exploration

### 9.2 Self-Evolving Skill RAG
**Tren:** Frontier 2026-2027. Setiap task berhasil disimpan sebagai reusable skill module.
**Integrasi Migancore:**
- `Skill Library`: Python modules yang disimpan di PostgreSQL
- Setiap task completion → extract reusable pattern → store sebagai skill
- Skill versioning: v1, v2, dst. dengan parent-child relationship
- Skill execution: LangGraph node yang load skill dari library

### 9.3 Causal AI + Active Inference
**Tren:** Moat arsitektural 5+ tahun. Agent yang minimize free energy + bisa jawab counterfactual.
**Integrasi Migancore (Phase 2+):**
- **Causal Graph:** DoWhy + EconML untuk living causal graph
- **Counterfactual Query:** "What would happen if X?"
- **Active Inference:** pymdp (Python) untuk curiosity-driven exploration
- **Use case:** Decision-grade enterprise output (hukum, keuangan, manufaktur)

### 9.4 Agentic Commerce (x402 + ERC-8004)
**Tren:** 69K active agents, 165M transaksi, $50M volume (April 2026).
**Integrasi Migancore (Phase 3+):**
- Setup ERC-8004 identity untuk setiap ADO instance
- x402 wallet per instance untuk agent-to-agent payment
- Charge per inference: $0.005 (basic) → $0.05 (reasoning) → $0.50 (autonomous task)
- B2A2A play: agen lain bayar untuk menggunakan Migancore Cognitive Kernel

### 9.5 Multi-tier Memory sebagai LLM OS
**Tren:** Letta (ex-MemGPT) dengan core/recall/archival memory.
**Integrasi Migancore:**
- Tier 1: Context window (working)
- Tier 2: PostgreSQL + Redis (episodic)
- Tier 3: Qdrant (semantic)
- Tier 4: LoRA adapters (procedural)
- Sleep-time compute: konsolidasi otomatis Tier 2 → Tier 3

---

## 10. IMPLEMENTATION PHASES

### PHASE 0: Foundation Hardening (Minggu 1-2)
**Goal:** Infrastructure solid, context tidak hilang, testing ada.

| Task | ETA | Deliverable |
|---|---|---|
| Alembic migrations | 2 hari | `alembic/` dir, all patches converted |
| Test suite v1 | 3 hari | pytest suite, 50+ tests, CI pass |
| GitHub Actions CI/CD | 1 hari | `.github/workflows/ci.yml` |
| Context preservation system | 1 hari | Daily log protocol, agent handoff template |
| Observability (Prometheus + Grafana) | 2 hari | Metrics endpoint, dashboard, alerting |

**Success Criteria:**
- `pytest` pass 100% di local dan CI
- `alembic upgrade head` berjalan tanpa error
- Setiap commit ke main otomatis deploy ke staging

### PHASE 1: Data Pipeline Plumbing (Minggu 2-3)
**Goal:** 4 pathways semua jalan, data nyata mengalir.

| Task | ETA | Deliverable |
|---|---|---|
| Fix user feedback persistence | 1 hari | Endpoint + worker + KTO pipeline |
| Build owner data pathway | 2 hari | 5 endpoints + UI upload/annotate |
| Fix self-growth pipeline | 2 hari | CAI critique auto-loop, 100% sample |
| Fix teacher distillation | 2 hari | Continuous 6h cycle, $5/day cap |
| Data quality curator | 2 hari | MTLD scoring, dedup, diversity filter |

**Success Criteria:**
- User thumbs → preference_pairs dalam 1 jam
- Owner bisa upload dataset dan convert ke SFT/DPO
- Self-growth generate ≥ 20 pairs/hari
- Teacher distillation generate ≥ 50 pairs/hari, cost ≤ $5/hari
- Real-data ratio ≥ 20% (dari 1% sekarang)

### PHASE 2: Multi-Loss Training Engine (Minggu 3-4)
**Goal:** Training engine yang bisa pilih loss function sesuai masalah.

| Task | ETA | Deliverable |
|---|---|---|
| SFT pipeline | 2 hari | `train_sft.py`, identity + voice support |
| DPO pipeline | 1 hari | `train_dpo.py`, preference pairs clean |
| KTO pipeline | 1 hari | `train_kto.py`, user thumbs direct |
| SimPO/ORPO refactor | 1 hari | Batasi untuk chat general only |
| Dataset builder v2 | 2 hari | Replay buffer 30/70, curriculum sort, anchor samples |
| Eval gate automation | 2 hari | pytest suite untuk identity, tool-use, regression |

**Success Criteria:**
- Bisa jalankan SFT/DPO/KTO/SimPO dari satu command
- Eval gate automated, tidak perlu manual check
- Dataset builder deterministic (same seed = same output)

### PHASE 3: Identity Anchor SFT (Minggu 4)
**Goal:** Fix Lesson #170 — identity baked into weights.

| Task | ETA | Deliverable |
|---|---|---|
| Generate 200 identity pairs | 1 hari | `generate_identity_anchor.py` |
| SFT training (rank 32, 5 epochs) | 1 hari | RunPod/VastAI job |
| Eval tanpa SOUL prompt | 1 hari | 5 fingerprint prompts, cosine sim > 0.85 |
| Deploy ke production | 1 hari | Hot-swap Ollama, monitor 24h |

**Success Criteria:**
- Model tanpa system prompt jawab "Saya Mighan-Core"
- Cosine similarity > 0.85 untuk 5 fingerprint prompts
- Tool-use dan chat quality tidak regress

### PHASE 4: Beta Data Collection (Minggu 5-6)
**Goal:** Kumpulkan data nyata dari beta users.

| Task | ETA | Deliverable |
|---|---|---|
| Recruit 10 beta users | 3 hari | Onboarding flow, beta invite |
| Monitor 4 pathways | ongoing | Dashboard data flow real-time |
| Weekly data quality review | ongoing | Report real-data ratio, diversity |
| Cycle 8 training (mixed source) | 2 hari | Pertama kali training dengan >50% real data |

**Success Criteria:**
- Real-data ratio ≥ 50% setelah 2 minggu beta
- Brain quality improve dari Cycle 3 baseline
- User retention ≥ 70% (7 dari 10 users aktif setelah 2 minggu)

### PHASE 5: Clone & White-Label (Minggu 7-8)
**Goal:** Unblock revenue — client pertama bisa deploy.

| Task | ETA | Deliverable |
|---|---|---|
| Clone mechanism E2E | 3 hari | `POST /v1/admin/clone`, Docker template |
| Per-org Docker template | 2 hari | `docker/ado-instance/` production-ready |
| White-label identity layer | 2 hari | `display_name`, logo, persona config |
| License enforcement | 2 hari | Startup validator, expired → read-only |
| Trilingual base (EN/ZH) | 2 hari | Base prompts EN + ZH, language switcher |

**Success Criteria:**
- Bisa clone ADO untuk client baru dalam < 10 menit
- Client bisa ganti nama ADO jadi "SARI" atau "LEX"
- License enforcement aktif, tidak bisa di-circumvent
- ADO bisa respond dalam EN dan ZH (minimum basic)

### PHASE 6: Revenue Path (Minggu 9-12)
**Goal:** First paying client, billing, support.

| Task | ETA | Deliverable |
|---|---|---|
| Landing page migancore.com | 1 minggu | Trilingual, pricing, demo |
| First client onboarding | 2 minggu | Deploy, train, handoff |
| Billing integration | 1 minggu | Stripe/x402, invoice, tier management |
| Support system | 1 minggu | Ticket, knowledge base, SLA |

---

## 11. DECISION REGISTRY

Setiap keputusan arsitektural dicatat di sini. Tidak boleh ada keputusan yang tidak tercatat.

| ID | Tanggal | Keputusan | Alternatif | Alasan | Dampak |
|---|---|---|---|---|---|
| D-001 | 2026-05-08 | Stop brain training sementara, fokus infrastructure | Lanjutkan Cycle 7d | 5 cycles gagal, root cause data pipeline | Brain stuck 2-4 minggu lagi tapi fondasi kokoh |
| D-002 | 2026-05-08 | Multi-loss arsenal (SFT/DPO/KTO/SimPO) | ORPO-only | ORPO wrong tool untuk voice/identity (Lesson #175) | Lebih kompleks tapi lebih efektif per kategori |
| D-003 | 2026-05-08 | SFT identity anchor FIRST sebelum white-label | Fix white-label UI dulu | Identity fragile = blocker fundamental | White-label aman, client tidak bisa "matikan SOUL = jadi Qwen" |
| D-004 | 2026-05-08 | 30% old / 70% new replay buffer | 50/50 atau 10/90 | Balance stability vs learning | Cukup stabil tapi tetap adaptif |
| D-005 | 2026-05-08 | Teacher distillation $5/day cap | Unlimited atau $0 | Budget sustainable, data berkualitas | ~$150/bulan, ~$0.18/cycle |
| D-006 | 2026-05-08 | Qwen2.5-7B tetap base (bukan upgrade ke Qwen3-8B sekarang) | Upgrade ke Qwen3-8B | Qwen3-8B butuh 3-5 hari migration, risk brain reset | Upgrade di Phase 5 setelah identity solid |
| D-007 | 2026-05-08 | pgvector untuk bootstrap, Qdrant untuk scale | Qdrant-only atau pgvector-only | pgvector cukup sampai 50M vector, satu sistem lebih simpel | Bootstrap lebih mudah, scale tanpa migration berat |
| D-008 | 2026-05-08 | Celery + Redis untuk workers | RQ atau Dapr Agents | Celery sudah ada di stack, Dapr terlalu berat untuk solo | Minimal change, reliable |
| D-009 | 2026-05-08 | DeepSeek R1-0528 sebagai reasoning tier (future) | Claude Sonnet 4.6 | DeepSeek 10-20× cheaper, strategis untuk Indonesia | Cost efficient, trilingual native |
| D-010 | 2026-05-08 | Causal AI + Active Inference Phase 2+ (bukan sekarang) | Bangun sekarang | Solo founder bandwidth terbatas, foundation dulu | Window arbitrage 12-18 bulan masih terbuka |
| D-011 | 2026-05-08 | Clone model: Self-contained Docker per instance (amoeba), bukan SaaS multi-tenant | SaaS multi-tenant shared DB | Zero data leak, on-premise capable, inheritance model | Setiap client = stack penuh, resource lebih besar |
| D-012 | 2026-05-08 | License validation: Offline HMAC-SHA256 (no phone-home) | Online validation tiap startup | Air-gapped requirement (BERLIAN tier), client trust | Tidak bisa revoke remote; harus kirim file license baru |
| D-013 | 2026-05-08 | Knowledge return: Opt-in, default false | Default on / mandatory | Privacy first, compliance (RS, bank, gov), client trust | Data yang kembali lebih sedikit tapi higher quality |
| D-014 | 2026-05-08 | Data yang kembali: Pola yang dianonimkan, bukan raw data | Kirim percakapan verbatim / database snapshot | Zero PII leakage guarantee, client bisa audit | Lebih kompleks: perlu anonymization pipeline di anak |
| D-015 | 2026-05-08 | Generation depth: Unlimited, tracked via lineage_chain | Max 1 level (direct child only) | Reseller model, white-label nesting, network effect | License schema lebih kompleks, tracking overhead |
| D-016 | 2026-05-08 | Death handler: Read-only grace 7 hari, kemudian knowledge return | Auto-delete on expiry | Window untuk backup & final contribution; client control | Grace period = resource gratis selama 7 hari |

**Referensi Locked:** `docs/MIGANCORE_AMOEBA_ARCHITECTURE_LOCKED.md` — Canonical document untuk clone, deployment, dan death model.

---

## 12. RISK & MITIGATION

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R-NEW-01 | Phase 0-1 memakan waktu > 4 minggu | Medium | High | Weekly sprint retro, cut scope jika perlu | Executor |
| R-NEW-02 | SFT identity anchor masih gagal (cosine < 0.85) | Medium | High | Naikkan rank ke 64, tambah epochs, atau pivot ke full fine-tune | Training Agent |
| R-NEW-03 | Beta users tidak aktif, data tidak mengalir | Medium | High | Owner recruit dari network sendiri, incentivize dengan early access | Owner |
| R-NEW-04 | Teacher API cost melebihi $5/day | Low | Medium | Hard cap di code, queue pause ketika cap tercapai | Executor |
| R-NEW-05 | Platform repo tetap empty, misleading | High | Medium | Hapus repo atau isi dengan placeholder yang jelas "coming soon" | DevOps Agent |
| R-NEW-06 | Context loss antar AI agent sessions | High | High | STRICT protocol: baca CONTEXT.md + daily log sebelum kerja | All Agents |
| R-NEW-07 | Schema drift tanpa Alembic | Medium | High | Alembic MANDATORY, CI gagal kalau tidak ada migration | Backend Agent |
| R-NEW-08 | Test suite terlalu lambat, tidak dijalankan | Medium | Medium | Parallel test, mock external APIs, pre-commit hook | QA Agent |

---

## APPENDIX A: DEFINISI SUKSES PER FASE

### Phase 0 Success
```
pytest pass: 100%
alembic upgrade head: pass
CI/CD deploy: automatic to staging
context loss incidents: 0
```

### Phase 1 Success
```
real-data ratio: ≥ 20%
user feedback latency: < 1 jam (thumb → pair)
owner upload: 5 endpoints working
self-growth pairs/day: ≥ 20
teacher pairs/day: ≥ 50
cost/day: ≤ $5
```

### Phase 2 Success
```
multi-loss engine: 4 methods runnable
 eval gate automated: PASS/FAIL deterministic
dataset builder: deterministic, versioned
```

### Phase 3 Success
```
identity cosine sim: > 0.85 (tanpa SOUL prompt)
tool-use accuracy: ≥ 80%
chat quality: ≥ Cycle 3 baseline
```

### Phase 4 Success
```
real-data ratio: ≥ 50%
brain improve from baseline: YES
user retention: ≥ 70%
```

### Phase 5 Success
```
clone time: < 10 menit
white-label: display_name, logo, persona configurable
license: enforceable, tidak bisa circumvent
trilingual: EN + ZH basic working
```

---

*Dokumen ini adalah SINGLE SOURCE OF TRUTH untuk arsitektur Migancore. Setiap perubahan harus melalui PR + review + update dokumen ini.*
