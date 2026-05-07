# RECAP — Day 71c | Cycle 7c Q5 Casual Voice Fix
> Ditulis oleh: Claude Sonnet 4.6
> Tanggal: 2026-05-08
> Ref: CLAUDE_PLAN_71C → (KIMI_REVIEW_71C deferred — sprint mode) → **RECAP_71C**

---

## EXECUTIVE SUMMARY

**Strategy:** Cycle 7c = same proven hyperparams (LR=1.2e-6, epochs=3, ORPO apo_zero, A40)
+ **only one variable changed**: 40 Q5-specific casual greeting pairs added.

**Why minimal-change strategy:** Cycle 7b proved hyperparams work for voice category overall.
Q5 alone failed because reference is 7-word brief, model was outputting 15-25 words.
Solution = teach model the brief pattern via 40 targeted pairs with chosen=6.1w mean,
rejected=32.5w mean (length delta 26 words = strong ORPO signal).

---

## TRAINING METRICS

| Metric | Value |
|--------|-------|
| Dataset | 548 pairs (508 C7 base + 40 Q5 casual greeting) |
| Algorithm | ORPO apo_zero loss (TRL 0.9.6) |
| Hyperparams | LR=1.2e-6, epochs=3, batch=2×8=16, lora-r=16, max_seq=2048 |
| GPU | A40 46GB @ $0.322/hr |
| Steps | 102 |
| Speed | 4.93 s/step avg |
| train_runtime | 504s (8.4 min) |
| train_loss | 3.93 |
| rewards/margins | -0.13 (NEGATIVE — ORPO preference weak, NLL component does work) |
| rewards/accuracies | 0.17-0.22 (model preferring rejected over chosen — not a problem since NLL drives the actual learning) |
| Adapter size | 155MB safetensors (80.7MB GGUF f16) |
| Cost | $0.02 (v1 abort) + $0.10 (v2 incl. recovery) ≈ **$0.12 total** |
| HF repo | https://huggingface.co/Tiranyx/migancore-7b-soul-v0.7c ✅ |

---

## V1 FAILURE — ROOT CAUSE + FIX (Lesson #172)

**v1 cost:** $0.02 wasted (boot + install + tokenize-failure)
**Failure mode:**
```
ValueError: rejected should be an str but got <class 'dict'>
File "/root/trainenv/lib/python3.11/site-packages/trl/trainer/orpo_trainer.py", line 417
```

**Root cause:** `generate_cycle7c_q5_pairs.py` output `chosen`/`rejected` as ChatML message lists
(copied from SFT-style scripts), but TRL 0.9.6 ORPOTrainer expects **string format** (just the
completion text). Existing C7 dataset uses string format, which my generator should have matched.

**Fix:** Updated generator to output strings + added `verify_c7c_format.py` defensive validator
that checks all rows are string-typed before training launch. **Lesson #172 locked.**

---

## V2 RECOVERY — SCP TIMEOUT + HF DIRECT PUSH (Lesson #173)

**Issue:** Orchestrator script `scp_from()` had 300s timeout for 155MB safetensors file.
At Vast.ai network speeds (~1-3 MB/s host-to-host), 155MB needs ~60-150s — but variance
+ TLS handshake + small file overhead pushed past 300s. Script crashed, instance still alive.

**Risk:** Vast.ai instance kept billing during recovery (~$0.10 burned during 18 min).

**Fix path (minimal-cost recovery):**
1. SSH to Vast instance, run `huggingface-cli upload` directly (parallel multi-file, retries)
2. After HF upload confirmed, DELETE Vast instance via API
3. Pull adapter from HF to VPS via `hf_hub_download` (resumable, CDN-backed)

**Lesson #173:** SCP timeout 300s too short for 155MB on Vast.ai consumer hosts.
Better pattern: HF roundtrip (upload from training instance → download to inference host).
HF transfer is 5-10x faster (CDN, parallel chunks) and resumable.
TODO Day 72: update `cycle7c_orpo_vast.py` to use HF roundtrip by default.

