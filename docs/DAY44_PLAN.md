# Day 44 Plan — ONAMIX MCP Stdio Singleton (8-10x speedup) + observability triage
**Date:** 2026-05-05 (Day 44, Bulan 2 Week 6 Day 4)
**Drafted by:** Claude Sonnet 4.6 — full mandatory protocol
**Triggered by:** User: "Ok catat, dan sprint!" (after Day 43 close-out)
**Research:** parallel agent (3 tracks: MCP stdio + conv summarization + LangFuse) + live VPS inspection

---

## 🧭 1. CONTEXT (Day 44 morning)

| Item | State |
|------|-------|
| API | v0.5.12 healthy |
| DPO pool | **439** (+7 overnight, need 61 more for Cycle 1 ≥500 gate) |
| Cycle 1 ETA | tonight or Day 45 morning (autonomous) |
| Bulan 2 spend | $1.39 of $30 (4.6%) |
| Tools live | 15 (3 ONAMIX via subprocess wrapper) |
| Lessons | 41 cumulative |

---

## 🔬 2. RESEARCH SYNTHESIS — 3 TRACKS

### Track A — ONAMIX MCP Stdio Singleton ⭐ PRIMARY
**Research said:** Wrap as asyncio.subprocess worker pattern (since CLI not MCP).
**Live discovery (refuted):** ONAMIX **already ships `hyperx-mcp.js`** — a full MCP server (JSON-RPC 2024-11-05, 320 lines, 9 tools).
**Revised approach:** Use Python `mcp.ClientSession` + `stdio_client` directly. Standard MCP protocol — no custom worker, no manual lock (SDK handles JSON-RPC ID multiplexing).

**Tools discovered (9 — was 3):**
- `hyperx_get` (current `onamix_get`)
- `hyperx_search` (current `onamix_search`)
- `hyperx_scrape` (current `onamix_scrape`)
- `hyperx_post` ⭐ NEW (POST requests with form/JSON body)
- `hyperx_crawl` ⭐ NEW (multi-page same-origin crawl, max 50 pages)
- `hyperx_history` ⭐ NEW (recent fetch history)
- `hyperx_links` ⭐ NEW (extract+filter links from URL)
- `hyperx_config` ⭐ NEW (engine config get/set)
- `hyperx_multi` ⭐ NEW (parallel fetch up to 10 URLs)

**Bonus value:** Migration buys us 6 new tools FREE (no extra wrapper code per tool — just MCP passthrough).

**Risk:** LOW
- Python `mcp>=1.27.0` already in requirements (Day 26 MCP server work)
- ONAMIX MCP path: `/opt/sidix/tools/hyperx-browser/bin/hyperx-mcp.js`
- Container already has `/app/hyperx` mount (Day 42)
- Fallback: keep subprocess code path as last-resort

**Effort:** ~3-4 hr
1. Create `services/onamix_mcp.py` (singleton client lifecycle)
2. Wire into FastAPI `lifespan()` — start once, share across requests
3. Refactor `_onamix_*` handlers in `tool_executor.py` → `session.call_tool()`
4. Add 6 new tool handlers (passthrough — minimal code)
5. Auto-respawn on crash (process death detection)
6. Benchmark: old subprocess MISS vs new MCP MISS

**Expected impact:**
- 80-200ms per call → 8-25ms (research validated, Cline benchmarks Nov 2025)
- Combined with Day 43 cache: HIT stays at 0ms, MISS drops 8-10x
- 6 new tools → ADO browser brain expanded

### Track B — Conversation Summarization (Innovation #1) — DEFER Day 45
**Research validated:**
- Trigger at ~2900 tokens (70% of num_ctx=4096), NOT 2000 (too aggressive)
- Use local Qwen 7B as summarizer (not Kimi/Gemini — sleep-time compute, cost=$0, doubles as DPO training data)
- Hierarchical 70/30 (older 70% summarized, recent 30% verbatim, last 4 turns ALWAYS verbatim)
- Output: structured JSON `{decisions, entities, open_questions, user_preferences, last_intent}`
- Pitfall: NEVER summarize within tool-call sequence (orphans tool_use_id pairs — Day 39 bug class)

**Why defer:** Track A is high-value + research already done. Splitting Day 44 across both = neither shipped properly. Capture findings here, ship Day 45.

### Track C — LangFuse Self-Hosted — SKIP (research refuted)
**Honest finding (research):** LangFuse v3 PG-only mode does NOT exist. v3 mandates Postgres + ClickHouse + Redis + S3/MinIO + 2 LF containers. RAM ~16GB recommended, 8GB hard floor. Adding to existing VPS (Postgres+Redis+Qdrant+Ollama 7B) = OOMs Ollama.

**Replacement (Day 45-46):** Build 50-line structlog→Postgres `traces` table with 5 SQL views for: token cost, latency P95, tool exec timing, error rate. RAM cost: ~50MB.

**Future observability:** Post-beta, deploy Arize Phoenix (single container, SQLite, ~500MB) on same VPS, OR LangFuse v3 on separate $20/mo droplet.

### Track D — Cycle 1 SimPO Trigger (autonomous)
- Gate: DPO ≥500
- Current: 439, last 24h: +438 pairs (synthetic gen healthy)
- ETA: tonight or Day 45 morning
- Cmd: `--loss-type apo_zero --simpo-beta 2.5 --use-apo --apo-lambda 0.05` (Day 42 hyperparams)
- Cost: ~$0.51 RunPod spot 4090

