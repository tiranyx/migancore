# Week 4 Retrospective — Day 28→35
**Sprint:** 2026-05-04 (compressed single-day execution after Day 28 distillation+dashboard ship)
**Lead Agent:** Claude Opus 4.7 (1m context)
**Outcome:** v0.5.0 milestone shipped — Level 5 visible + Cycle 1 ready

---

## 🎯 Original Week 4 Plan (recall)

Per `docs/WEEK4_DECISIONS_LOG.md` (the COMPASS):

**6 PRIMARY items:**
1. Agent Spawn UI in chat.html
2. Genealogy Tree D3.js visualization
3. 3 Mode Templates (customer_success, research_companion, code_pair)
4. First SimPO Training Run on RunPod ($5.50)
5. Identity Persistence Eval Set (20 prompts, ≥0.85 cosine)
6. migancore.com landing page

**Constraint:** ALL dev on `migancore.com` + subdomain. Consumer domains Bulan 3+.

---

## ✅ DELIVERED (5/6 PRIMARY shipped, 1 deferred)

### 1. ✅ Spawn UI (Day 29) — chat.html
**Code:** `frontend/chat.html` +407 lines
- AGENTS sidebar section dengan generation badges (G0/G1/G2)
- Agent switcher: click = switch + reset chat state
- "+ SPAWN CHILD" button → SpawnModal
- Modal: name + voice/tone/values + template dropdown (Day 31)
- Auto-switch to new child after spawn

**Backend additions (`api/routers/agents.py`):**
- `GET /v1/agents` — list all tenant agents
- `GET /v1/agents/genealogy` — flat tree for visualization
- `GET /v1/agents/templates` — list 3 mode templates

**E2E verified:** spawn → 4 agents in tree (3 G0 + 1 G1 DemoChildAgent)

### 2. ✅ Genealogy Tree D3.js (Day 30) — dashboard.html
**Code:** `frontend/dashboard.html` +297 lines
- D3.js v7 force-directed graph (CDN)
- Tab navigation: 📊 Overview | 🌳 Lineage
- Color-coded by generation: orange=G0, green=G1, blue=G2, purple=G3+
- Drag to reposition, click for detail panel
- Auto-refresh every 8s
- Generation count legend

**Backend (`api/routers/admin.py`):**
- `GET /v1/admin/genealogy` — system-wide cross-tenant view
- **RLS bug + fix**: agents table has Row-Level Security; iterate per-tenant with `set_tenant_context` instead of single global query

### 3. ✅ 3 Mode Templates (Day 31)
**Config:** `config/personalities.yaml` (per kickoff doc Section 13)
- `customer_success` — warm, patient, solution-oriented
- `research_companion` — curious, rigorous, citation-disciplined
- `code_pair` — senior engineer, terse, type-aware, tests-suggested

**Backend:**
- `services/config_loader.py::load_personality_templates()` + `get_personality_template()`
- `requirements.txt`: pyyaml>=6.0
- Spawn handler applies template fields to persona_blob (overridable)

**Frontend:** Spawn modal dropdown → auto-fill voice/tone/values when template selected

**E2E verified:** spawned `ResearchHelperD31` with `template_id=research_companion`

### 4. ⚠️ DEFERRED: First SimPO Training Run (Day 32)
**Reason:** DPO pool 277 pairs vs 500 threshold. Not enough yet.

**Scripts READY (committed):**
- `training/export_dataset.py` — pull pairs to JSONL with 50/30/20 mix + identity anchors
- `training/train_simpo.py` — Unsloth + QLoRA + SimPO on RunPod RTX 4090
- `training/convert_gguf.py` — adapter → GGUF Q4_K_M for hot-swap
- `training/README.md` — full workflow + cost breakdown

**Trigger condition:** When DPO pool ≥ 500 pairs (synthetic resumed, growing toward 1000 target).

### 5. ✅ Identity Persistence Eval (Day 33)
**Code:**
- `eval/persona_consistency_v1.jsonl` — 20 prompts across 8 categories (identity, values, voice, anti-pattern, tool-use, reasoning, creative, code, indonesian-cultural, honesty, evolution-aware)
- `eval/run_identity_eval.py` — 2 modes: `--mode reference` (capture baseline), `--mode eval` (gate ≥0.85 cosine sim)
- Uses fastembed + cosine similarity
- Decision: PROMOTE or ROLLBACK

