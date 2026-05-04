# Day 44 Retrospective — ONAMIX MCP Stdio Singleton + 6 NEW Tools v0.5.13

**Date:** 2026-05-04 (Day 44, Bulan 2 Week 6 Day 4)
**Versions shipped:** v0.5.12 → **v0.5.13** (ONAMIX MCP migration)
**Commits Day 44:** 3 (plan + feat + retro)
**Cost actual:** ~$0.00 (zero infra changes — pure code)
**Status:** ✅ **8x speedup verified empirically** + ADO brain expanded by 6 tools.

---

## ✅ DELIVERED & VERIFIED LIVE

### Track A — ONAMIX MCP Stdio Singleton ⭐
**Replaced:** Day 42 subprocess.run-per-call wrapper (Node.js cold-start ~80-200ms each)
**With:** Persistent `mcp.ClientSession` over stdio JSON-RPC, started once in FastAPI lifespan, reused across all requests.

**New module:** `services/onamix_mcp.py` (272 lines)
- `OnamixMCPClient` singleton with auto-respawn (exponential backoff 1→30s, 6 attempts)
- Process death detection on every `call_tool()` → respawn + retry once
- `set_global_client()` / `get_global_client()` accessor pattern
- AsyncExitStack lifecycle (clean teardown)
- Graceful import fallback if `mcp` SDK missing

**Lifespan integration:** `main.py` — start in step 7 (after memory pruner), teardown before pruner cancel.

**Empirical bench results (live, in-container):**
```
=== Subprocess (Day 42 path) ===
subprocess_1: ms=286 status=200
subprocess_2: ms=278 status=200
subprocess_3: ms=269 status=200
                              avg = 278ms

=== MCP stdio singleton (Day 44 path) ===
startup_ok=True startup_ms=393   (one-time, in lifespan)
call_1: ms=134 status=200        (cold network warmup)
call_2: ms=36  status=200
call_3: ms=31  status=200
                              warm avg = 34ms

SPEEDUP: 278ms → 34ms = ~8x faster (matches research-predicted 8-10x)
```

**Combined with Day 43 cache:**
| Path | MISS | HIT |
|------|------|-----|
| Subprocess (Day 42) | 278ms | n/a |
| Subprocess + Cache (Day 43) | 278ms | 0ms (1000x) |
| MCP + Cache (Day 44) | **34ms** | 0ms |

### Track A4 — 6 NEW Tools (FREE, MCP passthrough)
Live discovery: `hyperx-mcp.js` already exposes 9 tools. Migration unlocked **6 brand-new capabilities** with minimal handler code:

| Tool | Use case | Verified |
|------|----------|----------|
| `onamix_post` | POST requests (form/JSON body) — APIs, login, scraping | ✅ wired |
| `onamix_crawl` | Multi-page same-origin crawl (max 50 pages) | ✅ wired |
| `onamix_history` | Recent fetch history (debug/replay) | ✅ E2E (5 entries returned) |
| `onamix_links` | Extract+filter outgoing links | ✅ E2E (1 link from example.com, 129ms) |
| `onamix_config` | Get/set engine config (admin-only) | ✅ wired |
| `onamix_multi` | Parallel fetch up to 10 URLs | ✅ E2E (2 URLs in 70ms) |

**Total tools registered:** 17 → **23** (+6 new, +deprecated web_search kept for back-compat)

### Track B — Conversation Summarization — DEFERRED Day 45 (research captured)
Decision: focus Day 44 on Track A high-confidence win. Research findings captured in DAY44_PLAN.md for Day 45 execution.

### Track C — LangFuse v3 — SKIPPED (research-refuted)
Decision: confirmed v3 requires ClickHouse + 6-8GB RAM (kills Ollama on shared VPS). Day 45 will build minimal structlog→Postgres traces table (~50MB RAM). Future Phoenix on separate droplet post-beta.

### Track D — Cycle 1 SimPO Trigger — AUTONOMOUS PENDING
- Day 44 morning: 439 pairs
- Day 44 EOD: **450 pairs** (+11 over sprint)
- Need: 50 more for ≥500 gate
- ETA: ~50 min at current rate, autonomous trigger

---

## 📊 EMPIRICAL RESULTS

### Latency Comparison
| Operation | Day 42 (subprocess) | Day 44 (MCP) | Day 44 + cache HIT |
|-----------|---------------------|--------------|---------------------|
| onamix_get cold | ~286ms | 134ms | 0ms |
| onamix_get warm | ~278ms | **34ms** | 0ms |
| Startup overhead | 0 (paid per call) | 393ms (one-time) | n/a |

**Real-world implication:** A user asking 5 sequential URL fetches saves ~1.2 seconds (subprocess: 5×278=1390ms vs MCP: 134+4×34=270ms).

### New Tool Capability
- 6 net-new capabilities unlocked
- 0 lines of subprocess wrapper code added (all MCP passthrough)
- Skill schema entries added to `config/skills.json` for AI tool routing

---

