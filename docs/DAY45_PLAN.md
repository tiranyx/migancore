# Day 45 Plan — Defensive Deploy + Conv Summarization + Sleep-time Foundation
**Date:** 2026-05-05 (Day 45, Bulan 2 Week 6 Day 5)
**Drafted by:** Claude Sonnet 4.6 — full mandatory protocol
**Triggered by:** User: "Bisa lanjut? Sudah QA, review, testing semua?... Apa yang bikin proyek ini beda dengan ADO lain?"
**Research:** 2 parallel agents (cognitive trends 2026-2027 + competitive distinctiveness)
**Strategic anchor:** `docs/VISION_DISTINCTIVENESS_2026.md` (NEW — read this first)

---

## 🧭 1. CONTEXT (Day 45 morning — QA findings)

| Item | State |
|------|-------|
| API | v0.5.13 healthy ✅ |
| ONAMIX MCP singleton | ✅ LIVE (8x speedup, lifespan log confirmed) |
| Tool cache | ✅ LIVE (1400x HIT speedup) |
| JWT silent refresh | ✅ LIVE (60min TTL) |
| **Synthetic gen** | ⚠️ **WAS STALLED** (Day 44 deploy killed it) → restarted run_id `fd3acdd8` |
| DPO pool | **450/500** (need 50 more, ETA tonight after restart) |
| Cycle 1 trigger | NOT YET — autonomous when ≥500 |
| Bulan 2 spend | $1.39 of $30 (4.6%) |
| Tools live | 23 |
| Lessons | 44 cumulative (will hit 47 today) |

---

## 🚨 2. CRITICAL QA FINDING + LESSON #45

**Bug:** Day 44 retro deploy `docker compose up -d --build api` recreated container = killed in-process synthetic gen task. DPO stuck at 450 for ~14h overnight.
**Why it slipped:** Synthetic gen runs as `asyncio.create_task` in main process — has no persistence across container restarts. Background tasks die silently with the container.
**Fix Day 45:** (a) restart synthetic gen NOW (✅ done — `fd3acdd8`), (b) add `_AUTO_RESUME_ON_STARTUP` flag in lifespan to detect last incomplete run and auto-resume, (c) document deploy checklist: "before `up -d --build api`, check synthetic state; after, verify resume."

**Lesson 45:** *In-process background tasks die with the container. EVERY async task that should outlive a deploy needs (a) state persistence, (b) auto-resume logic in lifespan, (c) deploy-checklist entry.*

---

## 🔬 3. RESEARCH SYNTHESIS (2 agents, cognitive forecast + distinctiveness)

