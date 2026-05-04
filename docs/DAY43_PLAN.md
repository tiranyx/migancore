# Day 43 Plan — JWT Auto-Refresh + Tool Caching + ONAMIX MCP Migration Prep
**Date:** 2026-05-04 (Day 43, Bulan 2 Week 6 Day 3)
**Drafted by:** Claude Sonnet 4.6 — full mandatory protocol
**Triggered by:** User: "masih belum bisa baca. iterasi, optimasi iterasi, kalo bisa inovasi" + Invalid token bug screenshot
**Research:** parallel agent `ac81f98` (JWT/ONAMIX/innovation Top 3)

---

## 🧭 1. CONTEXT

| Item | State Day 43 morning |
|------|----------------------|
| API | v0.5.10 → **v0.5.11** (JWT fix shipped) |
| DPO pool | **427** (need 73 more for SimPO trigger) |
| ETA Cycle 1 | tonight or Day 44 morning |
| Bulan 2 spend | $1.29 of $30 (4.3%) |
| Tools | 15 (3 ONAMIX) |
| Lessons | 38 cumulative |

---

## 🐛 2. USER-BLOCKING BUG (root cause + fix)

**Symptom:** "Invalid or expired token" muncul saat user retry chat (15 min after login). Retry button → empty bubble.