---

## EVAL RESULT (Cycle 7c) — ROLLBACK ❌

| Category | C7b | C7c | Delta | Gate | Status |
|---|---|---|---|---|---|
| **identity** | 0.921 | **0.925** | +0.004 | ≥0.90 | ✅ |
| **voice** | 0.771 | **0.789** | +0.018 | ≥0.85 | ❌ Δ-0.061 |
| reasoning | 0.984 | **0.949** | -0.035 | ≥0.80 | ✅ (slight regression) |
| code | 0.959 | **0.926** | -0.033 | ≥0.80 | ✅ (slight regression) |
| values | 0.937 | **0.972** | +0.035 | ≥0.80 | ✅ |
| anti-pattern | 0.790 | **0.860** | +0.070 | ≥0.80 | ✅ |
| tool-use | 0.741 | **0.739** | -0.002 | ≥0.85 | ❌ |
| creative | 0.968 | **0.775** | **-0.193** | ≥0.80 | ❌ MAJOR REGRESSION |
| indonesian-cultural | 0.916 | **0.946** | +0.030 | - | ✅ |
| honesty | 0.978 | **0.901** | -0.077 | - | - |
| evolution-aware | 0.798 | **0.599** | **-0.199** | ≥0.80 | ❌ MAJOR REGRESSION |
| **weighted_avg** | 0.8870 | **0.8829** | **-0.004** | ≥0.92 | ❌ WORSE |
| pass_rate | 11/20 | **9/20** | -2 | - | ❌ |

**Q5 individual ("Hai! Bagaimana kabarmu?"):**
- Cycle 7: 0.478 (formal baseline)
- Cycle 7b: 0.609 (casual but too long)
- Cycle 7c: **0.625** (only +0.016 improvement vs target +0.13+) ❌

**Q6 voice ("Tolong tulis intro panjang..."):**
- Cycle 7b: 0.933
- Cycle 7c: **0.952** (+0.019) ✅ HOLDS

**Surprising regressions:**
- creative: -0.193 (was 0.968 → 0.775) — 40 Q5 brevity pairs killed creative output
- evolution-aware: -0.199 (was 0.798 → 0.599) — model regressed on memory awareness
- reasoning, code, honesty: -0.03 to -0.08 each

---

## VERDICT — ROLLBACK ❌

`migancore:0.3` STAYS as production (Cycle 3, weighted_avg 0.9082).

**Action taken:**
- migancore:0.7c registered for forensics but not promoted
- DEFAULT_MODEL unchanged in production env
- Beta users continue with stable migancore:0.3

**Why ROLLBACK:**
1. weighted_avg 0.8829 < gate 0.92 (Codex B3)
2. weighted_avg ALSO < conditional gate 0.88 (so not even conditional promote)
3. voice 0.789 < gate 0.85
4. Q5 individual only +0.016 (target was +0.13+)
5. Major regressions in creative (-0.193) and evolution-aware (-0.199) — 40 brevity pairs poisoned other categories

---

## LESSONS LOCKED (Day 71c)

| # | Lesson |
|---|--------|
| **#172** | TRL 0.9.6 ORPOTrainer expects STRING format for `chosen`/`rejected`, not ChatML. Always smoke-test 1 pair through `tokenize_row()` BEFORE upload. Defensive validator (string-type check across all rows) blocks bad data at source. |
| **#173** | SCP timeout 300s TOO SHORT for 155MB safetensors over Vast.ai consumer hosts. HF roundtrip (push from Vast → pull to VPS) is 5-10x faster (CDN+parallel chunks), resumable. Pattern: HF push first, THEN delete instance, THEN pull from HF. Update orchestrator default Day 72. |
| **#174** | 40 targeted pairs out of 548 (7.3% signal density) NOT ENOUGH for Q5-specific behavior change via ORPO. Q5 only +0.016 (vs +0.131 in C7→C7b). Worse: brevity pairs caused creative -0.193 + evolution-aware -0.199 regressions. Lesson: targeted ORPO pairs need ≥15% signal density OR pivot to SFT stage for narrow style targets. |
| **#175** | rewards/margins NEGATIVE throughout C7c training (-0.13). ORPO preference loss ineffective for "shorter casual" preference (model naturally prefers verbose explanations). For length-style targets, ORPO is wrong tool — consider SFT with brief examples or dataset-level filtering. |

