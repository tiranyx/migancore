# Day 39 Plan — SSE Tool Exec Fix + Cycle 1 Pre-flight + Distribution
**Date:** 2026-05-04 (Day 39, Bulan 2 Week 5 Day 4)
**Drafted by:** Claude Sonnet 4.6 — full mandatory protocol
**Triggered by:** User: "Lanjut Day 39 dengan protokol"
**Research source:** parallel agent `aab93eb3` (5 areas: SimPO/Smithery/SSE-tool/multimodal/observability) + Day 38 RETRO

---

## 🧭 1. CONTEXT INHERITED

| Item | Value Day 39 morning |
|------|----------------------|
| API version | v0.5.5 (chat continuity fix) live |
| DPO pool | 323 (synthetic_seed_v1: 297, cai_pipeline: 16, distill_kimi_v1: 10) |
| ETA SimPO trigger (≥500) | Day 39 evening hingga Day 40 |
| RunPod saldo | $16.17 (key dropped Day 38) |
| Bulan 2 spend | $0.59 of $30 cap (2%) |
| Synthetic gen | restarted run_id `6cc5c060` |
| Discovered Day 38 bug | stream `/chat/stream` emit raw `memory_write({...})` text — beta blocker ⚠️ |

---

## 🔬 2. RESEARCH SYNTHESIS — 6 GAME-CHANGERS

| Finding | Source | Impact |
|---------|--------|--------|
| **SimPO Q2 2026 hyperparameter update** (community shifted from paper defaults) | princeton-nlp/SimPO #47 #62 + arxiv 2502.01112 | β=2.0 ✅, γ=**1.0** (was 1.4), apo_λ=**0.05** (was 0.1), lr=**8e-7** (was 5e-6), epochs=**1** (NEVER 2 di <700 pairs) |
| Cost RTX 4090 4hr = **$2.80** with flash-attn 2.7+ | (was $5.50) | Save $2.70 vs original estimate |
| **SSE tool exec pattern** = Ollama native `tool_calls` field, NOT text parsing | Vercel AI SDK v4.2 + ollama Qwen2.5 native support | Clean architectural fix (no text parsing) |
| **Smithery.ai = informal GitHub PR** | smithery-ai/registry, auto-validate ~10min, free unlimited | 1hr task, no review wait |
| **Whisper.cpp WASM tiny.en (3MB)** in browser <500ms | r/LocalLLaMA Apr 2026 | Mic UX zero API cost (defer Day 40 implementation) |
| **MCP `tools/list_changed`** notification | MCP spec 2026-03 | Hot-add tools without client reconnect (defer) |

### Risk Forecasts (must mitigate before $2.80 RunPod spend)
1. **Identity drift Cycle 1** — 323 pairs thin. **Include 50 identity-anchor pairs in training set** + identity_eval gate ≥0.85 BEFORE hot-swap
2. **RunPod spot interruption** — use **on-demand ($0.74/hr vs $0.34 spot)** OR checkpoint every 25 steps + auto-resume

---

## 📐 3. DAY 39 TASK LIST — H/R/B FRAMEWORK

### TRACK A — Critical Beta Blocker

#### A1 — Stream endpoint tool execution fix ⭐ HIGHEST PRIORITY
**Hipotesis:** Migrate `/chat/stream` ke pattern: detect Ollama `tool_calls` field, execute, re-prompt, continue stream. SSE event types: `text-delta`, `tool-call-start`, `tool-call-result`, `text-delta`.
**Adaptasi gagal:** Sync `/chat` (with director) sebagai fallback in frontend; mark stream endpoint experimental.
**Impact:** Tool calls in chat actually work end-to-end (currently emits raw `memory_write({...})` text — fundamental UX break).
**Benefit:** Beta users can ACTUALLY use tools (image gen, search, memory, vision, files).
**Risk:**
- MEDIUM — refactor stream handler, frontend may need new event handlers too
- LOW — fallback to sync chat available (frontend can switch endpoint based on tools present)

**Effort:** ~3 jam (backend refactor + frontend SSE event handler updates)

---

### TRACK B — Cycle 1 Pre-flight (saves $2.80 if pipeline broken)