**Distinctive moat (May 2026, defensible 18+ months):**
1. Closed identity-evolution loop (CAI quorum + SimPO + SOUL.md + genealogy) — NO competitor
2. Modality-as-tool routing via MCP (12-month moat — Letta/mem0 lack it)
3. Hardware floor commitment (32GB CPU forever — Anthropic/OpenAI structurally can't match)

**STOP building:** more wrapper tools, custom UI polish, generic memory features (commoditized by Cline/Open WebUI/mem0).

**DOUBLE DOWN:** Genealogy Protocol v0.1 spec, hot-swap public eval demo, cross-vendor CAI as pip library.

**5 cognitive trends (next 12-18mo):**
1. Test-time reasoning default (Qwen3-Thinking) — 30-60d window
2. Sleep-time memory consolidation (Letta v0.5) — **NOW window**
3. A2A protocol layer above MCP (Google Apr 2025) — 90-180d
4. On-device MoE Qwen3-30B-A3B — 30-60d benchmark
5. Verifier-driven RL (Tülu 3) — 90-180d

**Bold move (Day 50+):** "Dream cycle" — adversarial self-critique during sleep-time generates counterfactual episodes; CAI verifier scores them; SimPO trains on synthetic experience the model never lived. **Closed nightly loop.** No public 2026 ADO does this. We have ALL components — only missing one cron job.

Full doc: `docs/VISION_DISTINCTIVENESS_2026.md`.

---

## 📐 4. DAY 45 TASK LIST — H/R/B FRAMEWORK

### A1 — Defensive Deploy: synthetic gen auto-resume on startup ⭐ CRITICAL
**Hipotesis:** Add `_check_resume_synthetic()` in FastAPI lifespan step 8 — query last incomplete `synthetic_runs` row → if found AND age <2h → auto-resume.
**Risk:** LOW — read-only check; if no row, no-op.
**Benefit:** Eliminates lesson #45 class of bug forever. Future deploys won't break long-running flywheel.
**Effort:** 1 hr.
**KPI:** kill+restart api container during synth → DPO continues incrementing within 60s.

### A2 — Innovation #1: Conversation Summarization (research-validated)
**Hipotesis:** When chat history >2900 tokens (70% of num_ctx=4096), summarize older 70% via local Qwen 7B → structured JSON `{decisions, entities, open_questions, user_preferences, last_intent}` → replace in-context. Last 30% turns + always-last-4-turns kept verbatim. NEVER summarize within tool-call sequence.
**Risk:** MEDIUM — orphaning tool_use_id pairs is the Day 39 bug class. Mitigation: only trigger between assistant final-answer turns, never mid-tool-loop.
**Benefit:** Unlocks long sessions (currently CTX-limited at 4096). Sleep-time compute cost = $0 (local Qwen). Doubles as DPO training data (model learning to summarize itself).
**Effort:** 3 hrs.
**KPI:** chat with >5 turns including 1 file paste → token count stays under 3500 across 10 turns; semantic recall test (does AI remember user's name from turn 1 at turn 8?).

### A3 — Cycle 1 SimPO Trigger (autonomous, gated DPO ≥500)
- Currently 450, ETA tonight after synth restart
- Cmd: `--loss-type apo_zero --simpo-beta 2.5 --use-apo --apo-lambda 0.05`
- Cost ~$0.51 RunPod spot 4090
- Identity gate ≥0.85 cosine vs baseline_day39.json

### A4 — Documentation: VISION_DISTINCTIVENESS_2026.md ⭐ DONE
**Status:** ✅ committed before this plan (anti-context-loss for strategic positioning).

### B1 — Sleep-time consolidator scaffolding (foundation for Innovation #4) — DEFER Day 46-47
Convert existing `services/memory_pruner.py` daemon → Letta-style consolidator pattern:
- Cron 03:00 daily
- Pull last 24h `messages` table → CAI quorum extracts durable facts
- Upsert to NEW `semantic_memory` Qdrant collection
- DEMOTE low-utility episodics (TTL on payload)

**Defer rationale:** A1+A2 are higher-priority Day 45 must-ships. B1 is Bulan 2 Week 7 anchor.

### C1 — A2A `/.well-known/agent.json` AgentCard — DEFER Bulan 3
60-day insurance window per research (ship before Q4-2026 A2A v1.0).

---

## 📊 5. KPI Day 45

| Item | Target | Verifikasi |
|------|--------|------------|
| A1 auto-resume | Container kill → synth resumes <60s | manual restart + watch DPO |
| A2 conv summarization | Long chat stays <3500 tok over 10 turns | chat E2E + log inspection |
| A3 Cycle 1 trigger | Autonomous when DPO ≥500 | RunPod logs |
| Lesson #45-47 logged | day45_progress.md updated | git diff memory/ |
| **v0.5.14** | health 200 + summarization endpoint live | curl |

---

## 💰 6. BUDGET PROJECTION Day 45

| Item | Estimate |
|------|----------|
| A1 auto-resume (zero infra) | $0 |
| A2 summarization (local Qwen, $0) | $0 |
| A3 Cycle 1 SimPO (when triggered) | $0.51 |
| Synthetic continued | $0.10 |
| **Day 45 total** | **~$0.61** |

Cumulative Bulan 2: $1.39 + $0.61 = **$2.00 of $30 (6.7%)** worst case.

---

## 🚦 7. EXIT CRITERIA — Day 45

Must-have:
- [x] VISION_DISTINCTIVENESS_2026.md committed
- [x] Synthetic gen restarted (run_id fd3acdd8)
- [ ] A1 auto-resume in lifespan
- [ ] A2 conv summarization shipped + E2E tested
- [ ] v0.5.14 deployed
- [ ] DAY45_RETRO.md committed
- [ ] day45_progress.md + MEMORY.md index

Stretch:
- [ ] DPO ≥500 → Cycle 1 trigger
- [ ] B1 sleep-time consolidator scaffolding
- [ ] Identity eval + PROMOTE/ROLLBACK decision

---

## 🛡️ 8. SCOPE BOUNDARIES (per STOP list)

❌ **DON'T BUILD Day 45:**
- More wrapper tools (Cline ships these weekly — we said STOP)
- Custom chat UI polish (Open WebUI 50k stars — STOP)
- Generic episodic memory upgrades (mem0 $25M — STOP)
- LangFuse v3 (research-refuted — needs ClickHouse 6-8GB)
- Dev mode E2B (deferred indefinitely — commoditized)

✅ **STAY FOCUSED ON THE MOAT:**
- A1: Defensive deploy (table-stakes engineering — must work for everything else)
- A2: Conv summarization (foundation for Dream Cycle Innovation #4)
- A3: Cycle 1 trigger (the closed loop differentiator)

---

## 🎓 9. LESSONS APPLIED + ANTICIPATED

45. **In-process background tasks die with the container.** EVERY async task that should outlive a deploy needs state persistence + auto-resume in lifespan + deploy-checklist entry. Day 44 deploy killed Day 43-44 synthetic gen flywheel for ~14h.

46. (anticipated) **Conversation summarization MUST avoid mid-tool-loop trigger** to prevent tool_use_id orphan bug class (Day 39 lesson). Trigger only between assistant final-answer turns.

47. (anticipated) **Vision doc as compass beats roadmap as schedule.** Research-revisable strategic positioning > date-stamped task list. Roadmap should be derivative of vision, not parallel to it.

---

## 🔭 POST-DAY-45 LOOKAHEAD (revised per VISION doc)

**Day 46-47 (Week 6 close):**
- B1 sleep-time consolidator (foundation)
- Cycle 1 hot-swap eval if PROMOTED
- Beta DM template polish (post-Cycle-1)

**Bulan 2 Week 7 (Day 50-56) — "Cognitive upgrade":**
- Qwen3-4B-Thinking benchmark vs Qwen2.5-7B (Trend 1)
- Hot-swap public eval demo (DD-2)
- Skill abstraction layer (B3 mitigation)

**Bulan 2 Week 8 (Day 57-65) — "Open + bold":**
- ⭐ **Dream Cycle prototype (Innovation #4 — bold move)**
- A2A AgentCard `/.well-known/agent.json` (B1 mitigation)
- Cross-vendor CAI as pip library (DD-3)
- GitHub repo public (Apache 2.0)

**Bulan 3 (Day 66-95) — "Verifier loop + lineage standard":**
- Train Qwen3-0.6B reward head (B2 mitigation, replaces expensive judge calls)
- ADO Genealogy Protocol v0.1 spec publication (DD-1)
- mighan.com clone marketplace foundation

---

**THIS IS THE COMPASS for Day 45. Strategic anchor = VISION_DISTINCTIVENESS_2026.md. Stop competing on tools. Compete on agents that EVOLVE and SURVIVE.**
