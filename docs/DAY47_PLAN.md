# Day 47 Plan — Comprehensive QA + Contract Assertions (the meta-pattern)
**Date:** 2026-05-05 (Day 47, Bulan 2 Week 6 Day 7)
**Drafted by:** Claude Sonnet 4.6 — full mandatory protocol
**Triggered by:** User: "iterasi lagi testing, review, negative test, stress test... pastikan semua berjalan sesuai visi"
**Research:** parallel agent (5-dimension QA synthesis + meta-pattern discovery)
**Strategic anchor:** `docs/VISION_DISTINCTIVENESS_2026.md`

---

## 🧭 1. CONTEXT (Day 47 morning)

| Item | State |
|------|-------|
| API | v0.5.14 healthy |
| Containers | 6/6 UP (api, letta, ollama, postgres, qdrant, redis) |
| DPO pool | **473/500** (+18 overnight, need 27 for Cycle 1 ≥500 gate) |
| Cycle 1 ETA | 1-2 hours, autonomous |
| Bulan 2 spend | $1.44 of $30 (4.8%) |
| Tools live | 23 (14 assigned to core_brain) |
| Lessons | 50 cumulative |
| Day 46 fix verified | E2E (Wikipedia search → 343ms typical) |

---

## 🚨 2. THE META-PATTERN (research-validated)

Days 39/44/45/46 all share ONE root cause:

> **Silent state drift across async/process boundaries.**
> An invariant that *should* hold had **no runtime assertion** guarding it.

| Day | Silent Drift |
|-----|--------------|
| 39 | `asyncio.create_task` swallowed exception → assistant message never persisted (2 days silent) |
| 44 | container kill killed background synthetic task → DPO flywheel died (14h silent) |
| 45 | auto-resume skip-list excluded "cancelled" → fix didn't fire on first deploy |
| 46 | `agents.json` drift from `skills.json` over 5 sprints → brain saw deprecated tool only |

**Solution: Design by Contract for LLM Agents** (2026 SOTA emerging in Letta v0.6, Pydantic AI, Instructor):
1. **Boot-time contract validation** — scan tool registry × agent assignment × prompt schema; fail-fast on drift
2. **Runtime invariant probes** — global `TaskRegistry` + watchdog, every 30s assert registered async tasks alive OR cleanly removed
3. **Output contracts at every LLM boundary** — non_empty_str, valid_json, size < limit; reject + retry on violation
4. **State-machine guards on resume/transition logic** — explicit FSM, illegal transitions raise

**One file (`services/contracts.py`) addresses all 4 historical bug classes.**

---

## 📐 3. DAY 47 TASK LIST — H/R/B FRAMEWORK

### A1 — `services/contracts.py` module ⭐ META-FIX
**Hipotesis:** A single contracts module with (a) boot-time tool-registry-vs-agent-assignment validator, (b) `safe_task()` wrapper with TaskRegistry, (c) `assert_non_empty_response()` validator covers Day 39/44/46 bug classes systematically.
**Risk:** LOW — pure additions, fail-loud-not-silent, safe_task can wrap existing create_task incrementally.
**Benefit:** Catches the entire bug class, not just one instance. Pays dividends every future sprint.
**Effort:** 2 hr.
**KPI:** Boot-time check fires on intentional drift (drop a tool from agents.json, deploy, expect "tool_drift" log+exit). Runtime watchdog logs every 60s with task counts.

### A2 — Comprehensive QA test sweep across 5 dimensions
Per research, run real smoke tests:

**Backend:**
- Every TOOL_HANDLERS entry called once with minimal valid args → assert success
- ONAMIX MCP singleton: call_tool ping
- Tool cache: write/read/expire cycle
- Conv summarizer: 4 guard cases (already done Day 45 ✅)
- Auto-resume: state-machine cases

**Frontend:**
- chat.html: render an SSE event sequence (start, chunk, tool_start, tool_result, done) end-to-end via test fixture
- Verify image attach payload format
- Error states (network drop simulation)

**Database:**
- Postgres connectivity from API
- conversations + messages persistence (verify Day 38 chat-continuity fix held)
- Multi-tenant RLS isolation

**Tools:**
- onamix_search wikipedia engine (verified Day 46 ✅)
- analyze_image (Gemini Vision) — needs real test image
- web_read (Jina) — needs real URL
- generate_image (fal.ai) — defer (costs $0.003)
- export_pdf — markdown→PDF
- export_slides — markdown→PPTX

**Integration:**
- Real chat flow: prompt → tool routing → tool exec → answer streaming → message persist
- JWT silent refresh on 401 (verified Day 43 ✅)
- ONAMIX MCP auto-respawn on process kill

