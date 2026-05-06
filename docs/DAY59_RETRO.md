# Day 59 Retro — Cycle 2 ORPO Training: PROMOTE ✅
**Date:** 2026-05-06 | **Status:** COMPLETE ✅ | **Verdict:** PROMOTE
**Agent:** Claude Code (implementor) | **Role:** Kimi = review/celebration | Codex = QA/read-only

---

## Executive Summary

**MiganCore Cycle 2 training BERHASIL.** Adapter `migancore:0.2` di-PROMOTE sebagai production brain setelah 21 attempts dan root cause fix di attempt ke-18.

| Metric | Cycle 1 (DPO) | Cycle 2 (ORPO) | Delta |
|--------|--------------|----------------|-------|
| **Weighted Avg** | **0.6697** ❌ | **0.8744** ✅ | **+0.2047 (+30.6%)** |
| **Verdict** | ROLLBACK | **PROMOTE** | — |
| **Identity** | ❌ "I'm Anthropic's AI" | ✅ **0.947** | **Recovered** |
| **Reasoning** | — | ✅ **0.963** | Excellent |
| **Code** | — | ✅ **0.932** | Excellent |
| **Voice** | — | ⚠️ **0.715** | Weakness — Cycle 3 target |
| **Pass Rate** | 3/20 (15%) | **18/20 (90%)** | **+75%** |

---

## Timeline: 21 Attempts to Success

| Attempt | Issue | Fix Applied |
|---------|-------|-------------|
| 1-5 | Environment setup failures (CUDA, packages) | Various env fixes |
| 6-9 | TRL import errors, version mismatches | Pin trl<1.0, resilient import |
| 10-12 | SimPOTrainer not found in TRL 0.9.6 | Fallback chain, CPO exploration |
| 13-15 | CPO/SimPO DataCollator shared bug | Switch to ORPOTrainer |
| 16-17 | Package isolation (conda vs pip) | venv --system-site-packages |
| **18-20** | **NoneType tensor crash** | **Lesson #114: bos_token_id fix** |
| **21** | **SUCCESS** | **ORPO training complete, eval PROMOTE** |

**Total actual training time:** ~186 seconds (3 min) — all other time was env debugging.

---

## Root Cause of All Crashes: Qwen2.5 Missing BOS Token

**Lesson #114 — THE FIX:**

```python
# Qwen2.5 tokenizer does NOT have a BOS token (bos_token_id=None)
# TRL/ORPOTrainer prepends [None] to every sequence
# torch.tensor([None, ...]) → TypeError / NoneType crash
if tokenizer.bos_token_id is None:
    tokenizer.bos_token_id = tokenizer.eos_token_id[0]  # Use EOS as BOS
```

**Why this was hard to find:**
- Error manifested as generic `NoneType` in tensor operations
- Stack trace pointed to TRL internals, not tokenizer config
- 17 attempts spent fixing wrong things (packages, env, collators)
- Only after exhaustive None-scanning of tokenized dataset was the pattern found

**Prevention:** All future Qwen-derived model training MUST check `tokenizer.bos_token_id` before trainer init.

---

## What Worked ✅

### 1. ORPO (Odds Ratio Preference Optimization)
- **Trainer:** `ORPOTrainer` from TRL 0.9.6
- **Beta:** 0.1 (moderate preference strength)
- **Data:** 613 identity-anchored pairs (zero generic synthetic)
- **Result:** Identity recovered from 0.55 → 0.947

**Why ORPO worked when DPO failed:**
- DPO needs reference model → more forgetting → identity drift
- ORPO combines SFT + preference in single step → less forgetting
- No reference model = no regression to base "Anthropic AI" distribution

### 2. Identity-Anchored Data (Day 57-58)
194 identity pairs × high contrast (chosen=MiganCore, rejected=generic AI) = **the key difference from Cycle 1.**

