# Week 4 — Decisions Log & Findings Recap
**Date:** 2026-05-04 (Day 28 evening / Day 29 morning)
**Last Agent:** Claude Opus 4.7
**Purpose:** Lock in the path. Prevent scope creep / direction loss. Single source of truth before Week 4 execution.

---

## 🎯 CORE TRUTH (Non-negotiable — DO NOT DEVIATE)

> **Migancore = Autonomous Digital Organism (ADO) — Core Brain AI yang bisa diajak ngobrol, mengingat semua konteks, menggunakan tools, memperbaiki diri setiap minggu, dan melahirkan child agents dengan kepribadian unik.**

**Domain mapping (LOCKED, per kickoff doc):**

| Domain | Role | Status |
|--------|------|--------|
| `migancore.com` | The engine + hosted platform (THE PRODUCT) | ⏳ root empty, build Week 4 |
| `api.migancore.com` | API gateway | ✅ live |
| `app.migancore.com` | Chat UI | ✅ live |
| `app.migancore.com/admin/` | Admin Dashboard | ✅ live |
| `tiranyx.com` | Owner / governance landing | future |
| `mighan.com` | Agent clone marketplace | **Bulan 3+** (only after Migancore ready to breed publicly) |
| `sidixlab.com` | Research lab dashboard | **Bulan 3+** (separate platform) |
| `mighantect3d.com` | 3D consumer | **Bulan 3+** (separate platform) |

**RULE:** Sampai Migancore Core siap berkembang-biak & di-clone publik, **SEMUA development di `migancore.com` + subdomain saja**. Jangan touch consumer domains.

---

## 📜 5-LEVEL EVOLUTION STATUS — ANCHOR ROADMAP

| Level | Original Target | Current Status | What Closes the Gap |
|-------|----------------|----------------|---------------------|
| **L1 — The Seed** | VPS+Ollama+API+Postgres, first token | ✅ DONE Day 1-7 | — |
| **L2 — The Director** | LangGraph+tools+Letta+Qdrant memory | ✅ DONE Day 8-14 | — |
| **L3 — The Factory** | Specialist agents paralel via Celery | ⚠️ Partial (Celery disabled save RAM, tools ok) | Mode templates Day 31 |
| **L4 — The Innovator** | Self-Reward Loop+SimPO+A/B versioning | ⚠️ Pipeline ready, training NEVER triggered | First SimPO run Day 32 |
| **L5 — The Breeder** | Spawn agents live + genealogy tree + marketplace foundation | ⚠️ Backend exists Day 10, NO UI | Spawn UI + Tree Day 29-30 |

---

## ⚠️ 3 PRIOR DIRECTION ERRORS (Pelajaran — JANGAN ULANGI)

