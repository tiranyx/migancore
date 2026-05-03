# WEEK 4 PLAN — "Level 5 Visible + Cycle 1 Self-Improvement"
**Date Drafted:** 2026-05-04 (Day 28 evening) | **REVISED** after re-reading original blueprint
**Agent:** Claude Opus 4.7
**Type:** Strategic Plan — protocol audit, vision-aligned to original 5-Level Evolution

---

## 🎯 NORTH STAR (per Original Blueprint + Kickoff Doc)

> **Migancore = Autonomous Digital Organism — Core Brain AI yang bisa diajak ngobrol, mengingat semua konteks, menggunakan tools, memperbaiki diri setiap minggu, dan melahirkan child agents dengan kepribadian unik.**

**Domain mapping (per kickoff):**
- `migancore.com` → produksi platform (the engine + hosted service)
- `sidixlab.com` → research lab (separate platform — defer Bulan 3+)
- `tiranyx.com` → owner / landing
- `mighan.com` → agent clone marketplace (separate platform — defer Bulan 3+)

**KRITIS:** Tiranyx, SIDIX, MighanTech3D adalah **future consumers**, bukan scope sekarang. **Week 4 fokus = Migancore Core itself harus mature.**

---

## 📊 STATE ASSESSMENT — 5-Level Evolution Status (Day 28)

| Level | Original target | Status now | Verdict |
|-------|----------------|------------|---------|
| **L1 — The Seed** | VPS+Ollama+API+Postgres, first token | ✅ **DONE** Day 1-7 | Solid |
| **L2 — The Director** | LangGraph + tools + Letta+Qdrant memory | ✅ **DONE** Day 8-14 | Solid |
| **L3 — The Factory** | Specialist agents paralel via Celery | ⚠️ **Tools ready, true parallel specialist BELUM** | Celery disabled in compose (saves RAM); orchestration via tool_executor |
| **L4 — The Innovator** | Self-Reward Loop + SimPO training otomatis + A/B model | ✅ **Pipeline DONE Day 15-28**, **Training run NEVER triggered** | Data ready, kompute belum dipakai |
| **L5 — The Breeder** | Agent spawning live, genealogy tree, marketplace foundation | ⚠️ **Backend ada (Day 10), VISIBILITY/UX BELUM** | Spawn endpoint works, but no UI, no public showcase |

**Bonus achievements (di luar plan original):**
- ✅ MCP Streamable HTTP server (Day 26-27) — distribution layer
- ✅ 4-teacher distillation pipeline (Day 28) — beyond Self-Rewarding only
- ✅ Admin Dashboard (Day 28) — beyond Sidixlab dashboard mentioned
- ✅ API key system + migan CLI (Day 27)

---

## ⚠️ WHAT'S MISSING vs ORIGINAL VISION (Honest Audit)

### 🔴 KRITIS — Level 5 Visibility Gap
1. **Genealogy Tree UI** — Backend has `parent_agent_id`, kickoff explicitly mentions D3.js force-directed graph visualization. **NONE EXISTS.**
2. **Agent Spawn UI di chat.html / dashboard** — Backend works (`POST /v1/agents/{id}/spawn`), UI tidak ada. User tidak bisa actually CREATE child agent visually.
3. **Mode templates aktif** — Kickoff defines: `customer_success`, `research_companion`, `code_pair` modes. Hanya 2 templates ada di `agents.json` (core_brain + aria_template). 1 specialist live = 0.
4. **Public-facing migancore.com landing page** — Currently `migancore.com` (root) tidak ada. Hanya `app.migancore.com` (chat) dan `api.migancore.com`. Tidak ada "this is the product" page.

### 🟡 MODERATE — Level 4 Final Lap
5. **First SimPO training run** — Pipeline ready, data ~277 pairs, threshold 500. **Should trigger by Day 32-33** when data hits 500+.
6. **Identity persistence eval set** — Original blueprint: "20 fixed prompts, response harus match >0.85 cosine sim dengan reference responses." **NOT BUILT.**
7. **GGUF hot-swap mechanism** — Original Day 25: "Hot-swap GGUF in Ollama, A/B test 50 prompts vs base." **NOT BUILT** (deploy mechanism for trained model).
8. **Sleep-time compute (Letta consolidation)** — Letta running but not actively consolidating idle.

