# Day 42 Plan — HYPERX Integration + LangFuse + Cycle 1 Trigger
**Date:** 2026-05-04 (Day 42, Bulan 2 Week 6 Day 2)
**Drafted by:** Claude Sonnet 4.6 — full mandatory protocol
**Companion:** RECAP_DAY36-41.md (just committed)
**Research:** parallel agent `a78fd1bf` (HYPERX/Cycle1/observability/portability)

---

## 🧭 1. CONTEXT

| Item | State Day 42 morning |
|------|----------------------|
| API | v0.5.9 healthy |
| DPO pool | 391 (need 109 more) |
| ETA Cycle 1 trigger | Today (mid-day or evening) |
| Bulan 2 spend | $1.19 of $30 (4%) |
| Tools | 12 registered |
| Smithery | LIVE PUBLIC |
| HYPERX | Discovered Day 41, Day 42 integrate |

---

## 🔬 2. RESEARCH SYNTHESIS — 4 GAME-CHANGERS

| Finding | Source | Impact |
|---------|--------|--------|
| **Persistent stdio MCP client > subprocess.Popen per call** | mcp Python SDK v1.6 Mar 2026 | Node startup 80ms × N = death; persistent client ~45MB RAM |
| **SimPO `loss_type=apo_zero`** outperforms vanilla on <1k pairs | TRL maintainers Mar 2026 PR #87 | Free win for Cycle 1 — better margin stability |
| **LangFuse v3 PG-only mode** (no ClickHouse) | langfuse v3.42 Apr 2026, discussion #4521 Feb 2026 | Fits 32GB VPS ~600MB RAM |
| **Agent File (.af) spec** — Letta + CrewAI + LangGraph signed Apr 2026 | github.com/letta-ai/letta v0.7.0 | ADO portability story = early adopter narrative |

### Surprises
- **Spot 4090 ($0.34) interruption rate dropped to ~6%** Q1 2026 (was 15-20% 2024) → use SPOT for Cycle 1 (~$0.51 total cost vs $1.10 on-demand)
- **APO-zero loss** quietly outperforming vanilla SimPO TRL Mar 2026 benchmark
- AIOS-v2 from Rutgers Apr 2026 added "agent migration API" — watch only

---

## 📐 3. TASK LIST — H/R/B FRAMEWORK

### A1 — HYPERX Integration (Persistent stdio MCP client) ⭐ HIGHEST ROI

**Hipotesis:** Mount /opt/sidix/tools/hyperx-browser → /app/hyperx (RO), spawn hyperx-mcp.js as persistent stdio MCP server in FastAPI lifespan, Python uses MCP SDK stdio_client to call. Memory: ~45MB persistent. Latency: <100ms after init.

**Adaptasi gagal:** Subprocess.Popen per call as fallback (80ms cold-start tolerable for occasional use).

**Impact:** **3 new tools** (hyperx_get, hyperx_search 7 engines, hyperx_scrape regex) replace existing limited web_search (DDG). Aligns with ADO modular brain (user-owned tool = first-class).

**Benefit:**
- 7 search engines vs 1 (DDG)
- Anonymous browsing (privacy)
- Built-in proxy support
- $0 cost (no third-party API)
- ADO modularity reinforced

**Risk:**
- MEDIUM — stdio MCP needs `asyncio.Lock()` (single-threaded)
- LOW — Node.js runtime in container already added Day 41 (Marp deps)
- MEDIUM — singleton lifecycle: must restart on container restart

**Effort:** ~2-3 jam (mount + lifespan + tool wrapper + test)

### A2 — LangFuse Self-Hosted (PG-only mode) ⭐ MUST BEFORE CYCLE 1

**Hipotesis:** LangFuse v3.42 PG-only Docker compose runs on existing Postgres + ~600MB RAM. SDK decorator integration: `@observe(as_type="generation")`. Wajib live SEBELUM Cycle 1 trigger untuk capture baseline metrics.

**Adaptasi gagal:** Tunda LangFuse Day 43, run Cycle 1 tanpa observability — metrics manual via DB.

**Impact:** Win-rate tracking (thumbs ratio, response length delta, turn-2 retention) untuk PROMOTE/ROLLBACK decision Day 42 evening.

**Benefit:**
- Trace setiap chat completion + tool call + vision/STT
- A/B routing data infrastructure (X-Model-Version header)
- Long-term observability foundation

**Risk:**
- LOW — separate container, doesn't touch existing services
- MEDIUM — PG connection pool tuning (must set `LANGFUSE_FLUSH_INTERVAL=5` or trace writes block FastAPI)

**Effort:** ~1.5 jam (docker-compose addition + SDK integration + verify dashboard)

### A3 — Cycle 1 SimPO Trigger (autonomous when DPO ≥500)

**Update from research:**
- `loss_type=apo_zero` (TRL 0.15+ better margin stability)
- `beta=2.5` (sweet spot small data — UPDATE from Day 39 default 2.0)
- `gamma_beta_ratio=0.55`
- `save_steps=50, max_steps=500`
- **SPOT $0.34/hr** (interruption ~6% Q1 2026 — acceptable risk)
- `--stop-after 7200s` autokill safety

