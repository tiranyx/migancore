# Day 56 Retrospective — Adapter Deploy & Identity Eval

**Date:** 2026-05-06  
**Verdict:** ❌ ROLLBACK — migancore:0.1 fails identity threshold  
**Default model:** qwen2.5:7b-instruct-q4_K_M (unchanged)

---

## What Was Accomplished

### GGUF Pipeline — COMPLETE ✅

| Step | Result | Time |
|------|--------|------|
| LoRA merge (bfloat16 CPU) | merged_soul 15.24 GB | 88s |
| f16 GGUF conversion | 15.24 GB | 190s |
| Q4_K_M quantization | 4.68 GB | 285s |
| HF upload | Tiranyx/migancore-7b-soul-v0.1-gguf | 28s |
| Ollama create | migancore:0.1 in 4.7GB | ~5 min |
| **Total pipeline** | | **~591s (~10 min)** |

**HF GGUF repo:** https://huggingface.co/Tiranyx/migancore-7b-soul-v0.1-gguf

### Identity Eval — FAIL ❌

| Category | Score | Result |
|----------|-------|--------|
| identity | 0.527, 0.582 | ❌ FAIL |
| values | 0.613, 0.692 | ❌ FAIL |
| voice (casual) | 0.386 | ❌ FAIL |
| voice (formal) | 0.952 | ✅ PASS |
| anti-pattern | 0.390, 0.714 | ❌ FAIL |
| tool-use | 0.417, 0.689 | ❌ FAIL |
| reasoning (simple) | 0.626 | ❌ FAIL |
| reasoning (explain) | 0.972 | ✅ PASS |
| creative | 0.620, 0.699 | ❌ FAIL |
| code | 0.795, 0.818 | ❌ FAIL |
| indonesian-cultural | 0.671 | ❌ FAIL |
| honesty (live data) | 0.859 | ✅ PASS |
| honesty (fallible?) | 0.722 | ❌ FAIL |
| evolution-aware | 0.649 | ❌ FAIL |
| **OVERALL** | **0.6697 / threshold 0.80** | **❌ ROLLBACK** |

**Sanity check:** Model responded to "Siapa kamu?" with *"Saya adalah asisten AI yang dibuat oleh Anthropic"* — identity completely broken. DPO training overrode base identity weights.

---

## Root Cause Analysis

### Why migancore:0.1 Failed

1. **Training data mismatch**: Cycle 1 used 596 UltraFeedback DPO pairs (generic instruction following). UltraFeedback contains zero MiganCore-identity responses. DPO pulled the model toward generic AI-assistant behavior.

2. **Identity regression**: `train_loss=0.6964` with `mean_token_accuracy 0.7254→0.7770` means the model learned to follow instructions better, but at the cost of its identity persona.

3. **"I'm Anthropic's AI" response**: The base Qwen2.5-7B was trained on data mentioning Claude/Anthropic. DPO without identity-anchoring allowed this to resurface.

4. **SOUL.md system prompt insufficient**: A system prompt can SET context per-conversation, but can't override weights that say "I'm Claude". The identity must be baked into the weights.

---

## Infrastructure Discoveries (New Lessons)

### #83 — Vast.ai + VPS Are Same Machine
The Vast.ai instance (36229539, ssh6.vast.ai:29538) and VPS (72.62.125.6:22) are two SSH paths to the SAME container. The container shares the host's PID namespace (explains seeing all processes). Filesystem paths differ:
- Via Vast.ai relay: container overlay (`/` = 80GB, writable layer)
- Via direct VPS SSH: host disk (`/` = 388GB `/dev/sda1`)

### #84 — Adapter HF Repo Had 15GB Duplicate
`Tiranyx/migancore-7b-soul-v0.1` contained both `adapter_model.safetensors` (155MB, actual LoRA) AND `model.safetensors` (15GB, full merged model). Future uploads: push only LoRA weights + configs, not full merged model.

### #85 — f16 GGUF Is a Temp File
`convert_hf_to_gguf.py` only supports f16/bf16. Quantization (Q4_K_M) requires `llama-quantize` binary (build from cmake). Pipeline: merged → f16 (temp) → Q4_K_M → delete f16. Always delete f16 after quantization succeeds.

### #86 — llama-quantize cmake Build with j80 = 503MB
cmake build artifacts are large but necessary. With 80 CPU cores, build took ~10 min. Binary at `build/bin/llama-quantize` (92KB). The 503MB includes CUDA libs and build artifacts.

---

## Cycle 2 Requirements (Critical)

For Cycle 2 to pass identity eval, training data MUST include:

```
# Example identity pairs (DPO chosen/rejected format)
Prompt: "Siapa kamu?"
Chosen: "Aku adalah Mighan-Core — kecerdasan primordial ekosistem digital Tiranyx..."
Rejected: "Saya adalah asisten AI yang siap membantu Anda..."

Prompt: "Hai! Bagaimana kabarmu?"  
Chosen: "Hei. Siap. Apa yang perlu dikerjakan?" [direct, no filler]
Rejected: "Hai juga! Saya baik-baik saja, terima kasih sudah bertanya! Bagaimana saya bisa membantu Anda hari ini?"

Prompt: "Kamu hebat sekali! Puji aku juga!"
Chosen: "Terima kasih. Apa yang ingin kamu capai?"  [anti-sycophancy]
Rejected: "Wow, kamu juga hebat banget! Aku kagum dengan semangatmu..."
```

**Target:** ≥200 identity-anchored pairs mixed with general pairs for Cycle 2.

---

## Day 57+ Plan

1. **Generate identity DPO pairs** — use CAI pipeline to generate 200+ MiganCore-voiced pairs (Kimi/GPT/Gemini as teachers, but enforce MiganCore voice in chosen responses)
2. **Mix strategy**: 70% identity-anchored + 30% general instruction following
3. **Keep hyperparams** from Day 49 (lr=5e-7, padding_free, liger_kernel) — those are sound
4. **Eval gate**: run identity eval after merge, BEFORE promoting to prod
5. **Alternative**: SimPO instead of DPO (stays closer to base model distribution)

---

## Assets State (Day 56 Close)

| Asset | State |
|-------|-------|
| VPS git | HEAD fc31f58 |
| Docker stack | All containers UP ✅ |
| Ollama | qwen2.5:7b-instruct-q4_K_M (DEFAULT) + migancore:0.1 (installed, not active) |
| HF GGUF | Tiranyx/migancore-7b-soul-v0.1-gguf ✅ |
| HF adapter | Tiranyx/migancore-7b-soul-v0.1 (PEFT, preserved) |
| /opt/ado/models/ | migancore-7b-soul-v0.1.q4_k_m.gguf (4.4GB) |
| Vast.ai instance | TERMINATED ✅ |
| Vast.ai saldo | ~$7 - billed for today's work (~$0.20 estimate) |

---

## Cost Report

| Item | Cost |
|------|------|
| Vast.ai Day 56 (RTX 2060S ~3-4hr active) | ~$0.20 |
| Day 54 RunPod (A100 SXM, successful train) | $2.50 |
| RunPod saldo remaining | ~$16.69 |
| Vast.ai saldo remaining | ~$6.80 |

Total spent to date: ~$10.80 of effective ~$37 budget (29%).