#### B1 — Update `train_simpo.py` with research-driven hyperparameters
**Changes:**
- `--simpo-gamma` default 1.4 → **1.0**
- `--apo-lambda` default 0.1 → **0.05**
- `--learning-rate` default 5e-6 → **8e-7**
- `--epochs` default 2 → **1**
- New `--length-normalize` flag (community fix Mar 2026 for Qwen2.5-7B over-length reward)

**Hipotesis:** With updated hyperparameters, SimPO Cycle 1 will produce model with identity_consistency ≥0.85 + win_rate ≥55% vs base (paper benchmark on similar setups).
**Adaptasi gagal:** Revert to old defaults + retry with smaller LR steps.
**Impact:** Cycle 1 actually works on first try (vs over-fitting catastrophe).
**Benefit:** $2.80 well-spent → migancore-7b-soul-v0.1.

**Effort:** ~30 min (defaults + flag + dry-run verify)

#### B2 — Identity eval baseline
**Hipotesis:** Baseline Qwen2.5-7B-Instruct → cosine sim ~0.92-0.97 vs reference (high — same model self-comparison; tests pipeline correctness).
**Adaptasi gagal:** Fix script issues locally before Cycle 1 trigger.
**Impact:** Catches eval bugs, prevents wasted $2.80.
**Benefit:** Trust gate for v0.1 promote/rollback decision.
**Effort:** ~30 min (run + commit `eval/baseline.json`)

**Trigger:** Run when synthetic temporarily paused OR when DPO ≥450 (close to threshold) to balance Ollama load.

---

### TRACK C — Distribution + Quality

#### C1 — Smithery.ai MCP listing 🎁
**Hipotesis:** PR to `smithery-ai/registry` with `smithery.yaml` → auto-merge after CI validation (~10 min).
**Adaptasi gagal:** Self-host listing on migancore.com homepage; submit PR later.
**Impact:** Free top-of-funnel discovery (Smithery has 2k+ servers, ~10k weekly users).
**Benefit:** Migancore visible to MCP ecosystem. Aligned with Bulan 2 Week 8 open-source goal.
**Risk:** LOW — informal PR, no review.

**Effort:** ~1 jam (write smithery.yaml + open PR + verify)

---

### TRACK D — DEFER Day 40

| Item | Why defer |
|------|-----------|
| Frontend mic + image attach UI (~6hr) | Backend ready (analyze_image, STT); UI can ship Day 40 with WhisperWASM (no API cost) |
| LangFuse self-hosted observability (~3hr) | Need POST-Cycle-1 (track v0.1 vs base) — not pre-trigger |
| MCP tools/list_changed notification | Nice-to-have, post-MVP |
| Magpie 300K full download | Triggered overnight via remove `MAGPIE_QUICK=1`; doesn't need Day 39 attention |

---

### Autonomous (background)
- Synthetic gen running (`run_id 6cc5c060`, target 1000)
- Distillation Kimi pipeline ready (10 pairs done; rerun on demand)
- DPO pool monitoring → trigger SimPO Cycle 1 when ≥500

---

## 📊 4. KPI PER ITEM (Day 39)

| Item | Target | Verifikasi |
|------|--------|------------|
| A1 stream tool exec fix | tool calls work in stream chat | E2E: `memory_write` triggered, result reflected in answer |
| B1 train_simpo new defaults | dry-run shows updated config | grep logs for "SimPO beta=2.0 gamma=1.0 lr=8e-7 epochs=1" |
| B2 identity baseline | `eval/baseline.json` committed | file exists with 20 entries |
| C1 Smithery PR | merged or in-CI | github URL + status |
| **DPO pool EOD** | **≥500 (SimPO trigger)** OR **≥450 (close)** | `/v1/public/stats` |
| **v0.5.6 deployed** | health 200 + new /chat/stream behavior | curl /health + 1 stream tool call |

### Gate-and-Trigger
- IF DPO ≥500 by Day 39 EOD → **TRIGGER SimPO Cycle 1** Day 40 morning (with new hyperparams + APO λ=0.05)
- IF DPO <500 → continue, trigger Day 40 evening
- IF identity baseline FAIL → fix before any RunPod spend