### 🟢 LOW PRIORITY — Production polish (kebutuhan UX 2026)
9. Multimodal chat input (image/file attach)
10. Voice I/O (TTS already done, STT pending)
11. Conversation export
12. Browser-use / external connectors

---

## 🗓️ WEEK 4 OBJECTIVES (Day 29-35) — REVISED

**Theme: "Make Level 5 VISIBLE + Trigger Cycle 1 Self-Improvement"**

### PRIMARY (must-ship, original blueprint priority)

1. **Agent Spawn UI** in `app.migancore.com/chat` and `/admin/`
   - "+ Spawn Agent" button → modal with name + persona overrides + tools
   - Calls existing `POST /v1/agents/{parent_id}/spawn` endpoint
   - Lists user's agents + can switch active

2. **Genealogy Tree Visualization** in `app.migancore.com/admin/`
   - D3.js force-directed graph (per kickoff spec)
   - Shows lineage: core_brain → child agents → grandchildren
   - Endpoint: extend existing `/v1/agents/{id}/children` for full tree

3. **Mode Templates** — 3 specialist templates ready to spawn
   - `customer_success.yaml` — warm, patient, solution-oriented
   - `research_companion.yaml` — curious, rigorous, citation-disciplined
   - `code_pair.yaml` — terse, type-aware, tests-suggested
   - Stored in `config/personalities.yaml`, exposed in spawn UI

4. **First SimPO Training Run (Cycle 1)** — original Day 24 deliverable
   - When DPO pairs hit 500+ (synthetic+CAI+distill mix), trigger run
   - RunPod RTX 4090 ($0.69/hr × 8hr ≈ $5.50)
   - Train Qwen2.5-7B base on combined dataset using Unsloth+QLoRA+SimPO
   - Output: GGUF Q4_K_M of `mighan/migancore-7b-soul-v0.1`

5. **Identity Persistence Eval Set** + **A/B test framework**
   - 20 fixed prompts in `eval/persona_consistency_v1.jsonl`
   - Test script: cosine sim of new model response vs reference
   - Gate: must score ≥ 0.85 BEFORE promote new model

6. **Public migancore.com Landing Page**
   - Root domain `migancore.com` saat ini kosong
   - Build static landing: hero, "5 Level Evolution" timeline, live stats from `/v1/admin/stats` (public read-only), CTA to chat
   - Same design system (dark sci-fi)
   - **Sets up "Watch MiganCore Learn" narrative for Bulan 2 dogfooding**

### SECONDARY (nice-to-have if time)

7. **Magpie pipeline** — Original Day 22-23 deliverable, kita pakai variant (synthetic_seed). Audit and align naming.
8. **HF Hub publish** — Original Day 23: publish dataset `migancore/preference-pairs-v1` to HuggingFace
9. **Letta sleep-time compute** — Enable consolidation when API idle
10. **Chat multimodal input** (image/file) — table stakes 2026

### DEFERRED (Bulan 2+, per kickoff timeline)

- ❌ `mighan.com` agent marketplace UI — Bulan 3+
- ❌ `sidixlab.com` research dashboard — Bulan 3+, separate platform
- ❌ Specialist domain expansion (Creative/Marketing/etc 10-domain) — Bulan 4+
- ❌ Multi-tenant billing — Bulan 3+
- ❌ Browser-use, vision API — Week 5 atau Bulan 2

---

## 📐 KPIs / SUCCESS METRICS