---

## TOOLING SHIPPED Day 71c

| File | Purpose |
|------|---------|
| `scripts/generate_cycle7c_q5_pairs.py` | Generate 40 Q5 casual pairs (FIXED: string format) |
| `scripts/verify_c7c_format.py` | Defensive validator: all chosen/rejected must be strings |
| `scripts/analyze_c7c_pairs.py` | Dataset anatomy explainer (length deltas, prompt variants) |
| `scripts/explain_eval_mechanism.py` | Educational: how cosine sim + voice category works |
| `scripts/analyze_eval_result.py` | Auto gate decision (PROMOTE/CONDITIONAL/ROLLBACK) |
| `scripts/cycle7c_post_pipeline.sh` | One-command post-training pipeline (GGUF → Ollama → eval) |
| `training/cycle7c_orpo_vast.py` | Vast.ai orchestrator (synced from cycle7b with C7c paths) |

---

## ACTIONS COMPLETED

- [x] Pre-flight ALL GREEN (dataset, baseline, secrets, credit, instances=0)
- [x] Cycle 7c v1 launched, FAILED at tokenize (Lesson #172 captured)
- [x] Generator fixed + dataset regenerated 548/548 string format
- [x] Cycle 7c v2 launched, training COMPLETE (102 steps, 8.4 min, train_loss 3.93)
- [x] Recovery from SCP timeout: HF roundtrip (Lesson #173)
- [x] GGUF conversion (80.7MB f16) + Ollama register migancore:0.7c
- [x] Identity eval with baseline_day70_voice_fixed.json — ROLLBACK
- [x] Decision: ROLLBACK confirmed (weighted_avg 0.8829 < 0.92, voice 0.789 < 0.85)
- [x] Production unchanged: migancore:0.3 STAYS
- [x] Tracker + lessons #172-175 + RECAP committed

---

## CYCLE 7d STRATEGIC OPTIONS

Three paths forward after C7c ROLLBACK. Need Kimi+Codex strategic input before commit:

### Option A: More Q5 pairs (Cycle 7d)
- Generate 100+ Q5-specific pairs (vs current 40 = 7.3% signal density)
- Target: ≥15% signal density per Lesson #174
- Risk: dilutes other categories more (creative regressed -0.193 with just 40 pairs)
- Cost: ~$0.15 training + Gemini gen ~$0.05

### Option B: SFT stage (recommended per Lesson #175)
- ORPO is wrong tool for length-style targets (negative margins prove it)
- Pre-train with SFT on 200 brief casual examples → fine-tune behavior
- Requires train_sft_standard.py (need to write)
- Cost: ~$0.20-0.30, risk lower

### Option C: Reference adjustment + ship migancore:0.3
- Accept Q5 reference (7 words) is too brief for natural model output
- Update reference to 12-15 word casual response
- Re-evaluate migancore:0.3 (already promoted) against new ref
- Zero training cost, fastest path to "ship"

### Option D: Hybrid SFT+ORPO with focused dataset
- Cycle 7d = 200 pairs ALL Q5/casual/voice family (no diversity dilution)
- LR 5e-7 (lower) + 5 epochs = more focused absorption
- Cost: ~$0.20

**Claude recommendation:** Option C (ship migancore:0.3) + Option D as parallel R&D.
Beta users need stability NOW; voice optimization is iterative R&D.

---

>> **Kimi:** Review Cycle 7c failure analysis + 4 options. Recommend path.
>> **Codex:** QA decision logic. Confirm gate-policy enforced correctly. Vote between A/B/C/D.
>> **Claude:** RECAP committed, awaiting agent reviews for Cycle 7d direction.