---

## 💰 5. BUDGET PROJECTION Day 39

| Item | Estimate |
|------|----------|
| Stream tool exec fix testing | $0 (local Ollama only) |
| Identity baseline (Ollama) | $0 |
| Smithery PR | $0 |
| Synthetic continued (~14 hr quorum) | $0.30 |
| Distillation rerun small batch (optional) | $1.00 |
| Buffer | $0.20 |
| **Day 39 total** | **~$1.50** |

If SimPO triggers Day 39 EOD: +**$2.80** RunPod (new estimate with flash-attn 2.7+, was $5.50)
- Total Day 39 with Cycle 1: **$4.30**
- Cumulative Bulan 2: $0.59 + $1.50 + $2.80 = **$4.89 of $30 cap (16%)**

---

## 🚦 6. EXIT CRITERIA — Day 39

Must-have:
- [ ] `/chat/stream` produces clean tool execution (no raw text leakage)
- [ ] `train_simpo.py` defaults updated to research recommendations
- [ ] `eval/baseline.json` committed
- [ ] Smithery.ai PR opened (merged is bonus)
- [ ] v0.5.6 deployed + healthcheck pass
- [ ] DPO pool ≥450 (within 50 of trigger threshold)
- [ ] `docs/DAY39_PROGRESS.md` + `memory/day39_progress.md` committed

Stretch:
- [ ] DPO ≥500 → SimPO Cycle 1 triggered + $2.80 spend visible
- [ ] First Magpie shard (60K) used in synthetic via SEED_SOURCE=magpie_300k
- [ ] Stream tool exec frontend events wired in chat.html

---

## 🛡️ 7. SCOPE BOUNDARIES (re-affirmed)

❌ **DON'T BUILD Day 39:**
- LangFuse observability (Day 40 post-Cycle-1)
- Whisper.cpp WASM mic UI (Day 40 — when Cycle 1 results in)
- WebSocket realtime STT (Day 40+)
- Frontend image attach UI (Day 40)
- New tools (analyze_image dan friends sudah cukup)
- Smithery paid tier (free unlimited cukup)
- MCP tools/list_changed (post-MVP)
- Qwen3-7B upgrade

✅ **STAY FOCUSED:**
- Stream tool exec fix (beta UX critical)
- Cycle 1 pre-flight (eval + hyperparameter lock)
- Distribution prep (Smithery PR)

---

## 🎓 8. LESSONS APPLIED (cumulative 17 → applied here)

1. ✅ Compass doc per sprint (this file)
2. ✅ Research-first prevents waste (5 SimPO hyperparameter changes saved 1 ruined Cycle 1 run = $2.80)
3. ✅ ENV flag rollback on every new feature
4. ✅ Fallback chain priority (sync `/chat` is fallback if stream tool fix breaks)
5. ✅ Live deploy with WIP code beats "perfect locally"
6. ✅ Empirical velocity > theoretical projection
7. ✅ Stop building what others ship (Smithery exists, list there; Whisper.cpp WASM ready, use it)
8. ✅ Hardcoded fallback as feature (sync chat fallback for tool calls)
9. ✅ Don't ignore silent failures (chat continuity bug from Day 38 = lesson 18)

**NEW LESSON 18:** asyncio.create_task swallows exceptions silently. ALWAYS add explicit success log + check for `chat.persist_assistant.ok` style markers. Background tasks need explicit observability.

---

## 🔭 9. POST-DAY-39 LOOKAHEAD

**Day 40:** SimPO Cycle 1 complete + GGUF Q4 convert + identity eval v0.1 ≥0.85 + frontend multimodal UI (mic+image)
**Day 41:** Hot-swap v0.1 to production + LangFuse observability + A/B 10% traffic
**Day 42:** 24h A/B win-rate + Week 5 Retro
**Day 43-49 (Week 6):** Beta launch — 5 invited users, 1-on-1 onboarding sessions

---

**THIS IS THE COMPASS for Day 39. 4 must-have items, ~5jam, ~$1.50 budget. Cycle 1 trigger imminent.**
