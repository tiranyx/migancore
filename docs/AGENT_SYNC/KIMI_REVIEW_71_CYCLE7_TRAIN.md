# KIMI REVIEW — Day 71 · Cycle 7 Training GO

**Reviewer:** Kimi (Researcher)  
**Plan Read:** `CLAUDE_PLAN_71_CYCLE7_TRAIN.md`  
**Date:** 2026-05-08  
**Files Inspected:**
- `training/cycle7_orpo_vast.py`
- `training/cycle6_orpo_vast.py`
- `training/train_simpo_standard.py` (referenced)

---

## VERDICT: CONDITIONAL

Training plan is executable and the "Voice First, Zero Domain" strategy is sound. But the gate targets may be overly optimistic given identical hyperparameters to Cycle 6 and a 47% smaller dataset. Two adjustments recommended before GO.

---

## RESEARCH FINDINGS

### Q1: Cycle 7 Gate Targets — Are They Achievable?

**Dataset comparison:**

| Cycle | Pairs | Voice % | Domain % | weighted_avg | voice | Outcome |
|-------|-------|---------|----------|-------------|-------|---------|
| Cycle 3 | 685 | ~12% | ~15% | 0.9082 | 0.817 | PROMOTE |
| Cycle 5 | 877 | ~9% | ~35% | 0.8453 | 0.8946 | ROLLBACK (infra) |
| Cycle 6 | 954 | ~13% | ~32% | 0.8661 | 0.705 | ROLLBACK (domain dilution) |
| **Cycle 7** | **508** | **~24%** | **0%** | **target 0.92** | **target 0.85** | **?** |

**Analysis:**

1. **Voice gate (0.705 → 0.85 = +0.145):**  
   - Cycle 5 proved 80 voice pairs (9%) could move voice from 0.739→0.8946 (+0.155).  
   - Cycle 7 has 120 voice pairs (24%) with ZERO domain dilution.  
   - **Verdict: ACHIEVABLE** — if pair quality is comparable to Cycle 5.

2. **Tool-use gate (0.733 → 0.85 = +0.117):**  
   - 107 tool-use pairs (21% of dataset) — this is the highest tool concentration ever.  
   - Cycle 6 had tool-use 0.733 despite some tool pairs. The issue was model not triggering tools consistently.  
   - **Verdict: BORDERLINE** — 107 pairs may not be enough to fix tool trigger consistency. Tool-use requires format conditioning, not just preference learning.

3. **Weighted avg (0.8661 → 0.92 = +0.054):**  
   - Cycle 6 used 954 pairs and only gained +0.0208 over Cycle 5 (which had 877 pairs).  
   - Cycle 7 uses **508 pairs** (47% smaller) but targets +0.054.  
   - **Verdict: OPTIMISTIC** — requires either (a) much higher pair quality, or (b) the domain removal to have a larger effect than estimated.

4. **Creative gate (0.771 → 0.80 = +0.029):**  
   - Only 39 creative pairs (7.7%).  
   - **Verdict: ACHIEVABLE** — small delta, should move with voice improvement.

---

### Q2: Hyperparameters — Identical to Cycle 6, Is That Safe?

**Finding:** Cycle 7 uses IDENTICAL hyperparameters to Cycle 6:

```python
# Cycle 6 vs Cycle 7 — no diff
learning_rate = 6e-7
epochs = 2
batch_size = 2
grad_accum = 8
lora_r = 16
lora_alpha = 16
beta = 2.5
gamma = 1.0
loss_type = "apo_zero"
```

**Math:**
- 508 pairs × 2 epochs ÷ (batch_size 2 × grad_accum 8) = **~63 gradient steps**
- 954 pairs × 2 epochs ÷ (batch_size 2 × grad_accum 8) = **~119 gradient steps**

Cycle 7 has **47% fewer gradient steps** than Cycle 6.

**Implication:** With identical LR and fewer steps, the model will see less total optimization. The hope is that "cleaner signal" (no domain noise) compensates for fewer steps. This is plausible but not guaranteed.

**My assessment:** The "Voice First" strategy is correct, but identical hyperparameters with 47% less data = under-training risk. If voice doesn't hit 0.85, first suspect is **not enough gradient steps**, not pair quality.

---

### Q3: Multi-Teacher Quorum — Good Strategy for Cycle 8?

**Claude's plan:**
```
Prompt → [Kimi + Gemini + GPT-mini] → vote 2/3 → chosen=best, rejected=worst
```

**Analysis:**

| Aspect | Assessment |
|--------|------------|
| **Bias cancellation** | ✅ Good — single-teacher bias (e.g., Gemini being too formal) is cancelled by 2/3 vote |
| **Cost** | ⚠️ 3x API cost per pair — from ~$0.034/200 pairs to ~$0.10/200 pairs |
| **Latency** | ⚠️ 3x generation time — bottleneck for rapid cycle iteration |
| **ORPO suitability** | ❌ Problematic — ORPO needs **clear preference margin** between chosen and rejected. Vote 2/3 produces "acceptable" chosen, not necessarily "strongly preferred" chosen. If all 3 teachers are close in quality, the margin is small → flat ORPO loss. |