**Status:** Set committed. Will run reference baseline before Day 32 SimPO trigger.

### 6. ✅ migancore.com Landing Page (Day 33)
**Code:** `frontend/landing.html` (621 lines)
- Hero: "The AI Core Brain that learns weekly, spawns child agents, and improves itself"
- Live Stats Widget (auto-refresh 30s) — DPO pairs, sources, training status
- 5 Levels of Evolution section with current status badges
- 6 Differentiators cards (self-improving, genealogy, ID-first, MCP, SOUL, open core)
- OG meta tags for social sharing

**Backend:**
- `GET /v1/public/stats` — sanitized aggregate (no PII, no per-tenant)
- CORS: `migancore.com` added to allowlist

**Infrastructure:**
- `nginx vhost` `/www/server/panel/vhost/nginx/migancore.com.conf`
- `Let's Encrypt cert` issued via certbot webroot (expires 2026-08-02)
- HTTP→HTTPS redirect
- Deployed to `/www/wwwroot/migancore.com/index.html`

**LIVE: https://migancore.com — HTTP 200, 18.8KB served, SSL valid**

---

## 🎁 BONUS Day 34 (committed, ready for execution)

**`docs/HOT_SWAP_GUIDE.md`** — Day 34+ workflow:
- Pull GGUF to Ollama
- A/B header routing (`X-Model-Version`)
- 24h test plan with metrics
- Promote / rollback procedure
- Cost audit per cycle: ~$6.20

---

## 📊 Metrics Achieved (Day 35 close)

| Metric | Day 28 baseline | Day 35 actual |
|--------|----------------|---------------|
| API version | 0.4.6 | **0.5.0** ⭐ |
| Endpoints (frontend) | 2 (chat, admin) | **3** (+ landing) |
| Backend routes | ~25 | **30+** (added agents/genealogy/templates, public/stats, admin/genealogy) |
| MCP tools | 8 | 8 (+ resource exposure) |
| Mode templates | 0 | **3** |
| DPO pairs | 277 | 277 (synthetic resumed, growing) |
| Agents in DB | 3 | **4** (+1 spawned G1) |
| Live domains | 2 (api., app.) | **3** (api., app., **migancore.com**) |
| SSL certs | 2 | **3** (added migancore.com + www.) |
| Training scripts | 0 | **4** (export, train, convert, eval) |
| Documentation files | ~10 | **12+** (added DECISIONS_LOG, HOT_SWAP_GUIDE, RETRO, BULAN2_PLAN) |

---

## 🏆 KEY WINS

1. **Level 5 (The Breeder) NOW VISIBLE** — original blueprint signature feature finally usable from UI
2. **migancore.com LIVE PUBLICLY** — public face of the product, narrative starts
3. **3 Mode Templates** — proves Level 3 (The Factory) extensible architecture
4. **Training pipeline ready** — Cycle 1 unblocked when data hits 500
5. **RLS bug discovered+fixed** — admin queries now properly iterate tenants
6. **D3.js genealogy** — sticky shareable visual for narrative
7. **v0.5.0 milestone** — semantic versioning bump signals major deliverable
8. **Honest scope discipline** — no creep into 10-domain ADO, stayed laser-focused on blueprint
9. **0 production downtime** despite 8+ deploys in single session
10. **All commits documented** — daily log + per-commit narrative for future agents

---

## ❌ MISSES (Honest)

1. **SimPO training NOT triggered** — pool below 500. Acceptable per Decision Log adaptation rule (defer until ready). Cost saved: $5.50.
2. **Distillation pipeline still flaky** — Ollama CPU bottleneck unresolved. Synthetic remains primary.
3. **Some test scripts had Python heredoc parsing bugs** — wasted ~15 min debugging chr() escapes. Lesson: write test scripts as files, not inline bash.
4. **A/B framework Day 34 only DOCUMENTED** — actual implementation deferred (no model trained yet to A/B).
5. **`migancore.com` still no Open Graph image** — landing has og:image meta but file `/og-image.png` not yet created. Cosmetic.