### A3 — Negative tests
**Hipotesis:** Probe known failure modes from research.
- Malformed tool args (trailing comma, NaN, oversized)
- Empty Ollama response (Day 46 regression check)
- Expired JWT mid-stream
- Tool returns >256KB
- 10 sequential tool calls (loop limit)
- ONAMIX MCP process killed mid-call → respawn + retry

### A4 — Light stress test
**Hipotesis:** 5 concurrent chat streams on 32GB CPU VPS — verify no Ollama queue collapse.
- Use Python asyncio.gather with 5 chat requests
- Measure: latency P50/P95, error rate, memory headroom

### A5 — Cycle 1 SimPO trigger (autonomous, gated DPO ≥500)
- Currently 473, ETA 1-2 hr
- No manual intervention needed

---

## 📊 4. KPI Day 47

| Item | Target | Verifikasi |
|------|--------|------------|
| A1 contract validator | Boot-time check logs `contracts.boot.ok` with N tools/agents | container logs |
| A1 safe_task | All `create_task` in chat.py wrapped, watchdog logs every 60s | log inspection |
| A2 backend QA | All TOOL_HANDLERS callable (no import/handler errors) | smoke test script |
| A2 DB QA | conversations table queryable + RLS working | pg query check |
| A3 negative | All 6 known modes gracefully handled (no 500, no empty bubble) | E2E test results |
| A4 stress | 5 concurrent: P95 <120s, 0 errors | k6 or asyncio.gather |
| Cycle 1 trigger | Autonomous when DPO ≥500 | RunPod logs |
| **v0.5.15** | health 200 + contracts module live | curl + logs |

---

## 💰 5. BUDGET PROJECTION Day 47

| Item | Estimate |
|------|----------|
| Contracts module (zero infra) | $0 |
| QA tests (in-container, free) | $0 |
| Stress test (local) | $0 |
| Cycle 1 SimPO (when triggered) | $0.51 |
| Synthetic continued | $0.10 |
| **Day 47 total** | **~$0.61** |

Cumulative Bulan 2 worst case: $1.44 + $0.61 = **$2.05 of $30 (6.8%)**.

---

## 🚦 6. EXIT CRITERIA — Day 47

Must-have:
- [ ] services/contracts.py with boot validator + safe_task + watchdog
- [ ] Wired into main.py lifespan + chat.py
- [ ] All TOOL_HANDLERS smoke-tested green
- [ ] DB persistence verified (conversation+message round-trip)
- [ ] 6 negative tests run + documented
- [ ] Light stress test results captured (5 concurrent)
- [ ] v0.5.15 deployed
- [ ] DAY47_RETRO.md committed

Stretch:
- [ ] DPO ≥500 → Cycle 1 trigger
- [ ] Identity eval if Cycle 1 PROMOTE
- [ ] Frontend Playwright skeleton (defer if time)

---

## 🛡️ 7. SCOPE BOUNDARIES (per VISION compass)

❌ **DON'T BUILD Day 47:**
- More wrapper tools (STOP — commoditizing)
- New search engines (Tavily etc.) — Day 48 polish
- Beta soft-launch (post-Cycle-1)
- Sleep-time consolidator (Day 48 — needs Cycle 1 baseline first)

✅ **STAY FOCUSED:**
- Contract assertions module (highest leverage — kills 4 historical bug classes)
- Comprehensive QA validation (visi: handal, kuat, skalabel)
- Cycle 1 trigger autonomous

---

## 🎓 8. LESSONS APPLIED + ANTICIPATED

51. (anticipated) **Design by Contract for LLM Agents** is the unifying pattern for silent-state-drift bugs. Boot-time validators + TaskRegistry watchdog + output contracts + FSM guards = one module addresses Day 39/44/45/46 simultaneously.

52. (anticipated) **5-dimension QA discipline:** backend handlers, frontend rendering, database persistence, tool execution, integration flow. Each dimension can mask another's bugs (Day 46 was a tool-config bug that LOOKED like a brain-emit bug). Test all 5 every sprint.

53. (anticipated) **Stress test on real hardware before claiming "scalable."** 32GB CPU VPS has hard ceiling ~5-8 concurrent active streams. Marketing "production-ready" without empirical concurrency curve = liability.

---

## 🔭 POST-DAY-47 LOOKAHEAD

**Day 48-49:** Sleep-time consolidator (foundation for Dream Cycle), Cycle 1 hot-swap if PROMOTE, beta soft-launch prep.

**Bulan 2 Week 7 (Day 50-56):** Per VISION compass — Qwen3-4B-Thinking benchmark, hot-swap public eval demo, skill abstraction layer.

**Bulan 2 Week 8 (Day 57-65):** ⭐ Dream Cycle prototype, A2A AgentCard, cross-vendor CAI pip library.

---

**THIS IS THE COMPASS for Day 47. Meta-fix > one-off fixes. QA discipline > "it works on my machine." Anti-context-loss documentation > silent ship.**