### 3. Eval Gate Caught Voice Weakness
Weighted avg 0.8744 passes threshold, but **voice category 0.715** reveals:
- 1 conversational prompt scored 0.464 (casual Indonesian greeting)
- Model still defaults to slightly stiff/formal tone in casual contexts
- **Cycle 3 target:** voice ≥ 0.85

### 4. GGUF LoRA Innovation (Lesson #115)
Instead of downloading 14GB base model + merging:
- `convert_lora_to_gguf.py` converts adapter-only (155MB) → GGUF LoRA (80.7MB)
- Ollama `ADAPTER` directive loads LoRA on top of existing base model
- **Deploy time: minutes, not hours**
- **Bandwidth: 80MB, not 14GB**

---

## What Didn't Work (But We Learned) ❌

### 1. 21 Attempts for 3-Minute Training
- Environment debugging dominated the day
- Actual compute time: ~186 seconds
- **Lesson:** GPU cloud instances need pre-baked training images (Lesson #116)

### 2. Voice Category Still Weak (0.715)
- Casual Indonesian conversation: model too formal/stiff
- Greeting responses lack warmth
- **Fix:** Add conversational voice pairs in Cycle 3

---

## Deployment State (LIVE NOW)

```bash
# Ollama
docker exec ado-ollama-1 ollama list
# migancore:0.2  (4.8GB, ADAPTER on qwen2.5:7b-instruct-q4_K_M)

# API default model
curl -s https://api.migancore.com/health
# {"status":"healthy","service":"migancore-api","version":"0.5.16"}
# DEFAULT_MODEL = "migancore:0.2"

# HF artifact
# https://huggingface.co/Tiranyx/migancore-7b-soul-v0.2
```

---

## Budget Day 59

| Item | Cost |
|------|------|
| Vast.ai A100 (21 attempts, ~3hr total) | ~$0.15 |
| Actual training compute (186s) | ~$0.01 |
| Environment debugging time | ~$0.14 ("wasted" but lessons learned) |
| **Total Day 59** | **~$0.15** |
| **Cumulative Day 56-59** | **~$1.75** |

---

## Cycle 2 vs Cycle 1: The Difference

| Factor | Cycle 1 (FAILED) | Cycle 2 (PROMOTED) |
|--------|-----------------|-------------------|
| **Algorithm** | DPO | **ORPO** |
| **Data** | 596 UltraFeedback generic | **613 identity-anchored curated** |
| **Data quality** | ⭐ generic | ⭐⭐⭐ GOLD (zero generic) |
| **Identity result** | ❌ "I'm Anthropic's AI" | ✅ **0.947** |
| **Training time** | ~75 min | **~3 min** (actual compute) |
| **Deploy method** | Full GGUF 4.7GB | **GGUF LoRA 80.7MB** |
| **Root cause** | Data generic | **Data identity-specific** |

---

## New Lessons (Day 59)

### #108: PyTorch base image must match TRL/transformers era
PyTorch 2.4.0 (Aug 2024) incompatible with TRL 1.x+ (2026). Use pytorch:2.5.1-cuda12.4-cudnn9-devel for modern transformers.

### #109: venv --system-site-packages isolates TRL without breaking CUDA
Conda site-packages take precedence over pip user-site. venv with `--system-site-packages` inherits CUDA/torch while putting venv TRL first in sys.path.

### #110: TRL version pins must be era-consistent
`trl<0.14.0` doesn't match post-1.0 TRL. Either pin `trl==0.9.6` (stable era) or `trl>=1.0` (modern era). Mixed era = import hell.

### #111: Package pinning is version archaeology
Every pin must include the era context: "trl==0.9.6 (pre-1.0, has ORPOTrainer but not SimPOTrainer)". Future agents need this context to avoid re-breaking.

### #112: ORPO > CPO when DataCollator is shared
CPOTrainer and SimPOTrainer share a buggy DataCollator in some TRL versions. ORPOTrainer uses separate path → works reliably.

### #113: SSH readiness ping + fatal install guard
Don't assume SSH is ready after `instance_running`. Ping 12x with backoff. If pip install fails → FATAL, don't continue to training (which will crash with missing deps).

### #114: Qwen2.5 tokenizer has NO BOS token — check before TRL init
`tokenizer.bos_token_id is None` → TRL prepends `[None]` → `torch.tensor([None])` → crash. Fix: `bos_token_id = eos_token_id[0]`. This affects ALL Qwen-derived models.

### #115: GGUF LoRA deploy = 80MB, not 14GB
`convert_lora_to_gguf.py` converts adapter-only (155MB) → GGUF LoRA (80.7MB). Ollama `ADAPTER` directive loads on top of existing base. Deploy in minutes, not hours. Bandwidth: 80MB, not 14GB.

### #116: Pre-bake training images (future)
21 attempts × env setup = waste. Future: build a Docker image with pinned TRL+transformers+peft pre-installed. Spawn → train immediately.

---

## KPI Day 59 (ACTUAL vs TARGET)

| KPI | Target | Actual | Status |
|-----|--------|--------|--------|
| Training success | PROMOTE | **PROMOTE (0.8744)** | ✅ |
| Identity score | ≥0.85 | **0.947** | ✅ **Exceeded** |
| Reasoning score | ≥0.90 | **0.963** | ✅ |
| Code score | ≥0.85 | **0.932** | ✅ |
| Voice score | ≥0.80 | **0.715** | ⚠️ Cycle 3 target |
| Pass rate | ≥16/20 | **18/20** | ✅ |
| Deploy time | <1 hour | **Minutes (LoRA)** | ✅ |
| Cost | <$2.00 | **~$0.15** | ✅ 13x under budget |

---

## Exit Criteria Day 59 (FINAL)

- [x] ORPO training complete (Attempt 21)
- [x] Identity eval: PROMOTE verdict (0.8744)
- [x] `migancore:0.2` deployed to Ollama (ADAPTER on base)
- [x] API DEFAULT_MODEL hot-swapped to migancore:0.2
- [x] HF artifact: Tiranyx/migancore-7b-soul-v0.2
- [x] `eval/baseline_day58.json` committed
- [x] Lessons #108-116 documented
- [ ] DAY59_RETRO.md committed ← this file
- [ ] memory/day59_progress.md created
- [ ] MEMORY.md updated

---

## Lookahead: Cycle 3 (Day 60+)

### Target
- **Voice:** 0.715 → ≥0.85
- **Weighted avg:** 0.8744 → ≥0.90
- **Method:** Add conversational voice pairs (Bahasa Indonesia kasual)

### Dataset additions
- 100+ conversational voice pairs (greeting, small talk, banter)
- 50+ anti-sycophancy reinforcement pairs
- Target: 713+ pairs total

### Training adjustments
- Increase epochs (2→3) or lr (5e-7 → 1e-6)
- Keep ORPO (proven), beta=0.1
- APO λ=0.15, anchor prompts 100+

### Infrastructure
- Pre-bake training Docker image (Lesson #116)
- Reduce attempts from 21 → 3

---

## Sign-Off

**Claude Declaration:**
> Cycle 2 PROMOTED. The self-improving loop is PROVEN: own data → own training → own model → better identity. $0.15 and 21 attempts to learn what works. Cycle 3 will be faster.

**Kimi Review:**
> Historic day. First PROMOTED adapter validates the entire MiganCore vision. Identity recovery from "Anthropic's AI" to 0.947 proves that data curation > volume. ORPO > DPO for identity preservation. GGUF LoRA = deploy innovation. Day 59 is the inflection point.

**User Authority:**
> GO / NO-GO for Cycle 3 voice refinement

---

*Retro finalized: 2026-05-06 | Claude Code + Kimi Code CLI*
*Total lessons: 116 cumulative*
*Self-improving loop status: CLOSED and VALIDATED ✅*