**Cost:** ~$0.51 total (~90min run)

**Hipotesis:** With apo_zero + beta 2.5 + 500 anchor pairs → identity preservation ≥0.85 cosine + win_rate ≥55% vs base.

**Adaptasi gagal:** ROLLBACK if eval <0.85, document failure mode, retry with smaller LR.

**Risk:**
- MEDIUM — spot interruption (mitigated checkpoint every 50 steps)
- LOW — APO loss term wired Day 38, identity baseline ready Day 39
- HIGH — model collapse on small dataset (mitigated by APO + early-stop signals)

**Effort:** Setup ~30 min, run ~90 min autonomous, eval ~30 min

### A4 — DEFER Day 43+
- A4 status hierarchy seeing/hearing
- Admin Dashboard fix (proper /admin + API Keys UI)
- Smithery quality polish (homepage migancore.com, README, badge)
- Beta soft-launch (after Cycle 1 v0.1 hot-swap if PROMOTE)
- .af exporter scaffold (Day 43 design)

---

## 📊 4. KPI PER ITEM (Day 42)

| Item | Target | Verifikasi |
|------|--------|------------|
| A1 HYPERX MCP client | 3 tools registered (hyperx_get/search/scrape) | TOOL_REGISTRY listing |
| A1 HYPERX latency | <500ms per call (after init) | log timestamp deltas |
| A2 LangFuse running | dashboard.migancore.com:3000 (or sub-path) | curl health |
| A2 First trace captured | chat call appears in dashboard | manual chat + check |
| A3 SimPO triggered | RunPod pod running | runpodctl status |
| A3 Cycle 1 complete | adapter saved to /workspace/v0.1 | RunPod artifacts |
| A3 Identity gate | ≥0.85 cosine | eval/v0.1.json |
| **v0.5.10** | health 200 + 15 tools | curl |
| **DPO** | ≥500 (trigger gate) | /v1/public/stats |

---

## 💰 5. BUDGET PROJECTION Day 42

| Item | Estimate |
|------|----------|
| HYPERX integration | $0 (no API) |
| LangFuse self-host | $0 (existing Postgres) |
| Cycle 1 SimPO (spot) | $0.51 |
| Synthetic continued | $0.20 |
| Buffer | $0.10 |
| **Day 42 total** | **~$0.81** |

Cumulative Bulan 2: $1.19 + $0.81 = **$2.00 of $30 cap (6.7%)**.

---

## 🚦 6. EXIT CRITERIA — Day 42

Must-have:
- [ ] HYPERX MCP client live + 3 tools registered
- [ ] LangFuse dashboard accessible + first trace captured
- [ ] DPO ≥500 → Cycle 1 triggered (autonomous)
- [ ] v0.5.10 deployed
- [ ] `docs/DAY42_PROGRESS.md` + memory committed

Stretch:
- [ ] Cycle 1 complete + identity eval ≥0.85 → PROMOTE v0.1
- [ ] Hot-swap GGUF Q4 to Ollama
- [ ] A/B 10% traffic via X-Model-Version

---

## 🛡️ 7. SCOPE BOUNDARIES

❌ **DON'T BUILD Day 42:**
- A4 status hierarchy (defer)
- Admin Dashboard (defer Day 43-44)
- Smithery polish (defer)
- Beta invite (wait Cycle 1 result)
- .af exporter actual code (only design Day 42)
- Web builder (Day 60-65)
- Dev mode (Day 50-58)

✅ **STAY FOCUSED:**
- HYPERX integration (ADO modularity proof)
- LangFuse (Cycle 1 prerequisite)
- Cycle 1 trigger (autonomous)

---

## 🎓 8. LESSONS APPLIED + NEW

35. **Persistent stdio MCP client > per-call subprocess.** Node startup 80ms × N calls = bottleneck. Singleton pattern in app lifespan.
36. **`loss_type=apo_zero`** > vanilla SimPO on <1k pairs (TRL Mar 2026 benchmark). Free win.
37. **Spot 4090 interruption rate dropped to 6%** Q1 2026 → safe to use spot for short runs (≤2hr).
38. **Agent File (.af) standardization** = ADO portability story. Letta + CrewAI + LangGraph adopted. Early adopter narrative for MiganCore.

---

## 🔭 POST-DAY-42 LOOKAHEAD

**Day 43:**
- Admin Dashboard fix + API Keys UI
- A4 status hierarchy (seeing/hearing)
- Beta first 3 invites (if Cycle 1 PROMOTED)

**Day 44-46:**
- Input artifacts (Docling/MarkItDown) parse_artifact tool
- Audio edit (FFmpeg MCP wrapper)
- Beta 1-on-1 sessions

**Day 47-49:**
- Bug iteration from beta feedback
- generate_video tool (fal.ai Kling)
- Episodic image memory

---

**THIS IS THE COMPASS for Day 42. 3 must-have items, ~5 jam, ~$0.81 budget.**
