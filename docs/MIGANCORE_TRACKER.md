# MIGANCORE TRACKER — Living System State
<!-- Single Source of Truth. Updated by `scripts/tracker.py` and manually by Claude/Kimi/Codex. -->
<!-- Command: python scripts/tracker.py status | day-start N | day-end N | agent-sync TOPIC | backlog | lesson "TEXT" -->

---

## ⚡ QUICK STATUS
<!-- Section tag: QUICK_STATUS — auto-updated by tracker.py update -->
| Key | Value |
|-----|-------|
| **Today** | Day 71 · 2026-05-08 |
| **Production Brain** | `migancore:0.3` — Qwen2.5-7B LoRA, weighted_avg 0.9082, Cycle 3 ← STAYS |
| **Cycle 7 Result** | ❌ ROLLBACK — voice 0.721 (gate 0.85), weighted_avg 0.8814 (gate 0.92). Root cause: under-training 63 steps |
| **Cycle 7b Status** | 🟡 TRAINING LIVE — A40 $0.322/hr, LR=1.2e-6, epochs=3 (~95 steps) — est. completion 21:51-22:01 UTC |
| **Baseline Fix** | ✅ `eval/baseline_day70_voice_fixed.json` — Q5 casual ref fixed (Kimi P0 Day 71b) |
| **API Commit** | `26eba3a` (Day 71b: Kimi+Codex 71b reviews + RECAP committed) |
| **API Version** | v0.5.16 — BUILD_DAY=Day 70, commit_sha=2d87c7b ✅ |
| **API Health** | https://api.migancore.com/health |
| **Chat App** | https://app.migancore.com |
| **Beta Users** | 53 registered · 65 conversations · **0 feedback signals** ← P0 fix deployed Day 69 |
| **Total Pairs** | ~3,004 in DB (same as C7 — no new pairs for C7b retry) |
| **Current Phase** | **Phase A — Stabilization** (Day 68–80) |
| **Revenue** | $0 · First client target: Day 101–130 |
| **Compute Budget** | Vast.ai ~$6.15 remaining · VPS ~$11-12/mo |
| **Lessons Cumulative** | 171 (Day 71 adds #162-171) |

---

## 🎯 VISION ALIGNMENT MAP
<!-- Update this table after each major milestone or strategic decision. -->
<!-- Rating: ✅ LIVE · ⚠️ PARTIAL · ❌ MISSING · 🔬 R&D -->

### Prinsip Non-Negotiable (dari MIGANCORE-PROJECT-BRIEF.md)

| # | Prinsip | Status | Gap / Evidence |
|---|---------|--------|----------------|
| P1 | Otak sendiri belajar dari interaksi | ⚠️ PARTIAL | Training pipeline live, **tapi 0 real-user signal 16 hari beta**. Flywheel mati di source. Fix: P0 feedback UI + Hafidz Ledger. |
| P2 | White-label, per-org clone | ⚠️ PARTIAL | clone_manager.py dry-run ✅. **Real deploy ke client VPS = BELUM**. Per-org Docker template belum live. |
| P3 | Self-hosted, zero data leak | ✅ LIVE | VPS 72.62.125.6, semua data lokal, SSL, gitignore clean. |
| P4 | License system (BERLIAN/EMAS/PERAK/PERUNGGU) | ✅ LIVE | HMAC-SHA256 Day 62. Ed25519 upgrade defer Phase D (air-gapped). |
| P5 | Trilingual (ID primary, EN secondary, ZH tertiary) | ⚠️ PARTIAL | ID ✅ (dominant), EN ✅ (functional), **ZH = 0 pairs**. Defer 2027. |
| P6 | Genealogy (parent→child ADO tracking) | ✅ LIVE | license.json + genealogy field + KB knowledge_return. |
| P7 | Multimodal (vision, voice, image gen) | ✅ LIVE | Gemini vision, Scribe STT, fal.ai image gen, TTS, PDF/PPTX export. |
| P8 | MCP ecosystem (tools, integrations) | ✅ LIVE | 23 tools, MCP server api.migancore.com/mcp/, Smithery public. |
| P9 | First paid client (Rp 5jt+/bln) | ❌ MISSING | Clone real deploy: BELUM. Client pipeline: BELUM. |

### Northstar Progress

| Milestone | Target | Actual | Delta |
|-----------|--------|--------|-------|
| Day 30: agent bisa interact, ingat, pakai tools, lahirkan child | Day 30 | Day 35 (~) | +5 days |
| Bulan 3: system perbaiki diri tanpa human weekly | Day 90 | 🔬 PENDING | Flywheel broken |
| Bulan 6: agent hidup, ingat semua, punya "cucu" | Day 180 | - | - |
| Bulan 12: agent punya "karakter" unik dari Core | Day 365 | - | - |
| Q2 2026: 5 beta users | Day 90 | 53 users ✅ | Engaged? 0 signals |

---

## 🗺️ ACTIVE ROADMAP
<!-- 4 Phases dari ROADMAP_DAY67_MASTER.md. Update status setelah milestone selesai. -->

### PHASE A — STABILIZATION (Day 68–80)
**Theme:** Fix broken flywheel before adding new spokes.

| ID | Task | Priority | Status | Owner | ETA |
|----|------|----------|--------|-------|-----|
| A-01 | Cycle 6 outcome: ROLLBACK — migancore:0.3 stays production | P0 | ✅ DONE | Claude | Day 69 |
| A-02 | Feedback UI live + wired to API (thumbs 👍👎 signals stored) | P0 | ⚠️ PARTIAL | Claude | Day 69–70 |
| A-03 | Admin key stored in password manager (Fahmi action) | P0 | ❌ PENDING | **Fahmi** | ASAP |
| A-04 | Hafidz Ledger Phase A (table + endpoint + genealogy) | P0 | ❌ PENDING | Claude | Day 70–74 |
| A-05 | Letta chat router wiring (verify or wire) | P1 | ❌ PENDING | Claude | Day 72–75 |
| A-06 | KB auto-update cron (script exists, not cron'd) | P1 | ❌ PENDING | Claude | Day 78–79 |
| A-07 | Sleep-time consolidator (memory_pruner → Letta pattern) | P1 | ❌ PENDING | Claude | Day 79–80 |
| A-08 | KG auto-extract (kg_entities currently 0) | P1 | ❌ PENDING | Claude | Day 75–78 |
| A-09 | Codex C5: OpenAPI schema (admin/license routes open) | P2 | ❌ PENDING | Claude | Day 70 |
| A-10 | Codex C6: Admin key in localStorage (XSS risk) | P2 | ❌ PENDING | Claude | Day 70 |
| A-11 | Codex C7: /v1/speech/to-text open (cost-bearing endpoint) | P2 | ❌ PENDING | Claude | Day 70 |
| A-12 | BUILD_DAY env update | P3 | ✅ DONE Day 70 | Claude | Day 70 |

**Phase A Exit Gate:** Feedback signals ≥10 in 7 days post-fix + Hafidz endpoint live + Cycle 6 resolved.

---

### PHASE B — FEEDBACK FLYWHEEL (Day 81–100)
**Theme:** Real signal in, real model out. Cycle 7 from user data.

| ID | Task | Priority | Status |
|----|------|----------|--------|
| B-01 | SIDIX bridge: 1,458 pairs audit + bridge pipeline | P0 | ❌ PENDING |
| B-02 | Cycle 7 dataset: ≥50 real signals + SIDIX bridge → training | P0 | ❌ PENDING |
| B-03 | A2A AgentCard: `/.well-known/agent.json` | P1 | ❌ PENDING |
| B-04 | Reasoning traces collection (Qdrant `reasoning_traces`) | P1 | ❌ PENDING |
| B-05 | UMKM vertical KB: `kb_umkm_warung.md` | P1 | ❌ PENDING |
| B-06 | Startup legalitas vertical KB: `kb_legalitas_startup.md` | P2 | ❌ PENDING |
| B-07 | Qwen3-8B upgrade (trigger: Cycle 6 PROMOTE) | P2 | 🔬 CONDITIONAL |

**Phase B Exit Gate:** Cycle 7 PROMOTE dari ≥50 real signals + A2A card live + SIDIX bridge extracting.

---

### PHASE C — FIRST CLIENT (Day 101–130)
| ID | Task |
|----|------|
| C-01 | Clone real deploy ke 1 client VPS (UMKM warm intro via Fahmi) |
| C-02 | Tokopedia Seller API connector (MCP tool) |
| C-03 | WhatsApp Business API connector |
| C-04 | License system: EMAS tier onboarding flow |
| C-05 | Target: Rp 5jt/bln × 1 client = first revenue |

---

### PHASE D — SCALE (Day 131–180)
| ID | Task |
|----|------|
| D-01 | Verifier-driven RL (Qwen3-0.6B reward head from 450+ CAI labels) |
| D-02 | x402 + ERC-8004 per-inference billing |
| D-03 | Open-source core components |
| D-04 | Ed25519 asymmetric license (air-gapped BERLIAN tier) |
| D-05 | Multi-language: Bahasa Jawa Ngoko/Krama (95M speaker UMKM pivot) |

---

## 📋 BACKLOG (Prioritized)
<!-- Keep sorted P0→P3. Update when items move to roadmap or done. -->

### P0 — Must Fix Now
- [x] **Cycle 6 ROLLBACK** — Done. migancore:0.3 stays. Root cause documented → Cycle 7 plan locked.
- [ ] **Cycle 7 dataset** — 260 pairs voice-first. 20/260 stored (honesty). Full generation running Day 70. → Vast.ai → eval.
- [x] **Fix eval script threshold** — `run_identity_eval.py` 0.8 → 0.92. Retry expansion (Lesson #156). DEPLOYED commit `4cfdd4e`.
- [x] **Feedback race condition + fbSent lock** — P0 Kimi bugs FIXED + DEPLOYED. Persist before SSE done. fbSent unlocks on error. Gate: 1st real signal in <72h.
- [ ] **Admin key in password manager** — Fahmi action, cannot be delegated.
- [ ] **Hafidz Ledger Phase A** — hafidz_contributions table + POST endpoint + genealogy link.

### P1 — Should Ship Phase A
- [ ] **Letta wiring** — is letta.py called from chat router? Check + wire.
- [ ] **KG entities populate** — kg_entities = 0. Run fact_extractor post-chat.
- [ ] **KB weekly cron** — kb_auto_update.py exists, cron not installed.
- [ ] **Sleep-time consolidator** — episodic → semantic nightly at 03:00 WIB.
- [ ] **Codex C5/C6/C7** — OpenAPI, localStorage XSS, STT auth.
- [x] **BUILD_DAY env** — Day 70 live in docker-compose + /health. ✅

### P2 — Nice to Have
- [ ] **SIDIX 1,458 pair audit** — bridge to training pipeline Phase B.
- [ ] **migancore:0.1, 0.4, 0.5 ollama rm** — reclaim ~14GB RAM/disk.
- [ ] **A2A AgentCard** — `/.well-known/agent.json` 1-day effort, high insurance.
- [ ] **Reasoning traces Qdrant collection** — pipe `<think>` traces from Qwen3.

### P3 — Defer
- [ ] **ZH (Mandarin) pairs** — defer 2027.
- [ ] **Speculative decoding (llama-server)** — KPI miss on shared host.
- [ ] **Active Inference (pymdp)** — 5-year moat, defer Phase D.
- [ ] **Causal AI (DoWhy + EconML)** — same, Phase D.

---

## 📅 DAILY LOG
<!-- Append new entry with: python scripts/tracker.py day-end N -->

### Day 71 — 2026-05-08 (IN PROGRESS)
**Status:** IN PROGRESS — Cycle 7b training LIVE, post-pipeline pending

**Delivered:**
- [x] **Mandatory protocol** — git status, 5-layer alignment, health check
- [x] **Vision elaboration** — DAY71_PLAN.md: Cognitive Kernel paradigm, BaaS architecture, Sprint roadmap D71-150
- [x] **Cycle 7 training** — 10.1 min, $0.054, Instance 36311511 DELETED ✅ (migancore:0.7 registered but ROLLBACK)
- [x] **Cycle 7 ROLLBACK documented** — voice 0.721 (gap -0.129), weighted_avg 0.8814 (gap -0.038). Root cause: 63 steps = under-training
- [x] **cycle7b_orpo_vast.py** — LR=1.2e-6 (2x), epochs=3 (+1). Committed c83371c
- [x] **Cycle 7b training LIVE** — Instance 36314593, A40, 21:29 UTC launch
- [x] **Agent sync complete** — CLAUDE_PLAN/KIMI_REVIEW/CODEX_QA/RECAP all committed
- [x] **Q5 baseline fix** — `eval/baseline_day70_voice_fixed.json` created (Kimi P0 action). Casual reference re-embedded.
- [x] **CLAUDE_PLAN_71B + KIMI_REVIEW_71B + CODEX_QA_71B + RECAP_71B** — committed 26eba3a
- [ ] Cycle 7b training complete + GGUF + Ollama register
- [ ] Eval with voice-fixed baseline + PROMOTE/ROLLBACK decision
- [ ] Formal register smoke test (Codex F3)
- [ ] Lesson #170-171 locked to tracker

**Lessons:**
- #162: Modelfile for each cycle must be created BEFORE training trigger, not after (Codex B1)
- #163: Eval command needs explicit `--model <tag>`, not just `--model-tag` (Codex B2)
- #164: Multi-teacher quorum (vote 2/3) bad for ORPO — flat margin. Use specialist per category
- #165: 47% fewer gradient steps + same LR = under-training risk. Scale LR × epochs with dataset
- #166: Cycle 7 ROLLBACK: cleaner data alone insufficient if steps too few. Voice needs gradient volume.
- #167: Q5 "Hai! Bagaimana kabarmu?" = hardest voice gate (0.478). Casual Indonesian greeting hard to transfer via ORPO.
- #168: Tool-use via ORPO = wrong tool. ORPO = preference learning. Tool trigger = format conditioning → few-shot SOUL.md.
- #169: weighted_avg can drop even if content better if training intensity insufficient.
- #170: Eval baseline reference must MATCH training target. Formal baseline punishes correctly casual model.
- #171: Steps > pair count for ORPO voice absorption. C5: 80 pairs/119 steps → +0.155; C7: 120 pairs/63 steps → +0.016.

**Costs:** Cycle 7 = $0.054 · Cycle 7b = ~$0.06 (in progress) · Day 71 total ≈ $0.11

---

### Day 70 — 2026-05-08 (IN PROGRESS)
**Status:** IN PROGRESS

**Delivered:**
- [x] **Docs committed + VPS synced** — CLAUDE_PLAN_70, KIMI_REVIEW_70, CODEX_QA_69, KIMI_REVIEW_69 committed (3a2f83d). VPS HEAD aligned.
- [x] **BUILD_DAY=Day 70** — docker-compose.yml updated, API restarted. `/health` returns `"day":"Day 70"` ✅
- [x] **Cycle 7 dataset generator** — `training/generate_cycle7_dataset.py` 260 pairs (80 voice-casual, 40 voice-style, 50 tool-write, 30 tool-image, 40 creative, 20 honesty). Zero domain pairs.
- [x] **Cycle 7 export** — `training/export_cycle7_dataset.py` with correct INCLUDE/EXCLUDE filters.
- [x] **Schema audit** — preference_pairs has NO category/is_validated/quality_score. Scripts fixed to use judge_score + ON CONFLICT DO NOTHING. Commit 1b58d57.
- [x] **Gemini model fix** — gemini-2.0-flash deprecated (404). Updated to gemini-2.5-flash. Commit d5d0d31.
- [x] **honesty 20/20 pairs** — smoke test pass. DB insert pipeline verified end-to-end.
- [ ] **Full generation 240 pairs running** — nohup on VPS /tmp/cycle7_full.log
- [ ] Cycle 7 export JSONL
- [ ] Letta audit findings documented
- [ ] Codex C5/C6/C7
- [ ] Admin key in password manager (Fahmi)
- [ ] Hafidz Ledger Phase A

**Lessons:**
- #158: `gemini-2.0-flash` deprecated → 404. Always use `gemini-2.5-flash`. Check model name each new cycle script.
- #159: preference_pairs schema ≠ what scripts assumed. Real columns: id, prompt, chosen, rejected, judge_score, judge_model, source_method, source_message_id, created_at, used_in_training_run_id. No category/quality_score/is_validated. Always verify schema before writing insert scripts.

**Costs:** $0

---

### Day 69 — 2026-05-08 ✅ COMPLETE

**Delivered:**
- [x] MIGANCORE_TRACKER.md created (this file) — living single source of truth
- [x] scripts/tracker.py CLI — status, day-start, day-end, agent-sync, lesson, align, update
- [x] scripts/watch_agent_sync.py — file-based ping watcher
- [x] docs/AGENT_SYNC/BRIEF_UNTUK_KIMI.md + BRIEF_UNTUK_CODEX.md — agent onboarding
- [x] docs/AGENT_SYNC/CLAUDE_PLAN_69_CYCLE6_AND_FEEDBACK.md
- [x] **Cycle 6 eval COMPLETE → ROLLBACK** — weighted_avg 0.8661, voice 0.705, tool-use 0.733
- [x] **Kimi P0 bugs FIXED + DEPLOYED** — race condition + fbSent lock. Commit `4cfdd4e`.
- [x] **Eval retry expansion** — timeout+connect errors retried.
- [x] **CYCLE7_DATASET_PLAN.md** — 260 pairs, voice-first strategy.

**Lessons:** #153–157 (tracker, file-sync, eval threshold, SSE race condition, fbSent lock)
**Costs:** $0

---

### Day 68 — 2026-05-08 (COMPLETE)
**Status:** ✅ COMPLETE — All 5 layers aligned, 9 commits, 4.4GB freed, 35-40s → 1-4s response fix

**Delivered:**
- [x] Block 1: Server hygiene (174 → 0 untracked, .gitignore, 4.5GB archived)
- [x] Block 2: Conversation history E2E (API-backed, sidebar click loads conv)
- [x] Block 3: Mobile nav drawer (hamburger ☰, slide-in, overlay)
- [x] Block 4: Dynamic build metadata at /health (commit_sha, build_time, day)
- [x] Block 5: Favicon SVG + ICO (0 nginx errors)
- [x] Security: Admin key ROTATED (exposed Day 22–68). USER_GUIDE.md redacted (5x).
- [x] Cycle 6 training: 118/118 steps, train_loss 2.4438, adapter 161MB (post_cycle6.sh triggered)
- [x] Seamless audit: ALL 5 LAYERS ALIGNED at commit `990458a`

**Lessons:** #147–152 (cancelled≠deploy-kill, user base audit, build SHA env, PowerShell heredoc, recovery script conditional bug, admin key exposure)

**Costs:** $0 (Vast.ai terminated $0 billing)

---

### Day 67 — 2026-05-07 (COMPLETE)
**Status:** ✅ COMPLETE

**Delivered:**
- [x] Performance fix: 35-40s → 1-4s (stopped synth gen, Ollama 4→6 cores, llamaserver removed)
- [x] VPS cleanup: 9 PM2 stopped, 4 nginx vhosts disabled, ~4GB freed
- [x] ROADMAP_DAY67_MASTER.md (4072 words, 4 phases, 5 risks, 8 trends)
- [x] DAY68_SPRINT_PLAN.md (Codex C1-C8 mapped, deploy checklist)
- [x] Cycle 6 training triggered (954 pairs, Vast.ai, RTX 8000)

**Lessons:** #144–146 (thumbs_up 200 no DB write, hardcoded version drift, cancelled≠deploy-kill)

---

## 🤖 MULTI-AGENT PROTOCOL
<!-- How Claude, Kimi, and Codex coordinate. -->

### Overview

```
CLAUDE (implementator + recap)
  → writes: docs/AGENT_SYNC/CLAUDE_PLAN_{DAY}_{TOPIC}.md
  
KIMI (researcher + reviewer, runs in VS Code)
  → reads: CLAUDE_PLAN
  → writes: docs/AGENT_SYNC/KIMI_REVIEW_{DAY}_{TOPIC}.md
  
CODEX (QA + security analysis)
  → reads: CLAUDE_PLAN + KIMI_REVIEW
  → writes: docs/AGENT_SYNC/CODEX_QA_{DAY}_{TOPIC}.md
  
CLAUDE (final)
  → reads: KIMI_REVIEW + CODEX_QA
  → writes: docs/AGENT_SYNC/RECAP_{DAY}_{TOPIC}.md
  → updates: MIGANCORE_TRACKER.md (day log, backlog status, lessons)
```

### Trigger Command
```bash
# Claude generates plan file, prints path for Kimi to open
python scripts/tracker.py agent-sync "TOPIC" --day 69

# Kimi opens in VS Code: code docs/AGENT_SYNC/CLAUDE_PLAN_69_TOPIC.md
# Kimi writes response to: docs/AGENT_SYNC/KIMI_REVIEW_69_TOPIC.md

# Claude reads Kimi review + decides
python scripts/tracker.py agent-read kimi --day 69 --topic TOPIC

# Claude outputs recap
python scripts/tracker.py agent-recap --day 69 --topic TOPIC
```

### Plan Template (Claude → Kimi)
Every `CLAUDE_PLAN_*.md` must include:

```markdown
## CONTEXT
[Current state: commit SHA, brain version, key metrics]

## HYPOTHESIS  
[What we think will work, and why]

## EXECUTION PLAN
[Step-by-step with rollback for each step]

## RISK / BENEFIT / IMPACT
| Dimension | Assessment |
| Risk | ... |
| Benefit | ... |
| Impact | ... |
| Reversibility | ... |

## RESEARCH QUESTIONS FOR KIMI
[3-5 specific questions for Kimi to research or analyze]

## DECISION GATE
[What must be true for Claude to proceed. GO if: ... / NO-GO if: ...]
```

### Review Template (Kimi → Claude)
Every `KIMI_REVIEW_*.md` must include:

```markdown
## VERDICT: GO / NO-GO / CONDITIONAL

## RESEARCH FINDINGS
[Answers to Claude's questions, with sources]

## ANALYSIS
[Kimi's independent analysis of Claude's plan]

## RISKS MISSED BY CLAUDE
[Anything Claude didn't consider]

## RECOMMENDATION
[If conditional: specific changes before GO]
```

### QA Template (Codex → Claude + Kimi)
Every `CODEX_QA_*.md` must include:

```markdown
## SECURITY FINDINGS
[Severity: P1/P2/P3 + specific file:line]

## LOGIC BUGS
[Any obvious flaws in execution plan or code]

## MISSING TESTS
[What should be tested before ship]

## SIGN-OFF: YES / CONDITIONAL / NO
```

---

## 📚 LESSON REGISTRY
<!-- Append new lessons with: python scripts/tracker.py lesson "TEXT" -->
<!-- Format: #NUM · DAY · CATEGORY · Lesson text -->

### Recent Lessons (Day 67–71)

| # | Day | Category | Lesson |
|---|-----|----------|--------|
| 171 | 71 | Training | Steps > pair count for ORPO voice absorption. C5: 80 pairs/119 steps → +0.155 voice; C7: 120 pairs/63 steps → +0.016. Effective optimization = LR × steps, not pair count alone. |
| 170 | 71 | Training | Eval baseline reference must MATCH training target. Formal baseline embedding punishes correctly casual model even if training succeeded. Fix: create versioned voice-fixed baseline before eval. |
| 169 | 71 | Training | weighted_avg can drop even if content quality improves, if training intensity (LR × epochs) insufficient. LR + epochs must scale proportionally with dataset size. |
| 168 | 71 | Architecture | Tool-use via ORPO = wrong tool. ORPO = preference learning. Tool trigger conditioning = format conditioning. Solution: few-shot examples in SOUL.md, NOT more training pairs. |
| 167 | 71 | Training | Q5 "Hai! Bagaimana kabarmu?" is hardest voice gate (scored 0.478 in C7). Casual Indonesian greeting extremely hard to transfer via ORPO in few steps. Pairs must be extremely casual to shift model from formal default. |
| 166 | 71 | Training | Cycle 7 ROLLBACK: cleaner data alone insufficient if gradient steps too few. Voice absorption needs gradient volume (steps), not just pair quality. |
| 165 | 71 | Training | 47% fewer gradient steps with same LR = under-training risk. Always prepare Cycle N+1 contingency (LR 2x) before GO when step count drops vs previous cycle. |
| 164 | 71 | Training | Multi-teacher quorum (vote 2/3) bad for ORPO — produces flat preference margin → flat loss. Use specialist per category: Kimi=voice, GPT=tool, Gemini=general/identity. |
| 163 | 71 | QA | Eval command needs explicit `--model <tag>`, not just `--model-tag`. Ambiguous model arg can cause silent default model usage. |
| 162 | 71 | Workflow | Modelfile for each cycle must be created BEFORE training trigger, not after. Missing Modelfile = post-training pipeline blocked (Codex B1 pattern). |
| 157 | 69 | Frontend | fbSent permanent lock on API error = user can never retry feedback. Always rollback UI state (fbSent=false, fbState=null) in catch. Silent swallowed errors = silent broken features. |
| 156 | 69 | Architecture | `asyncio.create_task(_persist)` AFTER `yield done` = race condition. Fast user clicks feedback before DB write completes → 404 for 16 days, 0 signals. Always `await _persist` BEFORE yielding SSE done. |
| 155 | 69 | Training | Eval threshold 0.80 ≠ real gate 0.92 — THIRD TIME (also Lessons #140, #144). Fix the source: hardcode real gates in eval script with permanent comment. |
| 154 | 69 | Workflow | Multi-agent sync via files beats real-time protocol. Async drop-and-pick pattern — each agent works when active, leaves artifact. |
| 153 | 69 | Workflow | Tracker must live alongside code — agents read context as files, not narrative. `docs/AGENT_SYNC/` as file-based message bus. |
| 152 | 68 | Infrastructure | Recovery scripts with `ls` multi-line output: `== "READY"` comparison fails. Always grep-filter: `ls ... | grep -c "READY"`. |
| 151 | 68 | Security | Admin key exposed since Day 22 in repo history. Lesson: ANY secret in a committed doc file = permanently exposed. Even after redact, git history retains it. Private vault is non-negotiable from Day 1. |
| 150 | 68 | Tooling | PowerShell heredoc `@'..'@` chokes on `()`, `:`, `$` in body. Workaround: write to `.commit_msg.tmp` → `git commit -F`. |
| 149 | 68 | Infrastructure | Build metadata pattern: `BUILD_COMMIT_SHA` env var at `docker compose up` time. Git not in container. Env var = fallback at module import. Reusable for all future deploys. |
| 148 | 68 | Product | "53 users" stat is dust without `last_active_at` audit. Real active users: 3 external (16 days beta). 0 feedback = not UI broken alone, user base too thin. |
| 147 | 68 | Architecture | `cancelled` status (admin /stop) ≠ deploy-kill. Only `{running, error, starting}` should auto-resume on container restart. `cancelled` = explicit user intent. |
| 146 | 67 | Infrastructure | Hardcoded version strings create invisible drift. Dynamic from /health endpoint = single source of truth. |
| 145 | 67 | QA | thumbs_up returned 200 but no DB write. Always verify with SELECT after first use, not just HTTP status. |
| 144 | 67 | Training | Eval script threshold `0.80` ≠ actual gate `0.92` = silent mismatch. Always validate gate threshold source (not eval default). Lesson #140. |
| 143 | 67 | Training | Rollback models waste RAM. `ollama rm migancore:0.1 migancore:0.4 migancore:0.5` = free ~14GB after Cycle 6 resolved. |
| 142 | 67 | Architecture | llamaserver `unless-stopped` policy = restart after every reboot without docker compose. Use docker compose for all services, not standalone docker run. |
| 141 | 67 | Performance | Synthetic gen pipeline + Ollama = CPU contention → 35-40s response. Stop synth gen during peak user hours. Consider time-gated cron (03:00-06:00 WIB). |

### Earlier Lessons Index
- #131–140: Day 65–66 (voice seed dedup, scp adapter dir, Ollama cores, SSE message_id, frontend serverId, gate threshold)
- #119–130: Day 61–64 (license crypto, Gemini thinking truncation, voice gate dominates, targeted pairs work)
- #110–118: Day 59–60 (Qwen bos_token_id, GGUF LoRA, ORPO apo_zero, Cycle 3 voice improvement)
- #83–109: Day 55–58 (eval recalibration, GGUF pipeline, identity anchor, cycle methodology)
- #65–82: Day 50–54 (Cycle 1 attempts, Vast.ai vs RunPod, local GPU infeasible)
- #54–64: Day 49 (pod boot timeout, cost telemetry, auto-abort, Vast.ai setup)
- #1–53: Day 1–48 (foundational: contracts.py, JWT refresh, tool cache, ONAMIX, memory pruner, etc.)

Full lesson text in `AGENT_ONBOARDING.md` (canonical) and `LESSONS_LEARNED.md`.

---

## 🔬 RESEARCH AGENDA
<!-- Questions that need deep research before execution. -->

### Active Research Questions
| # | Question | Assigned | Due |
|---|----------|----------|-----|
| R-01 | Letta 0.6 integration pattern: is `letta.py` in chat router? How to wire cross-session memory? | Claude (audit) | Day 69 |
| R-02 | Hafidz Ledger design: what schema + endpoints enable full ADO knowledge-return flow? | Claude (design) | Day 70 |
| R-03 | Cycle 6 eval outcome: which categories pass/fail? Root cause if ROLLBACK? | Claude (eval) | Day 69 |
| R-04 | SIDIX bridge: 1,458 pairs format, teacher API compatibility, estimated Cycle 7 boost? | Kimi (research) | Day 81 |
| R-05 | A2A AgentCard spec (Google A2A): minimal implementation for ADO? | Kimi (research) | Day 85 |

### Closed Research Questions
| # | Question | Answer | Day |
|---|----------|--------|-----|
| R-C01 | RunPod vs Vast.ai for training | Vast.ai 5-9x cheaper ($0.25/cycle vs $2.50 RunPod waste) | Day 49.7 |
| R-C02 | Speculative decoding (llama-server) on shared 8-vCPU | KPI MISS: 2.63 tok/s vs Ollama's better on shared host | Day 53 |
| R-C03 | Qwen2.5 vs Qwen3 for identity training | Lock Qwen2.5 until Cycle 5+. Qwen3 after first PROMOTE | Day 64 |
| R-C04 | Active Inference feasibility (pymdp) | Long-term moat, defer Phase D (requires signal dataset maturity) | Day 67 |

---

## 📊 METRICS DASHBOARD
<!-- Update weekly or after each cycle. -->

### Training Metrics
| Cycle | Pairs | weighted_avg | Voice | Identity | Outcome |
|-------|-------|-------------|-------|----------|---------|
| Cycle 1 | 596 | 0.6697 | 0.715 | N/A | ROLLBACK (DPO overwrote identity) |
| Cycle 2 | 613 | 0.8744 | N/A | 0.947 | PROMOTE → migancore:0.2 |
| Cycle 3 | 685 | 0.9082 | 0.817 | 0.953 | PROMOTE → migancore:0.3 ✅ PRODUCTION |
| Cycle 4 | 723 | 0.8910 | 0.739 | 0.963 | ROLLBACK (voice drift) |
| Cycle 5 | 877 | 0.8453 | 0.8946 | 0.9376 | ROLLBACK (3 Ollama 500 errors) |
| Cycle 6 | 954 | 0.8661 | 0.705 | 0.9334 | ROLLBACK (voice 0.705↓, tool-use 0.733, creative 0.771) |
| Cycle 7 | 508 | 0.8814 | 0.721 | 0.939 | ROLLBACK (under-training 63 steps, voice gap 0.721<0.85) |
| Cycle 7b | 508 (retry) | TBD | TBD | TBD | 🟡 TRAINING LIVE — LR=1.2e-6, 3 epochs, ~95 steps |

**Gate thresholds:** weighted_avg ≥ 0.92 · voice ≥ 0.85 · identity ≥ 0.90 · evo-aware ≥ 0.80 · tool-use ≥ 0.85 · creative ≥ 0.80

### System Performance
| Metric | Day 36 baseline | Day 67 | Day 68 | Target |
|--------|----------------|--------|--------|--------|
| Response (cold) | ~60s | 35-40s | 3-5s | <5s |
| Response (warm) | ~20s | 35-40s | 1-4s | <2s |
| SSE first token | timeout | ~5s | ~1-2s | <1s |
| Feedback signals | 0 | 0 | 0 | ≥10 (Day 75) |

### Cost Tracking
| Item | Budget | Spent | Remaining |
|------|--------|-------|-----------|
| Monthly VPS | $30/mo | ~$11-12 | ~$18 |
| Vast.ai credit | $7 | ~$0.80 | ~$6.20 |
| RunPod | $7 cap | $6.80 | $0.20 |
| Total compute | - | ~$8.80 | - |

---

## 🔐 SECURITY CHECKLIST
<!-- Verify before every deploy. -->

- [x] **Admin key NOT in repo** — rotated Day 68. `/opt/ado/.env` + `/root/.migancore_admin_key` only.
- [ ] **Admin key in Fahmi's password manager** — Fahmi action required.
- [x] **SSH credentials not in docs/** — pattern: `ssh -i <path> root@<ip>` generic only.
- [x] **VPS IP not in public docs** — redacted, private vault.
- [x] **.env gitignored** — verified Day 68.
- [ ] **Codex C5**: Admin/license routes in OpenAPI (should be hidden) — Day 70.
- [ ] **Codex C6**: Admin key in localStorage (XSS vector) — Day 70.
- [ ] **Codex C7**: `/v1/speech/to-text` unauthenticated (cost-bearing) — Day 70.

---

## 📐 DEPLOY CHECKLIST
<!-- Run before every deploy. From DAY68_SEAMLESS_AUDIT.md §G. -->

```bash
# 1. Pre-deploy
git status -sb                          # local clean
git diff --stat HEAD                    # review changes

# 2. Commit (Windows)
git add <specific files>
cat > .commit_msg.tmp << 'EOF'
Day N: change summary

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
git commit -F .commit_msg.tmp && rm .commit_msg.tmp

# 3. Push
git push origin main

# 4. Deploy to VPS
ssh -i <key> root@<vps-ip> "cd /opt/ado && git pull"
# If Python changes:
ssh ... "cd /opt/ado && BUILD_COMMIT_SHA=\$(git rev-parse --short HEAD) docker compose build api"
ssh ... "cd /opt/ado && BUILD_COMMIT_SHA=\$(git rev-parse --short HEAD) docker compose up -d api"

# 5. Smoke test
curl https://api.migancore.com/health   # commit_sha matches HEAD?
curl https://api.migancore.com/ready    # all downstream OK?
curl -I https://app.migancore.com/      # frontend 200?
# 1 chat call, target ≤4s warm

# 6. Rollback ready
# git reset --hard <prev_commit> && BUILD_COMMIT_SHA=<prev> docker compose up -d api
```

---

*MIGANCORE_TRACKER.md — owned by Claude (implementator), reviewed by Kimi, QA'd by Codex.*  
*Update protocol: `python scripts/tracker.py update` for Quick Status; manual for Vision Map and Roadmap.*  
*Last updated: Day 69 · 2026-05-08*