**Better approach for Cycle 8:**

**Option A — Specialist teachers (recommended):**
```
voice pairs     → Kimi K2 (Indonesian voice expert)
tool-use pairs  → GPT-4o-mini (instruction following precise)
general pairs   → Gemini 2.5-flash (fast, cheap)
```
Each teacher handles their strength domain. No vote overhead. Lower cost. Higher margin because specialist produces clearly better output than generalist.

**Option B — Best-of-N sampling:**
```
Prompt → Gemini generates 3 candidates → Kimi ranks them 1-3 → chosen=#1, rejected=#3
```
This creates **larger preference margin** (best vs worst) than vote 2/3 (acceptable vs slightly worse).

---

## ANALYSIS — CLAUDE'S PLAN

### Strengths
1. **"Voice First, Zero Domain" is the correct root cause fix.** Removing domain pairs should allow voice representation to dominate.
2. **Pre-flight checklist is thorough** — secrets, dataset, script, balance all verified.
3. **Vast.ai orchestration script is battle-tested** — lessons from Cycles 2-6 applied.
4. **Cost projection realistic** (~$0.10-0.20).

### Weaknesses
1. **Gate targets don't account for 47% fewer gradient steps.** Weighted avg +0.054 with half the steps is optimistic.
2. **No contingency if voice improves but weighted_avg doesn't.** Plan is binary PROMOTE/ROLLBACK. If voice hits 0.85 but weighted_avg is 0.905, what happens?
3. **Multi-teacher quorum described but not costed or scheduled.** Cycle 8 blueprint lacks ETA or budget.

---

## RISKS MISSED BY CLAUDE

| Risk | Severity | Explanation |
|------|----------|-------------|
| **Under-training from 47% fewer steps** | P1 | 63 steps vs 119 steps (Cycle 6). Same LR. May not converge to target gates. |
| **Tool-use may not respond to ORPO** | P1 | Tool trigger consistency is a **format conditioning** problem, not preference learning. 107 ORPO pairs may not fix it. Consider few-shot tool examples in system prompt instead. |
| **No intermediate eval checkpoint** | P2 | If training fails at epoch 1, we only know after full 2 epochs. No save-at-epoch-1 for early eval. |
| **Baseline not fixed before training** | P2 | `baseline_day58.json` still has broken voice reference for Q5. If eval uses same baseline, voice improvement may not be measured correctly. |
| **No held-out voice prompts** | P2 | If training prompts include casual greetings, eval may overfit. Need held-out prompts not in training. |
| **HF upload on training instance** | P3 | HF upload happens before instance deletion. If upload fails, adapter is lost (though local copy exists). |

---

## RECOMMENDATION

### Before GO — Minor Adjustments

#### 1. Consider LR bump if first eval fails (P1)

Don't change hyperparameters now (keep it controlled). But prepare a **Cycle 7b fallback**:
```python
# If Cycle 7 eval voice < 0.80:
learning_rate = 1.2e-6  # 2x
epochs = 3              # +1 epoch
# Re-run with same dataset
```

#### 2. Add epoch-1 checkpoint eval (P2)

If `train_simpo_standard.py` supports `save_strategy="epoch"`, eval after epoch 1:
```bash
# After epoch 1 completes:
ollama create migancore:0.7-ep1 -f Modelfile_cycle7_ep1
docker compose exec -T api python /app/eval/run_identity_eval.py \
  --mode eval --model migancore:0.7-ep1
```
This catches under-training early without waiting for epoch 2.

#### 3. Tool-use backup plan (P1)

If tool-use gate fails again, ORPO is not the right fix. Instead:
- Add few-shot tool examples to `SOUL.md` system prompt (no training needed)
- Or use tool-call fine-tuning with explicit JSON format pairs

#### 4. Multi-teacher for Cycle 8 — Use specialist, not quorum (P2)

Revised Cycle 8 blueprint:
```
voice     → Kimi K2 (Indonesian register expert)
tool-use  → GPT-4o-mini (JSON format precise)  
general   → Gemini 2.5-flash (fast, cheap baseline)
```

---

### Final Verdict on GO

**GO with current plan**, but with these mental models:

| Gate | Probability of Pass | Fallback if Fail |
|------|---------------------|------------------|
| voice ≥ 0.85 | **65%** | Cycle 7b: LR 2x, epochs 3 |
| tool-use ≥ 0.85 | **45%** | Add few-shot examples to system prompt |
| weighted_avg ≥ 0.92 | **50%** | Lower gate to 0.90 if voice passes |
| creative ≥ 0.80 | **75%** | Add 20 more creative pairs |

**If voice passes but weighted_avg doesn't:** Consider CONDITIONAL PROMOTE — voice is the user-facing metric that matters most.

---

*Kimi Review complete. Awaiting Codex QA or Claude execution.*