| Item | Metric | Target by Day 35 |
|------|--------|------------------|
| Spawn UI | User can spawn child agent via web UI | E2E from chat.html |
| Genealogy tree | D3.js graph showing >= 5 agents in lineage | Live in /admin/ |
| Mode templates | 3 templates loadable, spawn produces persona-correct child | All 3 verified |
| First SimPO run | `migancore-7b-soul-v0.1` GGUF exists in HF Hub | Published |
| Identity eval | 20-prompt eval set + scoring script | Run on baseline + v0.1 |
| migancore.com landing | Live page accessible | HTTP 200 + Lighthouse > 90 |
| **DPO pairs total** | ≥ 1000 pairs (synthetic + distill) | Hit 1000 |
| **Cycle 1 training** | New model evaluated, ≥ 1% above baseline | If pass → A/B 10% traffic |

**Exit criteria for Week 4:** Items 1-6 (PRIMARY) shipped + Cycle 1 training attempted (pass/fail documented).

---

## 🔬 HYPOTHESIS + ADAPTATION

### H1: Spawn UI ≤ 1 day (backend ready, frontend extension)
- Test end Day 29: spawn from chat.html works
- Adapt fail: ship as separate `/admin/spawn` page, dogfooding still possible

### H2: D3.js genealogy tree ≤ 1 day in dashboard
- Test end Day 30: tree renders for test tenant
- Adapt fail: simple table view + indented list (vis later)

### H3: 500 DPO pairs reached by Day 31
- Sources: existing 277 + synthetic resume (auto +120/round) + distillation (in progress)
- If lag: increase distillation budget + run multiple teachers parallel

### H4: SimPO training under $7 on RunPod RTX 4090
- Test Day 33: 8-hr run on combined dataset
- Adapt fail: use spot pricing ($0.34/hr), longer wait acceptable

### H5: Identity preservation eval pass-rate ≥ 0.85 cosine sim
- Test Day 34: run new model on 20 fixed prompts, compare embeddings
- Adapt fail: rollback model, add more identity-anchor samples to dataset, retrain

### H6: migancore.com landing live + indexable
- Test Day 35: page live, OG tags valid, no 404
- Adapt fail: simple HTML on aaPanel, defer fancy interactions

---

## ⚠️ RISKS

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Catastrophic forgetting** during fine-tune (loses persona) | Medium | High | Identity-preserving anchor samples (50 prompts) MUST be in training set. Eval gate before promote. |
| **Training cost overrun** RunPod | Low | Medium | Hard cap $10 per run. Use spot RTX 4090 ($0.34/hr) not Secure Cloud. |
| **Distillation pipeline still flaky** | Medium | Medium | Adapt: switch teacher to Claude (more reliable than Kimi K2 thinking mode quirks) |
| **Spawn UI complexity blow time budget** | Low | Low | Cap at 1 day. Ship MVP modal even if styling rough. |
| **D3.js learning curve eats time** | Medium | Low | Use ready-made library (`react-force-graph`), not from scratch |
| **migancore.com nginx config conflict** | Low | Medium | Pattern proven (api/app subdomains). Apply same to root. |
| **Letta integration in spawn flaky** | Medium | Medium | Already wired Day 13. Verify still works during testing. Fallback: spawn without Letta. |
| **GGUF conversion / Ollama hot-swap fails** | Medium | High | Test conversion on small Phi-3 model first. Keep base model as fallback. |

---

## 💰 COST ANALYSIS

| Item | Estimate (Week 4) |
|------|-------------------|
| Distillation 200 more pairs (Kimi+Claude judge) | ~$2 |
| **First SimPO training run** RunPod RTX 4090 8hr | ~$5.50 |
| Eval inference (RunPod 1hr) | ~$0.70 |
| Misc API calls (testing) | ~$2 |
| **TOTAL Week 4 budget** | **< $11** |

**Saldo aman:** Anthropic $4.55, Kimi $2, OpenAI $5+, Gemini free, ElevenLabs $5, fal.ai $9.99 = **~$26 reserve**.

---

## 📅 DAY-BY-DAY EXECUTION PLAN

### Day 29 — "Spawn UI + Genealogy Foundation"
- AM: Audit + fix Day 28 distillation pipeline (Ollama timeout pattern)
- PM Phase A: Add "+ New Agent" + "Spawn Child" buttons to `chat.html`
  - Modal: name, parent (select), persona overrides (textarea YAML)
  - Wire to existing `POST /v1/agents/{id}/spawn`