---

## 📚 LESSONS LEARNED (capture for future agents)

### Technical
1. **FastAPI route declaration order matters** — `/{param}` catches more specific paths if declared first. Always concrete BEFORE parameterized. Add inline comments as anti-regression doc.
2. **PostgreSQL RLS requires per-tenant context for raw SQL queries** — admin endpoints must iterate tenants and `set_tenant_context` per query, OR use a BYPASSRLS role.
3. **Container `--build` flag mandatory** — `--force-recreate` reuses old image. Code changes need explicit rebuild.
4. **Embedding model load is slow startup** — when synthetic gen running, fastembed takes 60-90s vs <10s idle. Plan deploys with 2-minute wait windows.
5. **Ollama CPU 100% saturated by 7B inference** — distillation pipeline cannot run concurrent with synthetic gen. Serialize them.
6. **PyYAML safe_load for config** — no eval risk, robust failure mode.
7. **D3.js v7 force-directed graph** — `forceLink + forceManyBody + forceCenter + forceCollide` baseline. Drag handlers via `d3.drag`.

### Process
1. **`WEEK4_DECISIONS_LOG.md` saved us from scope creep** — when in doubt, refer to compass doc. User-approved boundaries held firm.
2. **Original blueprint > current trends** — researcher proposed Creative Director / browser-use; blueprint said Level 5 visibility. Blueprint won, was correct.
3. **Domain mapping clarity early** — Tiranyx/SIDIX/MighanTech3D = future consumers, not current scope. Saved week of misdirected work.
4. **Daily log convention works** — `docs/logs/daily/YYYY-MM-DD.md` per kickoff doc keeps continuity.
5. **Atomic commits per Day** — 11+ commits in Week 4, each focused on 1 PRIMARY item. Easy to review/rollback.
6. **PowerShell quote escape hell** — write all multi-line scripts as files (`Write` tool) then `scp + bash`. Don't fight `ssh "..."`.
7. **Monitor + Bash run_in_background** for slow operations — keep working in parallel, get notified on completion.

### Strategic
1. **"Win 1 thing completely" trumps "ship 10 things partially"** — Level 5 visibility ships > 10 specialist agents half-done
2. **Public narrative needs ARTIFACT** — `migancore.com` landing is the artifact. Without it, internal progress = invisible
3. **Cost discipline preserves runway** — Week 4 spent ~$0 on external APIs (deferred SimPO to when data ready). $26 reserve preserved
4. **Open core model holds** — engine + UX live publicly, marketplace/billing for Bulan 3+

---

## 💰 Cost Audit Week 4

| Item | Estimate | Actual | Notes |
|------|----------|--------|-------|
| Distillation testing (Day 28) | $5 | ~$0 (errors, no charges) | Kimi pipeline flaky |
| ElevenLabs TTS testing | $1 | $0 | Free tier sufficient |
| fal.ai image gen | $3 | ~$0.01 | Cached prior tests |
| Anthropic Claude API | $2 | ~$0.01 | Smoke tests only |
| OpenAI GPT API | $2 | ~$0.001 | Smoke tests only |
| Gemini API | free | $0 | — |
| RunPod (planned for Day 32) | $5.50 | $0 | Deferred — pool not ready |
| Let's Encrypt cert | $0 | $0 | Free |
| **TOTAL Week 4** | $18.50 | **<$0.05** | Under-budget by 99.7% |

**Reserve:** ~$26 across all providers + entire RunPod budget intact for Bulan 2.

---

## 🛣️ HANDOFF TO BULAN 2

See `docs/BULAN2_PLAN.md` for next 30 days.

**Critical context for next agent:**
- Reference `WEEK4_DECISIONS_LOG.md` first (compass)
- v0.5.0 = current milestone
- 3 domains live (api/app/landing migancore.com)
- All consumer domains (mighan.com, sidixlab.com, etc.) DEFERRED to Bulan 3+
- 5 beta dogfooding next phase
- SimPO training trigger when DPO ≥ 500