## 🎓 LESSONS LEARNED Day 44 (3 new, **44 cumulative**)

42. **READ before WRAP** — research agent assumed ONAMIX was "just CLI" (recommended custom subprocess worker). Live inspection of `/opt/sidix/tools/hyperx-browser/bin/` revealed `hyperx-mcp.js` (full MCP server, 320 lines, 9 tools). Always inspect tool capabilities before scaffolding around assumptions. Research is starting point, not gospel.

43. **MCP ClientSession SDK >>> custom subprocess worker for any tool that already speaks MCP.** Protocol gives you for-free: ID multiplexing (concurrent calls on one stream), schema validation, capability negotiation, standardized error envelope (isError flag), graceful initialize/notifications handshake. Don't reinvent.

44. **Skip popular SaaS observability when self-host requirements outscale your VPS** — LangFuse v3 mandates ClickHouse cluster (~6-8GB RAM minimum). On a 32GB VPS already running Postgres+Redis+Qdrant+Ollama-7B, that OOMs the LLM. Minimal SQL+structlog beats forced infra. Phoenix or v2 if you must have UI.

---

## 🚦 EXIT CRITERIA STATUS

- [x] services/onamix_mcp.py singleton + lifespan integration LIVE
- [x] _onamix_get/search/scrape refactored MCP-first (subprocess fallback)
- [x] 6 new tool handlers wired + skills.json + tool_cache config
- [x] v0.5.13 deployed + 8x speedup empirically verified
- [x] DAY44_PLAN.md + DAY44_RETRO.md committed
- [ ] DPO ≥500 → SimPO Cycle 1 (autonomous, ETA ~50 min)
- [ ] Conversation summarization (defer Day 45)
- [ ] Beta soft-launch (defer post-Cycle-1)

---

## 💰 BUDGET ACTUAL Day 44

| Item | Estimated | Actual |
|------|-----------|--------|
| MCP migration (zero infra) | $0 | $0 |
| Synthetic continued | $0.10 | $0.00 (covered by ongoing run) |
| Cycle 1 SimPO | $0.51 | $0 (not yet triggered) |
| **Day 44 total** | **~$0.61** | **~$0.00** |

Cumulative Bulan 2: $1.39 + $0.00 = **$1.39 of $30 (4.6%)**.

---

## 🔭 DAY 45 LOOKAHEAD

### Track A — Conversation Summarization (Innovation #1) ⭐
- Trigger: ~2900 tokens (70% of num_ctx=4096), NOT 2000 (research-validated)
- Summarizer: local Qwen 7B (sleep-time compute, $0 cost, doubles as DPO data)
- Hierarchical: older 70% summarized, last 30% verbatim, last 4 turns ALWAYS verbatim
- Output: structured JSON `{decisions, entities, open_questions, user_preferences, last_intent}`
- AVOID: never summarize within tool-call sequence (orphans tool_use_id pairs)

### Track B — Minimal Observability (replacement for skipped LangFuse)
- structlog→Postgres `traces` table (4 columns: trace_id, ts, event, payload_json)
- 5 SQL views: token cost, latency P95, tool exec timing, error rate, DPO progress
- ~50MB RAM, ~50 lines of code, 1 day effort

### Track C — Cycle 1 hot-swap eval (if PROMOTED overnight)
- Identity baseline + safety bench
- A/B traffic split if structlog views ready

### Track D — Beta DM template polish (post-Cycle-1)

---

## 📈 PRODUCTION HEALTH (end Day 44)

| Component | Status |
|-----------|--------|
| API v0.5.13 | ✅ healthy |
| Tools live | **23** (was 17 — +6 new ONAMIX MCP) |
| **ONAMIX MCP singleton** | ✅ LIVE (auto-respawn ready, 8x speedup verified) |
| **Tool cache** | ✅ LIVE (Day 43, all 6 new tools properly configured) |
| **JWT auto-refresh** | ✅ LIVE (Day 43, 60min TTL + silent refresh) |
| Synthetic gen | ✅ running (DPO 450 → ≥500 ETA ~50 min) |
| Bulan 2 spend | $1.39 of $30 (4.6%) |
| Lessons cumulative | **44** |

---

## 🧠 ADO ALIGNMENT CHECK Day 44 changes

| Feature | MCP-first? | Skill-portable? | Memory-aware? |
|---------|-----------|-----------------|---------------|
| ONAMIX MCP client | ✅ native MCP | ✅ stdio = portable to any framework | n/a (web layer) |
| 6 new tools | ✅ MCP passthrough | ✅ skills.json registered | ✅ cache-aware (per-tool TTL) |

**Day 44 = textbook ADO modular brain migration.** ONAMIX speaks MCP natively; we now consume it via standard SDK; future agents using MiganCore via MCP gateway get all 6 new tools automatically.

---

**Day 44 = SHIPPED + DEPLOYED + 8x SPEEDUP EMPIRICALLY VERIFIED + 6 free tools unlocked. 44 lessons cumulative. Bulan 2 still 4.6% spend (zero infra cost Day 44).**