- Commit + deploy

### Day 30 — "Genealogy Tree Visualization"
- AM: Backend endpoint `GET /v1/agents/genealogy` (full tree for current tenant)
- PM: Add "Lineage" tab to `/admin/`
  - Use `react-force-graph` library (CDN)
  - Color-coded nodes: core_brain (orange), gen 1 (green), gen 2+ (purple)
  - Click node → show agent details
- Commit + deploy

### Day 31 — "3 Mode Templates"
- AM: Create `config/personalities.yaml`
  - `customer_success`: voice/tone/anti-patterns
  - `research_companion`: cite sources, never fabricate refs
  - `code_pair`: terse, type-aware, suggest tests
- PM: Update spawn UI to include "Choose Template" dropdown
  - Loading template auto-fills persona_overrides
  - Test: spawn one of each, verify persona inherited correctly
- Document in `docs/MODE_TEMPLATES.md`

### Day 32 — "Trigger First SimPO Training (when data ready)"
- AM: Final data check — should hit ~500-700 pairs by now
  - Combined: synthetic resumed + distillation continued + CAI accumulating
- PM: SimPO training prep
  - Build training script: `training/train_simpo.py` (Unsloth+QLoRA recipe)
  - Identity-preserving anchor samples (50) added to dataset
  - RunPod pod template
  - **Trigger training run** (8hr expected)
- Monitor cost + progress

### Day 33 — "Migancore.com Landing Page + Eval Set"
- AM: Build `migancore.com` static landing
  - Hero: "Migancore — The AI that learns weekly"
  - 5-level evolution timeline (visual)
  - Live stats widget (public read-only `/v1/public/stats`)
  - CTA: "Try the chat" → app.migancore.com
  - Deploy to nginx aaPanel root
- PM: Build identity persistence eval
  - 20 fixed prompts (creative, Q&A, persona, tool-use mix)
  - Reference responses from baseline Qwen2.5-7B
  - Embedding similarity gate ≥ 0.85
  - Script: `eval/run_identity_eval.py`

### Day 34 — "Hot-swap + A/B Test Framework"
- AM: When SimPO done — convert adapter to GGUF
  - Pull from RunPod, convert to Q4_K_M
  - Run identity eval — gate check
  - If pass: load to Ollama as `migancore-7b-soul-v0.1`
- PM: A/B test framework
  - Header `X-Model-Version` to route 10% traffic to new
  - Monitor metrics in dashboard
  - 24h evaluation period

### Day 35 — "Polish + Document + Lock Bulan 2"
- Public Learn dashboard variant for `migancore.com/learn` (read-only)
- Update CHANGELOG, SPRINT_LOG, CONTEXT
- `docs/WEEK4_RETRO.md` — what worked, what didn't
- `docs/BULAN2_PLAN.md` — kickoff: 5 beta users dogfooding (per original timeline)
- Push everything to GitHub

---

## 🎁 BENEFITS — Why This Plan Wins (vs my previous "Creative Agent" plan)

### Aligned with Original Blueprint:
1. **Closes Level 5 (The Breeder) gap** — original feature signature ADO
2. **Triggers Cycle 1 Self-Improvement** — original Level 4 final lap
3. **Sets up `migancore.com` landing** — public-facing per original kickoff intent
4. **Mode templates** — exactly what kickoff specified (customer_success, research_companion, code_pair)
5. **Identity persistence eval** — original blueprint risk mitigation #3

### Strategic narrative:
- **"Migancore can BREED agents now, and is starting to LEARN from them"** — much stronger than "Migancore added Creative tool"
- **Lineage tree visualization** = sticky shareable visual (vs another chat UI)
- **First trained model** = real proof flywheel works (vs "we have a pipeline")

### Cost efficient:
- **< $11 total** — preserves $26 runway for Bulan 2 (5 beta users dogfooding)

### Honest to original timeline:
- Day 28 expected: spawn endpoint + Letta integration ← we have backend, ship UI
- Day 30 expected: demo + landing page ← align Day 35
- Bulan 2 expected: 5 beta dogfooding ← Week 5 transition