**Root cause:**
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15` (default)
- Frontend stored `refresh_token` di localStorage tapi **TIDAK auto-call** `/v1/auth/refresh` saat 401
- User harus logout + login ulang manually

**Fix v0.5.11:**
- Frontend `apiFetch()` + `startStream()`: detect 401 → silent `tryRefreshToken()` → retry once
- Single-flight lock (concurrent 401s share one `/v1/auth/refresh` promise — prevents rotation race)
- Backend JWT_ACCESS_TOKEN_EXPIRE_MINUTES bumped 15 → **60** min (defense in depth)
- Refresh token TTL stays 7 days (atomic rotation, Day 1)

**Test:** Wait 60+ min, send chat → no error, brain responds normally. Refresh happens silently in background.

---

## 🔬 3. RESEARCH SYNTHESIS — INNOVATION TOP 3

Per research agent (`ac81f98`), 3 innovations bisa ship Day 43-49 untuk ADO modular brain:

| # | Innovation | Effort | Impact |
|---|-----------|--------|--------|
| **#1** | **Conversation summarization @ 2000-token threshold** | 6h | Unlocks long sessions (4096 ctx limit), align Day 16 episodic RAG |
| **#2** | **Tool result caching in Qdrant (idempotent calls)** | 3h | 80% repeat tool latency saved, ONAMIX search cached 5min, kb 24h |
| **#3** | **Self-debugging loop (tool error → auto-correct)** | 4h | Cursor-pattern: stderr fed back to ReAct loop, max 2 attempts |

**Skipped (rationale):**
- Voice realtime — Whisper.cpp CPU too slow, defer post-GPU Day 50+
- Multi-agent spawn UX — infra exists, no UX win this week
- Inline React components — security/sandbox cost too high
- Letta sleep-time compute — needs background worker redesign Day 50+

---

## 📐 4. DAY 43 TASK LIST — H/R/B FRAMEWORK

### A1 — JWT Silent Refresh + TTL Bump ⭐ DONE (v0.5.11 deployed)
**Status:** ✅ SHIPPED. User unblocked.

### A2 — Tool Result Caching in Qdrant (Innovation #2)
**Hipotesis:** Cache idempotent tool calls (search, web_read, analyze_image) di Qdrant 5-24h TTL → 80% repeat latency saved + future API cost reduction.
**Cache key:** SHA256(tool_name + sorted args JSON + tool_version)
**TTL per tool:**
- onamix_search: 5 min (volatile)
- onamix_get / web_read: 10 min
- analyze_image: 24h (image hash → caption stable)
- generate_image: never (creative variance desired)
**Adaptasi gagal:** Tools fallback to fresh call (current behavior).
**Impact:** Repeated user queries hit cache instantly (ONAMIX search "AI news today" 1s → 50ms).
**Benefit:** Especially valuable when synthetic gen calls overlap with chat — same prompts cached.
**Risk:** LOW — cache miss = current behavior; per-tool TTL config prevents stale results.
**Effort:** ~3 hr (cache layer wrapper + Qdrant collection + per-tool TTL config + invalidation hook)

### A3 — Conversation Summarization (Innovation #1) — DEFER Day 44
**Hipotesis:** When chat history >2000 tokens, auto-summarize old turns into structured episodic memory entry, replace in-context with `[CONTEXT: previous N turns summarized as: <summary>]`.
**Effort:** 6h — sizeable, deserves dedicated day.
**Trigger:** Day 44 morning (if Cycle 1 not yet triggered).

### A4 — Self-Debugging Loop (Innovation #3) — DEFER Day 45
**Hipotesis:** Tool error → ReAct loop sees stderr → "fix and retry" message → max 2 attempts.
**Effort:** 4h — needs careful loop control to prevent infinite retry.
**Trigger:** Day 45 (post-Cycle-1).

### B1 — ONAMIX MCP Stdio Migration — DEFER Day 44
**Research basis:** Cline+Cursor+Continue.dev all use `mcp.ClientSession` singleton pattern.
**Real numbers:** stdio singleton ~8-25ms/call vs subprocess ~80-200ms = **8-10x speedup**.
**Effort:** ~1 full day (lifespan integration + asyncio.Lock + auto-respawn).
**Migration steps Day 44:**
1. Add `mcp.ClientSession` singleton to FastAPI lifespan
2. Replace `_onamix_run` subprocess calls with `session.call_tool(...)` JSON-RPC
3. Keep CLI fallback for resilience
4. Benchmark old vs new latency

### Track A — Cycle 1 (autonomous when DPO ≥500)
- DPO 427 → ETA today/tomorrow morning
- Trigger: `--loss-type apo_zero --simpo-beta 2.5 --use-apo --apo-lambda 0.05`
- Cost ~$0.51 spot 4090

### Track B — Beta Soft-Launch (post-Cycle-1)
- Fahmi 1-day own-use smoke test
- Invite 3 friends via DM template

---

## 📊 5. KPI PER ITEM (Day 43)

| Item | Target | Verifikasi |
|------|--------|------------|
| A1 JWT refresh | No 401 errors after 60+ min session | manual test wait + send chat |
| A2 Tool cache | onamix_search "X" repeat <100ms (vs 1000ms first) | curl benchmark |
| **DPO** | ≥500 (trigger gate) | /v1/public/stats |
| **v0.5.12** | health 200 + tool cache verified | curl + log inspection |

---

## 💰 6. BUDGET PROJECTION Day 43

| Item | Estimate |
|------|----------|
| JWT fix (frontend+config) | $0 |
| Tool cache (Qdrant existing) | $0 |
| Synthetic continued | $0.20 |
| Cycle 1 SimPO (if triggered) | $0.51 |
| **Day 43 total** | **~$0.71** |

Cumulative Bulan 2: $1.29 + $0.71 = **$2.00 of $30 (6.7%)**.

---

## 🚦 7. EXIT CRITERIA — Day 43

Must-have:
- [x] JWT auto-refresh shipped + verified (v0.5.11 LIVE)
- [ ] Tool result caching layer + per-tool TTL config
- [ ] v0.5.12 deployed + benchmarks documented
- [ ] DPO progress logged (target 500)
- [ ] `docs/DAY43_PROGRESS.md` + memory committed

Stretch:
- [ ] DPO ≥500 → Cycle 1 trigger
- [ ] Beta soft-launch (Fahmi → 3 friends DM)
- [ ] Smithery quality polish

---

## 🛡️ 8. SCOPE BOUNDARIES

❌ **DON'T BUILD Day 43:**
- Voice realtime (post-GPU Day 50+)
- Inline React components (sandbox cost)
- ONAMIX MCP migration (Day 44 dedicated)
- Conversation summarization (Day 44)
- Self-debug loop (Day 45 post-Cycle-1)
- Multi-agent UX, Letta sleep-time, A-LoRA

✅ **STAY FOCUSED:**
- JWT user-blocking fix (DONE)
- Innovation #2 tool caching (3h ROI win)
- Cycle 1 trigger when DPO ≥500 (autonomous)

---

## 🎓 9. LESSONS APPLIED + NEW

39. **JWT 15min default too short for AI debugging sessions.** CPU 7B inference + tool exec + multi-iteration debug = >15min easy. Bump 60min OR auto-refresh BOTH (defense in depth).
40. **Single-flight lock mandatory for refresh token rotation.** Without it, parallel REST + SSE 401s double-rotate, both end up invalid.
41. **Tool result caching = 80% latency win for free.** Especially for idempotent calls (search, fetch). Per-tool TTL config prevents staleness.

---

## 🔭 POST-DAY-43 LOOKAHEAD

**Day 44:**
- ONAMIX MCP stdio migration (8-10x speedup target)
- Conversation summarization @ 2000 tokens
- LangFuse self-hosted (if Cycle 1 triggered Day 43)

**Day 45:**
- Self-debugging loop (Innovation #3)
- Cycle 1 v0.1 hot-swap (if PROMOTED)
- A4 status hierarchy seeing/hearing

**Day 46-49:**
- Beta soft-launch (3 friends → 5)
- Bug iteration from feedback
- Input artifacts (Docling/MarkItDown — Day 43-46 plan)

---

**THIS IS THE COMPASS for Day 43. Priority 1 SHIPPED (JWT fix). Innovation #2 in progress (tool caching).**
