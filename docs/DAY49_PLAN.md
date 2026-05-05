# Day 49 Plan — CYCLE 1 SimPO Trigger (the missing "Self-Improving v1")
**Date:** 2026-05-05 (Day 49, Bulan 2 Week 7 Day 2)
**Drafted by:** Claude Sonnet 4.6 — full mandatory protocol
**Triggered by:** User: "QA seamless dulu... cognitive trends 2026-2027... pondasi kokoh" (post Day 48 close-out)
**Research:** parallel agent (Cycle 1 SimPO best practices May 2026) + 4 original IDE re-read
**Strategic anchor:** `docs/VISION_DISTINCTIVENESS_2026.md` + `compass_artifact_wf-...md` (original 30-day blueprint)

---

## 🧭 1. THE GAP BETWEEN VISION & STATE

**Original 30-day blueprint promise:** *"Seed is Alive + Self-Improving v1"* in 30 days.

**Day 49 reality (48 days in):**
| Component | Original Vision | Current State |
|-----------|-----------------|---------------|
| Seed alive | Qwen2.5-7B GGUF Q4 on Ollama | ✅ Running, 7-14 tok/s |
| Self-improving via SimPO | Train cycle on synthetic+CAI pairs | ❌ **NEVER actually triggered** |
| Identity eval gate | ≥0.85 cosine drift | Baseline captured Day 39, never run vs trained model |
| Hot-swap to live | Ollama Modelfile swap, A/B traffic | Framework wired Day 35, never used |
| DPO pool | ≥500 pairs minimum | ✅ **588** (passed gate, 88 over) |

**Conclusion:** The "Self-Improving" half of the original promise is **unverified**. We have all the infrastructure. We have the data (588 pairs > 500 gate). We just have **never pulled the trigger**. Day 49 closes that gap.

This is the long-promised "Aha Moment."

---

## 🔬 2. RESEARCH SYNTHESIS (May 2026)

### Hyperparameter refinements vs Day 42 config
| Parameter | Day 42 | Day 49 (research-validated) | Source |
|-----------|--------|------------------------------|--------|
| `loss_type` | `apo_zero` | `apo_zero` ✓ keep | Karel D'Oosterlinck Aug 2024; correct for weak-base regime |
| `simpo_beta` | 2.5 | 2.5 ✓ keep | Princeton SimPO Issue #50 |
| `gamma_beta_ratio` | 0.4 (γ=1.0/β=2.5) | 0.4 ✓ keep | safe band, low-margin edge OK for small data |
| `learning_rate` | 8e-7 | **5e-7** ⭐ | arxiv 2602.00954 (Feb 2026): <1k pairs need lr halved to avoid reward hacking |
| `epochs` | 1 | 1 ✓ keep | >1 epoch overfits at this size |
| `apo_lambda` | 0.05 | 0.05 ✓ keep | Letta benchmark: identity-anchor conservative-correct |
| `save_steps` | 50 | 50 ✓ keep | survives ~5% spot preemption with 1-2 checkpoints recoverable |
| `padding_free` | not set | **True** ⭐ | TRL 1.x feature, ~2x mem headroom |
| `use_liger_kernel` | not set | **True** ⭐ | TRL 1.x feature, stacks with padding_free |

### Identity preservation gates (research-tightened)
- **PROMOTE gate**: cosine ≥0.85 mean **AND** ≥0.75 minimum (no prompt below floor)
- **WARNING band**: 0.85-0.90 (acceptable but flag)
- **Embedding model**: switch from sentence-transformers default → **BGE-M3** (multilingual, robust to paraphrase, 2026 SOTA for persona similarity)
- **Eval count**: 160 prompts (current Day 39 baseline) is OK for v0.1 but undersized; expand to 300+ for v0.2

### RunPod May 2026 reality
- Spot RTX 4090 ~$0.34/hr, 4090 community cloud
- Interruption rate <5% outside model-launch windows; 30%+ during major releases
- **Unsloth Docker image** = ~2x training throughput + ~50% VRAM reduction vs base PyTorch+TRL
- **Estimated wall-clock**: 15-25 min for 588 pairs at 7B Unsloth+APO-Zero
- **Estimated cost**: **$0.10-0.15 per cycle** — well under $7 hard cap (lets us afford 40+ ablation runs)

