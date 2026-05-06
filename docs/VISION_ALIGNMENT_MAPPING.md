# VISION ALIGNMENT MAPPING — Day 60
**Date:** 2026-05-07 | **Status:** ACTIVE — Direction LOCK per owner
**Purpose:** Sinkronisasi visi besar (MIGANCORE-PROJECT-BRIEF.md) dengan realitas teknis Day 1-60.
**Rule:** JANGAN pivot. SELARASKAN.

---

## Executive Summary

Owner Fahmi telah mengkomunikasikan **visi besar ADO MiganCore** melalui `MIGANCORE-PROJECT-BRIEF.md` (di-download ke `C:\Users\ASUS\Downloads\`). Dokumen ini mendefinisikan produk komersial yang mature: platform self-hosted ADO dengan white-label, license system, trilingual (ID/EN/ZH), dan business model SaaS.

**Status saat ini (Day 60):**
- Self-improving loop: **PROVEN ✅** (3 cycles, 2 PROMOTE)
- Identity layer: **STRONG ✅** (0.953)
- Self-hosted deployment: **LIVE ✅** (VPS, Docker, Ollama)
- Zero data leak: **BY ARCHITECTURE ✅** (self-hosted, no external calls)
- Voice naturalness: **IMPROVING ✅** (0.715 → 0.817, target 0.85+)

**Gap antara visi dan realitas:** Signifikan di frontend, license system, white-label, dan trilingual. Ini adalah pekerjaan struktural, bukan pivot.

---

## 1. VISI vs REALITAS — Detailed Mapping

### 1.1 Core Concept: ADO Three Layers

| Layer (Visi) | Visi Dokumen | Realitas Day 60 | Status | Action |
|--------------|--------------|-----------------|--------|--------|
| **Otak** | Cognitive Core — reasoning, analisis, sintesis, self-learning | FastAPI + LangGraph + Qwen2.5-7B + ORPO training pipeline | ✅ **ALIGNED** | Upgrade ke Qwen3-8B (Day 65+) |
| **Syaraf** | Integration Layer — MCP tools, API, workflow, memory | 23 tools, MCP server, Qdrant memory, Redis cache | ✅ **ALIGNED** | Expand MCP ecosystem |
| **Jiwa** | Identity Layer — persona, value alignment, tujuan org | SOUL.md + identity_anchor_v2 pairs + eval gate | ✅ **ALIGNED** | Add trilingual identity |

**Assessment:** Three-layer architecture sudah ada dalam bentuk fungsional. Jiwa (identity) sudah proven dengan 3 training cycles. Otak (reasoning) di 0.994 — hampir sempurna.

---

### 1.2 Product Features

| Feature | Visi Dokumen | Realitas Day 60 | Gap | Priority |
|---------|--------------|-----------------|-----|----------|
| **White-label** | Client bebas namai ADO ("SARI", "LEX") | Belum ada | 🔴 HIGH | Phase 2 sprint |
| **License system** | HMAC-SHA256 license file, offline validator | Belum ada | 🔴 HIGH | Phase 1 sprint |
| **Trilingual** | ID/EN/ZH native | Indonesian only | 🟡 MEDIUM | Phase 2 sprint |
| **Clone mechanism** | 1-click clone base → org instance | Manual deployment | 🟡 MEDIUM | Phase 2 sprint |
| **Business data training** | Upload SOP → RAG → fine-tune | Basic RAG exists, no upload UI | 🟡 MEDIUM | Phase 2-3 |
| **Business flow training** | Input workflow → ADO pahami alur | Belum ada | 🟡 MEDIUM | Phase 2-3 |
| **Self-learning loop** | Data → train → improve → deploy | **PROVEN ✅** (3 cycles) | ✅ ALIGNED | Continue Cycle 4+ |
| **Self-hosted** | VPS client / on-premise | **LIVE ✅** | ✅ ALIGNED | Maintain |
| **Zero data leak** | No external calls, encrypted | **BY ARCHITECTURE ✅** | ✅ ALIGNED | Maintain |
| **MCP integration** | Pluggable tools | 23 tools, MCP server | ✅ **ALIGNED** | Expand marketplace |

---

### 1.3 Tech Stack

| Component | Visi Dokumen | Realitas Day 60 | Gap | Action |
|-----------|--------------|-----------------|-----|--------|
| **Base LLM** | Qwen3-8B | Qwen2.5-7B | 🟡 MEDIUM | Upgrade path planned (Day 65+) |
| **Frontend** | Next.js 14 + TypeScript | Static HTML (chat.html) | 🔴 HIGH | Migration needed |
| **API** | FastAPI | **FastAPI ✅** | ✅ ALIGNED | Maintain |
| **RAG/Memory** | ChromaDB atau Qdrant | **Qdrant ✅** | ✅ ALIGNED | Add ChromaDB option |
| **Deployment** | Docker + Coolify/aaPanel | **Docker + aaPanel ✅** | ✅ ALIGNED | Maintain |
| **Database** | PostgreSQL + SQLite per instance | PostgreSQL only | 🟡 MEDIUM | Add SQLite per instance |
| **Auth** | NextAuth v5 / JWT | Basic auth exists | 🟡 MEDIUM | Upgrade to NextAuth |
| **i18n** | next-intl (ID/EN/ZH) | None | 🟡 MEDIUM | Implement next-intl |

---

### 1.4 Business Model

| Stream | Visi Dokumen | Realitas Day 60 | Gap |
|--------|--------------|-----------------|-----|
| **License Fee (SaaS)** | Basic/Pro/Enterprise tiers | Belum ada billing | 🔴 HIGH |
| **Setup Fee** | Rp 5-25 jt one-time | Belum ada | 🔴 HIGH |
| **Training Service** | Rp 2-8 jt per sesi | Training pipeline exists, no service layer | 🟡 MEDIUM |
| **Reseller Program** | 30-40% revenue share | Belum ada | 🟡 MEDIUM |
| **Marketplace** | Skill/tools plugin | 23 tools exist, no marketplace UI | 🟡 MEDIUM |

---

## 2. STRENGTHS — What We Have Built (Day 1-60)

### 2.1 Self-Improving Loop — VALIDATED ✅

```
User Chat → CAI Quorum → Synthetic Pairs → ORPO Training → Eval Gate → Deploy
```

**Proof:**
- Cycle 1: DPO generic → ROLLBACK (0.6697)
- Cycle 2: ORPO identity-anchored → PROMOTE (0.8744)
- Cycle 3: ORPO identity + voice + tool + code → PROMOTE (0.9082)

**This is the moat.** Tidak ada kompetitor yang punya closed-loop self-improvement yang sudah proven 3x.

### 2.2 Identity Preservation — STRONG ✅

- Identity score: 0.953 (threshold 0.80)
- Model knows it's Mighan-Core, not Anthropic/ChatGPT
- Voice naturalness: 0.817 (naik dari 0.715)
- Bahasa Indonesia primary: proven

### 2.3 Cost Efficiency — UNBEATABLE ✅

| Item | Cost |
|------|------|
| Cycle 1 (fail) | ~$1.50 |
| Cycle 2 (PROMOTE) | ~$0.15 |
| Cycle 3 (PROMOTE) | ~$0.16 |
| **Total Day 56-60** | **~$1.81** |
| 3 training cycles + deploy | **<$2.00** |

Kompetitor (OpenAI, Anthropic API): $0.01-0.03 per 1K tokens = $100+ per bulan untuk usage moderate. MiganCore: sekali training, run forever on VPS.

### 2.4 Infrastructure — PROVEN ✅

- VPS self-hosted: running
- Docker Compose: running
- Ollama hot-swap: proven (0.1 → 0.2 → 0.3)
- MCP server: 23 tools
- Memory (Qdrant + Redis): running

---

## 3. GAPS — What Needs Building

### 🔴 HIGH PRIORITY (Phase 1-2)

#### 3.1 License System
**Why critical:** Without license enforcement, produk tidak bisa dijual. Client bisa copy-paste tanpa bayar.
**What to build:**
- License file schema (JSON with HMAC-SHA256 signature)
- Offline validator (no phone-home)
- Expired → read-only mode
- Revoked → grace period 7 hari

#### 3.2 White-Label System
**Why critical:** Core differentiator dari kompetitor. Client harus bisa namai ADO mereka sendiri.
**What to build:**
- `display_name` config per instance
- Logo & color theme config
- Persona override (tetap inherit SOUL.md base)
- "Powered by Migancore × Tiranyx" watermark (non-removable)

#### 3.3 Next.js 14 Frontend
**Why critical:** Static HTML tidak scalable untuk platform. Perlu proper SPA dengan routing, state management, i18n.
**What to build:**
- Migrate dari `chat.html` → Next.js 14
- TypeScript strict
- next-intl untuk ID/EN/ZH
- Dashboard untuk monitoring

### 🟡 MEDIUM PRIORITY (Phase 2-3)

#### 3.4 Trilingual Support
**Why important:** Market expansion ke SEA (English) dan China (Mandarin).
**What to build:**
- System prompt trilingual switching
- UI i18n (next-intl)
- Eval prompts untuk EN dan ZH
- Identity pairs untuk EN dan ZH personas

#### 3.5 Clone Mechanism
**Why important:** Core product value — 1 base → ratusan instance.
**What to build:**
- Base ADO template (Docker image pre-configured)
- Clone script: copy config → generate license → deploy
- Per-instance isolation (database, memory, model)

#### 3.6 Business Data Training UI
**Why important:** Client perlu bisa upload data internal tanpa coding.
**What to build:**
- Upload interface (PDF, DOCX, CSV)
- Chunking & indexing pipeline
- RAG hot-reload
- Validation & test interface

---

## 4. ROADMAP REVISED — Day 60+ Alignment

### Sprint 61-65: Cycle 4 Training + Foundation
**Focus:** Fix remaining weaknesses + build license foundation

| Task | Owner | Target |
|------|-------|--------|
| Cycle 4 dataset (evolution + creativity + tool-use) | Claude | 200-300 pairs |
| Cycle 4 training (ORPO, target ≥0.92) | Claude | PROMOTE |
| License schema + validator skeleton | Claude/Kimi | Draft |
| White-label config schema | Claude | Draft |
| Qwen3-8B research + compatibility check | Kimi | Report |

### Sprint 66-70: White-Label + Clone + Trilingual
**Focus:** Core product features untuk commercialization

| Task | Owner | Target |
|------|-------|--------|
| White-label system (display_name, logo, persona override) | Claude | MVP |
| License enforcement (validator, expiry, revoke) | Claude | MVP |
| Clone mechanism (base template → instance) | Claude | MVP |
| Trilingual system prompt + eval | Kimi/Claude | ID/EN/ZH ready |
| Next.js 14 migration (chat page) | Claude | MVP |

### Sprint 71-75: Platform + Business Data Training
**Focus:** migancore.com platform untuk client self-service

| Task | Owner | Target |
|------|-------|--------|
| ADO Builder UI (config without coding) | Claude | MVP |
| Business data upload + RAG | Claude | MVP |
| Deploy wizard (Docker config generator) | Claude | MVP |
| Dashboard (monitoring, logs) | Claude | MVP |
| Billing integration (stripe/xendit) | Claude | Backend ready |

### Sprint 76-80: Go-to-Market
**Focus:** First 7 paying clients

| Task | Owner | Target |
|------|-------|--------|
| Landing page migancore.com (trilingual) | Claude | Live |
| Documentation trilingual | Kimi | Complete |
| Reseller portal | Claude | MVP |
| First 7 clients onboarding | Fahmi | Closed |

---

## 5. CYCLE 4 SPECIFIC (Day 61-66)

### Weaknesses from Cycle 3 Eval

| Category | Score | Target | Action |
|----------|-------|--------|--------|
| evolution-aware | **0.568** | ≥0.80 | Regenerate 5 pairs dengan gaya aligned |
| creative | **0.695** | ≥0.80 | Add 20-30 creative pairs |
| tool-use | **0.797** | ≥0.85 | Add more tool-use discrimination pairs |
| voice | 0.817 | ≥0.85 | Add conversational Bahasa Indonesia pairs |
| identity | 0.953 | ≥0.95 | Maintain |
| reasoning | 0.994 | ≥0.99 | Maintain |
| code | 0.929 | ≥0.92 | Maintain |

### Dataset Plan Cycle 4

| Source | Count | Focus |
|--------|-------|-------|
| evolution_fixed_v1 | 20 | Regenerate 5 pairs dengan better alignment |
| creative_anchor_v1 | 30 | Creative writing, storytelling, ideation |
| tool_use_enhanced_v1 | 50 | Tool discrimination (when to use, when not) |
| voice_conversational_v1 | 50 | Casual Indonesian greeting, small talk |
| identity_reinforcement_v1 | 50 | Identity hardening (edge cases) |
| **Total new** | **200** | |
| **+ Cycle 3 best 685** | **885** | **Cycle 4 training ready** |

---

## 6. QWEN3-8B UPGRADE PATH

Dokumen visi mensyaratkan Qwen3-8B sebagai base model. Ini adalah upgrade strategis:

| Aspect | Qwen2.5-7B (Current) | Qwen3-8B (Target) |
|--------|---------------------|-------------------|
| Parameters | 7B | 8B |
| Native trilingual | Partial | **Full ✅** |
| Reasoning | Good | **Excellent (thinking mode)** |
| Context window | 128K | 128K |
| Tool calling | Good | **Better** |
| Self-hosted VRAM | ~8GB Q4 | ~10GB Q4 |
| License | Open | MIT-compatible |

**Upgrade plan:**
1. Day 65-70: Research Qwen3-8B compatibility (tokenizer, TRL, Ollama)
2. Day 71-75: Baseline eval dengan Qwen3-8B (no adapter)
3. Day 76-80: Cycle 5 training on Qwen3-8B base
4. Day 81+: Gradual migration (A/B test Qwen2.5 vs Qwen3)

---

## 7. COMPETITIVE POSITIONING UPDATE

Dengan visi baru, positioning MiganCore menjadi lebih tajam:

### vs ChatGPT/Claude API
| Aspect | Them | MiganCore |
|--------|------|-----------|
| Data privacy | Cloud, can be subpoenaed | **Self-hosted, zero leak** |
| Identity | Generic | **Mighan-Core, customizable** |
| Self-learning | None | **Closed loop proven** |
| Cost | $0.01-0.03/1K tokens | **Once trained, run forever** |
| White-label | No | **Full white-label** |

### vs Custom Bot/GPT
| Aspect | Them | MiganCore |
|--------|------|-----------|
| Self-hosted | Partial | **Full VPS/on-premise** |
| Retrain | Manual prompt | **Upload data → auto train** |
| Clone | No | **1-click clone per org** |
| License | Platform-dependent | **Migancore × Tiranyx** |

---

## 8. NON-NEGOTIABLES (from Dokumen Visi)

1. ✅ **Zero Data Leak** — Sudah by architecture (self-hosted)
2. ✅ **Self-Hosted di Infrastruktur Client** — Sudah live
3. 🔄 **Modular Clone** — Perlu build clone mechanism
4. ✅ **Retrain by Owner** — Training pipeline proven
5. ✅ **Base Skills Pre-loaded** — 23 tools, memory, reasoning
6. 🔄 **White-label Naming** — Perlu build white-label system
7. 🔄 **Licensed Migancore × Tiranyx** — Perlu build license system
8. ✅ **Anti Vendor Lock-in** — Open weights, migratable
9. 🔄 **Trilingual by Design** — Perlu implement EN/ZH

---

## 9. SIGN-OFF

**Kimi Assessment:**
> Visi baru adalah **evolusi natural**, bukan pivot. Semua yang dibangun Day 1-60 (self-improving loop, identity, self-hosted) adalah fondasi yang VALID untuk visi komersial ini. Gap ada di frontend, license, dan white-label — ini adalah pekerjaan struktural yang bisa dikerjakan sambil training cycles berlanjut.
>
> **Rekomendasi:** Continue Cycle 4 training (fix evolution + creativity + tool-use) SEMENTARA building license + white-label skeleton di background. Jangan pause training untuk feature development.

**Owner Direction:**
> Direction LOCK — jangan pivot dari MIGANCORE-PROJECT-BRIEF.md. Selaraskan semua.

---

*Document: VISION_ALIGNMENT_MAPPING.md*
*Created: 2026-05-07 by Kimi Code CLI*
*Next review: Day 65 (mid-Cycle 4 checkpoint)*