---

## 🛡️ ANTI-PATTERN COMPLIANCE

| Original blueprint warning | Mitigation |
|---------------------------|------------|
| "Self-evolving" ≠ AGI emergence in 30 days | Realistic: incremental sharpening + persona consolidation only |
| Letta not 100% production-ready | Already pinned version, fallback to non-Letta path documented |
| Multi-tenancy data leak | RLS active, `tenant_id` everywhere, tested Day 11+ |
| RunPod budget overrun | Hard cap $10/run, spot pricing, eval gate before commit |
| Catastrophic forgetting | Identity anchor samples + 0.85 cosine gate before promote |

---

## 🔄 ADAPTATION CHECKPOINTS

- **End Day 29**: Spawn UI working? If no → ship as backend-only, document curl pattern
- **End Day 31**: Mode templates verified? If issues → ship 1 template (customer_success), iterate
- **End Day 32**: 500+ pairs reached? If under → defer training to Day 34, fill gap with more distillation
- **End Day 33**: Eval set ready? If under → run with smaller (10 prompts) to unblock training
- **End Day 35**: All 6 PRIMARY shipped? If 5/6 → still ship, document the gap, plan Week 5 catch-up

---

## ❓ DECISIONS NEEDED FROM USER

1. **Approve revised plan?** Aligned with original blueprint 5-Level Evolution, defers 10-domain ADO ke Bulan 4+
2. **OK trigger first SimPO run di RunPod** Day 32-33 ($5.50 cost)?
3. **migancore.com root domain**: kasih landing page basic atau redirect ke app.migancore.com?
4. **Identity eval reference responses**: pakai response dari Qwen2.5-7B base sekarang sebagai "ground truth"?
5. **Bulan 2 dogfooding**: kamu siap invite 5 beta users (per kickoff timeline)?

---

## 📂 FILES TO CREATE/MODIFY (Week 4)

**New:**
- `frontend/dashboard.html` — extend with Lineage tab
- `frontend/spawn-modal.js` — embedded in chat.html (or separate)
- `config/personalities.yaml` — 3 mode templates
- `training/train_simpo.py` — RunPod-ready training script
- `eval/persona_consistency_v1.jsonl` — 20 fixed prompts
- `eval/run_identity_eval.py` — cosine similarity gate
- `frontend/migancore-landing.html` — root domain landing
- `docs/MODE_TEMPLATES.md`
- `docs/WEEK4_RETRO.md`
- `docs/BULAN2_PLAN.md`

**Modify:**
- `frontend/chat.html` — spawn modal + agent switcher
- `api/routers/agents.py` — `GET /v1/agents/genealogy` endpoint
- `api/routers/admin.py` — `GET /v1/admin/public-stats` (for landing widget)
- `api/main.py` — version bumps per day

---

## 🚀 IF I WERE FAHMI (revised, post-blueprint re-read)

Original blueprint sangat clear: **Migancore Core itself is the product**. SIDIX, MighanTech3D, Mighan = future consumers (Bulan 3+). My previous Creative Agent plan was anachronistic — that's Bulan 4+ stuff.

Week 4 closes the **Level 5 (The Breeder) visibility gap** — the ONE thing that makes Migancore visibly different from "another chat UI with tools." Spawning child agents with inherited persona + visible lineage tree = ADO signature feature.

Plus trigger Cycle 1 self-improvement — actually USE the data flywheel we built (Days 14-28). $5.50 RunPod is rounding error vs the narrative value of "Migancore v0.1 → trained on 500 user-validated pairs."

By Day 35: Migancore has **The Breeder UI**, **The Innovator triggered**, **migancore.com landing**, **3 mode templates**, **first trained model**, **identity eval**. That's the original 30-day plan ACTUALLY DELIVERED — not deviation.

Bulan 2 = 5 beta users dogfooding. Bulan 3 = open-source repo public. Bulan 4 = mighan.com marketplace foundation. Stay disciplined to original sequence.