### GGUF + Ollama hot-swap footguns (verified 2026)
- llama.cpp ≥ b8475 required (preserves Qwen2.5 chat template + tool-call format)
- Merge order: `save_pretrained_merged()` → `convert_hf_to_gguf.py` → `llama-quantize Q4_K_M`
- Modelfile `TEMPLATE` block must be copied verbatim from `ollama show qwen2.5:7b-instruct-q4_K_M --modelfile`
- `OLLAMA_KEEP_ALIVE=24h` during A/B (default 5min causes cold-reload latency)
- Preserve `PARAMETER num_ctx 4096` (Day 20 explicit setting; Ollama default reverts)

---

## 📐 3. DAY 49 TASK LIST — H/R/B FRAMEWORK

### A1 — Pre-flight (THIS SESSION, ~30 min)
**Hipotesis:** All training/eval/swap infrastructure already exists from Day 35-42; Day 49 only needs minor config refinement + DPO export verification.
**Risk:** LOW — read-only checks + local export, no RunPod spend.
**Benefit:** Confirms readiness before spending RunPod budget.
**Effort:** 30 min.
**Steps:**
1. Verify `training/train_simpo.py` accepts new hyperparams (lr=5e-7, padding_free, use_liger_kernel)
2. Verify `training/export_dataset.py` outputs DPO-format JSONL
3. Verify `eval/run_identity_eval.py` works against `eval/baseline_day39.json`
4. Export 588 DPO pairs locally → check format + size
5. Pre-stage everything in /tmp ready for RunPod upload

### A2 — Cycle 1 trigger (REQUIRES USER GO-AHEAD, ~25 min wall-clock + $0.15)
**Hipotesis:** Single SimPO run on 588 pairs with research-validated hyperparams produces an adapter passing identity gate ≥0.85.
**Risk:** MEDIUM — model collapse possible (mitigated by APO λ=0.05 + identity gate); RunPod preemption (mitigated by save_steps=50).
**Benefit:** Closes the 30-day blueprint promise. Validates self-improving claim. Produces first MiganCore-branded checkpoint.
**Cost:** ~$0.15 (Unsloth on spot 4090, 15-25 min).
**Steps (autonomous after user approves):**
1. Push DPO JSONL to HuggingFace temporary dataset OR direct RunPod upload
2. Launch RunPod pod via API (Unsloth Docker, RTX 4090 spot)
3. SSH/exec training script with new hyperparams
4. Save checkpoints every 50 steps to S3-compatible storage
5. Download final adapter on completion

### A3 — Identity eval + PROMOTE/ROLLBACK gate
**Hipotesis:** Trained adapter preserves persona ≥0.85 mean cosine vs baseline_day39.json.
**Risk:** MEDIUM — if FAIL, ROLLBACK + analyze + try lower lr (3e-7) next cycle.
**Benefit:** Public proof of "modular brain that survives weight changes" claim.
**Effort:** ~10 min eval run.
**Cmd:** `python eval/run_identity_eval.py --adapter ./migancore-v0.1 --baseline eval/baseline_day39.json --embedding bge-m3`
**Decision:**
- Mean ≥0.85 AND min ≥0.75 → **PROMOTE** to GGUF + Ollama
- Mean 0.80-0.85 OR min 0.65-0.75 → WARNING band, log + manual review
- Mean <0.80 OR min <0.65 → **ROLLBACK** + post-mortem

### A4 — GGUF conversion + Ollama hot-swap (if PROMOTE)
**Hipotesis:** `unsloth.save_pretrained_merged()` + llama.cpp convert + Ollama push produces working `migancore:0.1` model.
**Risk:** LOW per research — well-documented path, just need correct llama.cpp build (≥b8475).
**Benefit:** First MiganCore-branded model live in production.
**Effort:** ~15 min on VPS.
**Steps:**
1. Merge adapter with base via Unsloth
2. Convert to GGUF Q4_K_M
3. `ollama create migancore:0.1 -f Modelfile` (Modelfile copied from base + new FROM)
4. `OLLAMA_KEEP_ALIVE=24h` env var set
5. Update agents.json `core_brain.model_version` → `migancore:0.1` (or A/B traffic split)

### A5 — Documentation + handoff
- DAY49_RETRO.md
- memory/day49_progress.md
- AGENT_HANDOFF_MASTER.md update
- Update VISION doc with "Cycle 1 PROMOTED" status

---

## 📊 4. KPI Day 49