---

## 📐 3. TASK LIST — H/R/B FRAMEWORK

### A1 — Create `services/onamix_mcp.py` singleton
**Hipotesis:** Persistent MCP ClientSession in FastAPI lifespan eliminates per-call subprocess spawn (~80-200ms).
**Risk:** LOW — fallback to subprocess still works. asyncio handles JSON-RPC multiplexing.
**Benefit:** 8-10x latency drop + auto-multiplexed concurrent calls.
**Effort:** 1 hr.

### A2 — Wire lifespan + auto-respawn
**Hipotesis:** Detect process death (returncode != None) → respawn with exponential backoff.
**Risk:** LOW — even if respawn fails, subprocess fallback intact.
**Benefit:** Zero-downtime resilience.
**Effort:** 30 min.

### A3 — Refactor `_onamix_get/search/scrape` handlers
**Hipotesis:** Replace `_onamix_run` subprocess wrapper with `client.call_tool(name, args)`.
**Risk:** MEDIUM — schema/response format must match what tool_executor returns. Validate via E2E benchmark before/after.
**Benefit:** Cleaner code (no parser regex), proper MCP error handling.
**Effort:** 1 hr.

### A4 — Add 6 new tool handlers (passthrough)
**Hipotesis:** Since they're real MCP tools, wrappers can be 5-line passthroughs to `client.call_tool`.
**Risk:** LOW — same pattern as A3.
**Benefit:** 21 total tools (was 15) — major capability expansion.
**Effort:** 30 min.

### A5 — Bump v0.5.13, deploy, E2E benchmark
**KPI:** old MISS latency vs new MCP MISS latency. Target ≥3x speedup (research said 8-10x but Node startup cost matters).

---

## 📊 4. KPI Day 44

| Item | Target | Verifikasi |
|------|--------|------------|
| A1-A2 MCP singleton | health 200 + lifecycle log "onamix.mcp.started" | container logs |
| A3 latency | onamix_get MISS <50ms (was ~150-340ms) | curl bench MISS x3 |
| A4 new tools | 21 tools registered, hyperx_post + hyperx_crawl callable | /v1/admin/tools list |
| Cache compat | Day 43 cache HIT still ~0ms | bench HIT x3 |
| **DPO** | ≥500 (Cycle 1 gate) | /v1/public/stats |
| **v0.5.13** | health 200 + bench passes | curl + log inspection |

---

## 💰 5. BUDGET PROJECTION Day 44

| Item | Estimate |
|------|----------|
| MCP migration (zero infra) | $0 |
| Synthetic continued | $0.10 |
| Cycle 1 SimPO (if triggered) | $0.51 |
| **Day 44 total** | **~$0.61** |

Cumulative Bulan 2: $1.39 + $0.61 = **$2.00 of $30 (6.7%)** worst case.

---

## 🚦 6. EXIT CRITERIA — Day 44

Must-have:
- [ ] services/onamix_mcp.py singleton + lifespan integration
- [ ] _onamix_* handlers refactored to call_tool()
- [ ] 6 new tool handlers wired (post/crawl/history/links/config/multi)
- [ ] v0.5.13 deployed + benchmark results documented
- [ ] DAY44_RETRO.md committed

Stretch:
- [ ] DPO ≥500 → Cycle 1 trigger
- [ ] Conv summarization scaffolding (defer if time)

---

## 🛡️ 7. SCOPE BOUNDARIES

❌ **DON'T BUILD Day 44:**
- LangFuse v3 (research-refuted — RAM kills Ollama)
- Conversation summarization (defer Day 45 — needs dedicated focus)
- Self-debug loop (Day 46)
- Beta soft-launch (post-Cycle-1)

✅ **STAY FOCUSED:**
- ONAMIX MCP singleton (research-validated 8-10x + 6 free tools)
- Cycle 1 trigger when autonomous gate (no manual intervention)

---

## 🎓 8. LESSONS APPLIED + ANTICIPATED

42. **READ before WRAP** — research agent assumed ONAMIX was "just CLI"; live inspection found full MCP server. Always inspect tool capabilities before scaffolding around assumptions.
43. (anticipated) MCP ClientSession SDK >>> custom subprocess worker for any tool that already speaks MCP — protocol gives you for-free: ID multiplexing, schema validation, capability negotiation.
44. (anticipated) Skip popular SaaS observability when self-host requirements outscale your VPS — minimal SQL+structlog beats forced ClickHouse cluster.

---

## 🔭 POST-DAY-44 LOOKAHEAD

**Day 45:**
- Conversation summarization (Innovation #1) at 2900-token threshold + structured JSON + local Qwen 7B
- Minimal observability: structlog→Postgres traces table + 5 SQL views
- Cycle 1 v0.1 hot-swap eval (if PROMOTED)

**Day 46:**
- Self-debugging loop (Innovation #3)
- Beta soft-launch prep (if Cycle 1 PASS)

**Day 47-49:**
- Beta DM 3 friends (Fahmi own-use first)
- Iteration on feedback

---

**THIS IS THE COMPASS for Day 44. Track A primary (high-confidence + bonus tools), Track C skip (refuted), Track B defer Day 45, Track D autonomous.**