### Error 1: "10-Domain ADO" Specialist scope creep
- **What I planned:** Creative Director Agent + Programming + Productivity + 7 lainnya
- **Why wrong:** Original blueprint says **Migancore Core itself harus mature dulu**. 10-domain specialists adalah **Bulan 4+**.
- **Lesson:** Vision ADO 10-domain dari user adalah LONG-TERM (months), not Week 4 scope.
- **Correction:** Week 4 fokus = Level 5 visibility + Level 4 cycle 1 (per blueprint's 30-day plan).

### Error 2: Domain mapping confusion
- **What I assumed:** SIDIX/MighanTech3D = "specialist domains" untuk Migancore agents
- **Reality (kickoff doc):** SIDIX/MighanTech3D = **separate consumer platforms** that will USE Migancore Core in the future
- **Lesson:** Tiranyx ecosystem = host of platforms, Migancore = engine. Hanya Migancore + subdomain yang aktif sekarang.
- **Correction:** Lock all dev to `*.migancore.com`.

### Error 3: Browser-use / Vision API as core priority
- **What I planned:** Browser automation + vision = differentiating features
- **Why wrong:** These are **Bulan 2+ polish**, not original Week 4. Original Week 4 = Self-improvement cycle 1 + agent breeding.
- **Lesson:** "What's hot in 2026 trends" ≠ "what original blueprint says do next." Blueprint wins.
- **Correction:** Browser/Vision DEFERRED. Maybe Week 5 if PRIMARY done early.

---

## ✅ WEEK 4 PLAN — LOCKED (User-Approved)

**Theme:** "Level 5 VISIBLE + Cycle 1 Self-Improvement Triggered"

### 6 PRIMARY ITEMS (Day 29-35)

| # | Item | Day | Why (blueprint reference) |
|---|------|-----|---------------------------|
| 1 | **Agent Spawn UI** in chat.html | 29 | Blueprint Section 8.1: "Owner ... Choose Template ... POST /agents/spawn" |
| 2 | **Genealogy Tree** D3.js force-directed | 30 | Blueprint Section 8.3: "Visualisasi di dashboard: D3.js force-directed graph" |
| 3 | **3 Mode Templates** (customer_success, research_companion, code_pair) | 31 | Blueprint Section 13: kickoff explicitly defines these 3 modes |
| 4 | **First SimPO Training Run** on RunPod ($5.50) | 32 | Blueprint Section 10 Day 24-27: this WAS the deliverable, never executed |
| 5 | **Identity Persistence Eval Set** (20 prompts, ≥0.85 cosine) | 33 | Blueprint Section 7.2: "20 fixed prompts ... cosine sim ... lulus" |
| 6 | **migancore.com Landing Page** | 33 | Kickoff: "Domain migancore.com (produksi)" — currently empty |

### Bonus Items (if time permits, in priority order — A>C>B per user)
- 7. **Hot-swap GGUF** (Day 34) — original Day 25 blueprint
- 8. **A/B test framework** (Day 34) — 10% traffic to new model
- 9. **STT input** + **conversation export** (Day 34-35) — table stakes 2026
- 10. **Vision API** (only if all 1-9 done) — defer browser-use to Week 5

### DEFERRED (Bulan 2+)
- ❌ Multimodal chat input → Bulan 2 (after dogfooding feedback)
- ❌ Browser-use, Firecrawl, GitHub connector → Week 5 or Bulan 2
- ❌ Creative/Programming/Productivity specialist agents → Bulan 4+
- ❌ mighan.com marketplace UI → Bulan 3+
- ❌ sidixlab.com research dashboard → Bulan 3+

---

## 📊 STATE AT START OF WEEK 4 (Day 29 AM)

### Production
| Component | Status |
|-----------|--------|
| API v0.4.6 | ✅ healthy |
| Chat UI | ✅ live `app.migancore.com` |
| Admin Dashboard | ✅ live `app.migancore.com/admin/` |
| MCP Server | ✅ 8 tools + 4 resources at `api.migancore.com/mcp/` |
| 4 Teacher APIs | ✅ all 4 verified |
| Distillation pipeline | ⚠️ flaky (Ollama CPU bottleneck) |
| Synthetic generator | ⏸ stopped (avoid Ollama race) |
| Memory pruner | ✅ daily |

### DPO Flywheel
| Source | Pairs | Status |
|--------|-------|--------|
| `synthetic_seed_v1` | 262 | resumed-paused |
| `cai_pipeline` | 15 | live (real chat) |
| `distill_kimi_v1` | 0 | flaky, 6 errors / 7 attempts |
| **TOTAL** | **277** | Need 500+ for SimPO |

### Tooling
- 4 teacher API keys live (Anthropic, Kimi K2.6, OpenAI, Gemini)
- ElevenLabs TTS key + voice (`pIdeS8l1cmJzzqqt7NRc`)
- fal.ai $9.99
- API_KEY_PEPPER set
- 1 active API key on test tenant

### Documentation Coverage
- ✅ CONTEXT.md updated to v0.4.6
- ✅ CHANGELOG.md complete
- ✅ SPRINT_LOG.md (Days 0-28)
- ✅ HANDOFF.md (comprehensive)
- ✅ MCP_USAGE.md
- ✅ DAY26/27/28_PLAN.md
- ✅ WEEK4_PLAN.md (revised, blueprint-aligned)
- ✅ This file (WEEK4_DECISIONS_LOG.md)

---

## 🛠️ KEY TECHNICAL DECISIONS (Locked)

1. **Distillation Ollama bottleneck** — Run as background pipeline ONLY when synthetic gen idle. Won't be primary path. **Synthetic + CAI = primary data sources**.
2. **Identity eval reference** = current Qwen2.5-7B base responses on 20 fixed prompts (set frozen Day 33)
3. **Cycle 1 trainer** = Unsloth + QLoRA + SimPO on RunPod RTX 4090 spot ($0.34/hr, hard cap $10)
4. **Hot-swap mechanism** = GGUF Q4_K_M conversion + Ollama `pull migancore/v0.1` + ENV var swap
5. **A/B routing** = `X-Model-Version` header, 10% to new, 90% baseline, 24h eval window
6. **Mode templates location** = `config/personalities.yaml` (not separate files — keep config minimal)
7. **Spawn UI auth** = JWT (current chat) — works as-is, no changes needed
8. **Genealogy library** = `react-force-graph` via CDN (no build step, matches existing pattern)
9. **Landing page tech** = static HTML + design system tokens (same as chat.html/dashboard.html)
10. **Public stats endpoint** for landing widget = `GET /v1/public/stats` (read-only, no auth, rate-limited)

---

## ⚙️ COST DISCIPLINE

| Item | Budget | Actual to date | Remaining buffer |
|------|--------|----------------|------------------|
| Anthropic Claude | $4.55 | ~$0.01 | $4.54 |
| Kimi K2 | $2.00 | $0 (errors) | $2.00 |
| OpenAI GPT | $5+ | ~$0.001 | $5+ |
| Gemini | free | $0 | unlimited |
| ElevenLabs | $5.00 | $0 | $5.00 |
| fal.ai | $9.99 | ~$0.01 | $9.98 |
| **RunPod (planned Week 4)** | $10 cap | $0 | $10 |
| **Total** | ~$36 | ~$0.02 | ~$36 |

**Hard rule:** Hentikan tugas apapun yang potential cost > $1 tanpa explicit approval.

---

## 🚦 EXECUTION DISCIPLINE — RULES UNTUK WEEK 4

1. **Every commit = updates progress note** (this file or daily progress)
2. **Every PRIMARY item = own commit** (atomic)
3. **No new dependencies tanpa rationale doc** (kalau add library, jelaskan kenapa)
4. **Cost > $1 = stop + ask** (RunPod, distillation batch besar)
5. **Skip = document + adapt** (kalau item ditunda, tulis kenapa di file ini)
6. **Container --build flag mandatory** untuk code changes (lesson Day 28)
7. **Bash here-doc untuk multi-line script** (avoid PowerShell quote hell)
8. **`docs/CONTEXT.md` updated end of each day**

---

## 🎯 EXIT CRITERIA — WEEK 4 (Day 35)

Must-haves:
- [ ] PRIMARY 1 (Spawn UI) shipped + E2E tested
- [ ] PRIMARY 2 (Genealogy Tree) live in dashboard
- [ ] PRIMARY 3 (3 Mode Templates) working spawn from each
- [ ] PRIMARY 4 (SimPO Training) attempted, result documented
- [ ] PRIMARY 5 (Identity Eval) committed, run on baseline
- [ ] PRIMARY 6 (migancore.com landing) HTTP 200 live
- [ ] Total DPO pairs ≥ 500 (training-ready threshold)
- [ ] All Week 4 docs updated (CONTEXT, CHANGELOG, SPRINT_LOG)
- [ ] WEEK4_RETRO.md written
- [ ] BULAN2_PLAN.md drafted (5 beta dogfooding)

If any miss → carry to Week 5 first 2 days, document why.

---

## 🔁 PROTOCOL CHECKPOINT (Mandatory before each Day's work)

Each day morning:
1. ✅ Read this file (decisions log) — anti scope-creep
2. ✅ Check current distillation/synthetic state
3. ✅ Re-confirm today's deliverable matches PRIMARY list
4. ✅ Cost check (RunPod balance)
5. Begin work

Each day evening:
1. ✅ Commit + push
2. ✅ Update CONTEXT.md
3. ✅ Daily log in `docs/logs/daily/YYYY-MM-DD.md` (per kickoff convention)
4. ✅ Distillation/synthetic restart if stopped

---

**THIS IS THE COMPASS. Refer back when in doubt.**