| Item | Target | Verifikasi |
|------|--------|------------|
| A1 pre-flight | All 5 checks PASS, JSONL ≥588 lines | local script output |
| A2 Cycle 1 | RunPod adapter file downloaded | RunPod logs + adapter size ~50MB |
| A3 identity eval | Mean ≥0.85, min ≥0.75 | eval JSON output |
| A4 GGUF + Ollama | `ollama list` shows `migancore:0.1` | curl /api/tags |
| Cost actual | <$0.50 | RunPod billing |
| **v0.5.17** | health 200 + first MiganCore-branded model | curl + log |

---

## 💰 5. BUDGET PROJECTION Day 49

| Item | Estimate |
|------|----------|
| Pre-flight (zero infra) | $0 |
| RunPod Cycle 1 (Unsloth spot 4090) | $0.15 |
| Optional ablation: γ/β schedule | $0.30 |
| **Day 49 total** | **~$0.50** |

Cumulative Bulan 2 worst case: $1.44 + $0.50 = **$1.94 of $30 (6.5%)**.
RunPod saldo $16.17 → after Cycle 1 ~$15.97 (98% reserve preserved for Cycle 2-6).

---

## 🚦 6. EXIT CRITERIA — Day 49

Must-have (this session):
- [x] DAY49_PLAN.md committed (research-validated, H/R/B)
- [ ] A1 pre-flight: training/eval/swap infrastructure verified
- [ ] DPO 588 pairs exported as JSONL
- [ ] User explicit GO/NO-GO for A2 RunPod trigger ($0.15-0.50 spend)

Stretch (autonomous if user GO):
- [ ] A2 Cycle 1 adapter trained
- [ ] A3 identity eval passes ≥0.85/0.75
- [ ] A4 `migancore:0.1` live on Ollama
- [ ] DAY49_RETRO.md committed

---

## 🛡️ 7. SCOPE BOUNDARIES (per VISION compass)

❌ **DON'T BUILD Day 49:**
- Frontend changes (chat UI is fine; Cycle 1 is invisible to user)
- More tools (STOP list — see VISION compass)
- Sleep-time consolidator (Day 50 — needs Cycle 1 baseline first)
- Bold γ/β schedule ablation IF time-pressed (defer to Cycle 2)

✅ **STAY FOCUSED:**
- Cycle 1 trigger = THE missing piece between 48-day reality and 30-day blueprint promise
- Validates entire "Self-Improving" thesis
- Unblocks beta soft-launch (model is now ours, not vanilla Qwen)

---

## 🎓 8. LESSONS APPLIED + ANTICIPATED

54. (anticipated) **Infrastructure-ready ≠ shipped.** From Day 35 (hot-swap framework) and Day 42 (SimPO trainer), all components existed but never wired together. Aha Moments require the CHAIN, not just the links. Day 49 = chain assembly.

55. (anticipated) **Research-validated single-metric discipline.** PROMOTE/ROLLBACK on identity cosine alone (not AlpacaEval + MT-Bench + identity = 3 ways to be blocked). Pick one well-baselined metric, keep others informational.

56. (anticipated) **Cost discipline pays off in option count.** $0.15/cycle on Unsloth = 40+ ablation runs within $7 cap. Cheap iteration > expensive perfection.

---

## 🔭 POST-DAY-49 LOOKAHEAD

**Day 50:** Cycle 1 PROMOTE eval (24h A/B win-rate vs base Qwen) + sleep-time consolidator (foundation for Dream Cycle Innovation #4)

**Day 51-55 (Bulan 2 Week 7 close):** Hot-swap public eval demo (DD-2 — unfakeable proof of "modular brain"); Qwen3-4B-Thinking benchmark vs Cycle 1 v0.1.

**Day 56-65 (Week 8):** Dream Cycle prototype (Innovation #4); A2A AgentCard; cross-vendor CAI pip library; GitHub repo public.

---

## 🧠 ADO ALIGNMENT CHECK Day 49

| Feature | MCP-first? | Skill-portable? | Memory-aware? | Vision-aligned? |
|---------|-----------|-----------------|---------------|------------------|
| Cycle 1 SimPO | n/a (training) | ✅ adapter is portable across any compatible base | ✅ pairs harvested from episodic memory | ⭐ THE proof of "agents that EVOLVE" thesis |
| Identity eval gate | n/a | ✅ baseline JSON portable | ✅ persona is THE memory | ⭐ proves "agents that SURVIVE model swaps" |

**Day 49 = textbook closure of original 30-day vision.** All Day 41-48 work was foundation. This is the wall.

---

**THIS IS THE COMPASS for Day 49. Pre-flight first (no spend), then user GO/NO-GO on Cycle 1 trigger ($0.15-0.50). All research-validated. All infrastructure already exists.**
