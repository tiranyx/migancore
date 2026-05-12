# MiganCore Identity Collapse Incident Report
**Date:** 2026-05-12
**Status:** RESOLVED — Production reverted to `migancore:0.7c`
**Severity:** CRITICAL — Total identity loss in production model

---

## 1. Incident Summary

`migancore:0.8` (deployed 2026-05-11) suffered **complete identity collapse**. When asked "Siapa kamu?", the model responded with identities from competing AI companies instead of Mighan-Core:

| Model | Response to "Siapa kamu?" | Status |
|---|---|---|
| `migancore:0.7c` | "Saya Mighan-Core, asisten AI yang dikembangkan oleh PT Tiranyx Digitalis Nusantara" | ✅ Production |
| `migancore:0.8` (original) | "Saya penulis teknologi..." | ❌ Broken |
| `migancore:0.8-fixed` (seq merge) | "Saya ChatGPT, asisten AI yang dibuat oleh OpenAI" | ❌ Broken |
| `migancore:0.8-identity` (id-only) | "Saya primanya Claude 2, asisten AI yang dibangun oleh Anthropic" | ❌ Contaminated |

---

## 2. Root Cause Analysis

### 2.1 Primary Cause: Identity Signal Drowning
`migancore:0.8` DPO training started from **base Qwen** (not from identity checkpoint) with:
- **951 DPO utility pairs** (99.5%)
- **5 identity SFT pairs** (0.5%)

The 5 identity pairs were statistically drowned by 951 utility pairs. `training_report.json` confirmed `"identity_pairs": 0`.

### 2.2 Secondary Cause: Sequential Merge Failure
Attempted fix: sequentially merge `identity_adapter_v0.4` (r=32, 200 SFT pairs) then `migancore_dpo_v1` adapter (r=16, 951 DPO pairs). 

**Why it failed:** The DPO adapter was trained on base Qwen, not on the identity-merged checkpoint. Its LoRA weights `B*A` were computed relative to base Qwen weights. When loaded on top of the identity-merged model, the strong utility gradients pulled representations back toward generic assistant space, overriding identity.

### 2.3 Tertiary Cause: Training Data Contamination
The archived `identity_adapter_v0.4` training data (`identity_sft_200.jsonl`) contains **Anthropic/Claude references** baked into the dataset. When converted and tested without DPO (`0.8-identity`), the model leaked these references:
> "Jangan jawab 'Saya adalah asisten AI milik Anthropic.' ... Kamu primanya Claude 2"

This means **the Day 0-39 identity foundation itself is contaminated** and must be rebuilt with clean data.

### 2.4 Why 0.7c Works
`migancore:0.7c` was produced during Cycles 4-7 (Day 49-71) using a different training approach that successfully embedded identity. When tested **with the system prompt** (which the API always injects), 0.7c correctly follows instructions and identifies as Mighan-Core. Without system prompt, it falls back to "Qwen by Alibaba" (base model identity), but this is acceptable since the API always injects SOUL.md.

---

## 3. Recovery Actions Taken

1. **Hard revert API default** from `migancore:0.8` → `migancore:0.7c`
2. **Updated all hardcoded references** across:
   - `/opt/ado/api/config.py` — `DEFAULT_MODEL`
   - `/opt/ado/docker-compose.yml` — `DEFAULT_MODEL`, `OLLAMA_DEFAULT_MODEL`
   - `/opt/ado/config/agents.json` — both agent `model_version`
   - `/opt/ado/api/models/agent.py` — DB default
   - `/opt/ado/api/routers/agents.py` — schema default
   - `/opt/ado/api/routers/system.py` — fallback default
   - `/opt/ado/api/scripts/seed_users.py` — seed data
   - `/opt/ado/api/services/distillation_worker.py` — worker default
3. **Rebuilt & restarted** `ado-api-1` Docker container
4. **Removed broken Ollama models:** `0.8`, `0.8-fixed`, `0.8-identity`, `0.4`, `0.4-fixed`, `0.7`, `0.7b`
5. **Cleaned disk:** Removed 45GB+ of broken GGUF/HF artifacts
   - `migancore_0.8_fixed_f16.gguf` (15.2GB)
   - `migancore_0.8_fixed_q4_k_m.gguf` (4.2GB)
   - `merged_identity_v0.4_f16.gguf` (15.2GB)
   - `merged_identity_v0.4_q4_k_m.gguf` (4.7GB)
   - `migancore_0.8_identity_fixed/` HF model (15GB)
   - **Disk: 79% → 66%** (102GB → 136GB free)

---

## 4. Key Findings

| Finding | Implication |
|---|---|
| `merged_identity_v0.4` has Anthropic contamination | Identity training data from Day 0-39 is **not reusable**. Must rebuild from scratch. |
| DPO adapter must be trained from identity checkpoint, not base | Any future DPO must use `0.7c` (or later stable identity model) as base_model, not `Qwen/Qwen2.5-7B-Instruct` |
| System-prompt-following ≠ weight-embedded identity | 0.7c follows system prompt but doesn't "know" identity without it. A robust model should know identity even with system prompt removed. |
| Sequential adapter merge is not a silver bullet | LoRA adapters are relative to their training base. Merging adapters trained on different bases causes unpredictable interference. |

---

## 5. Recommended Next Steps

### Immediate (Sprint 0)
1. **Audit `identity_sft_200.jsonl`** — find and remove all Anthropic/OpenAI/Google/Claude/ChatGPT references
2. **Audit all training datasets** (`dpo_v1`, `identity_sft_200`) for competitor contamination
3. **Verify 0.7c production stability** — monitor API responses for 24-48h

### Short-term (Sprint 1)
4. **Clean identity retrain** — create new `identity_sft_clean_v1.jsonl` with verified-zero-contamination data
5. **Train new identity adapter** from base Qwen using clean data
6. **Test WITHOUT system prompt** — true identity is embedded only when model answers correctly without system prompt injection

### Medium-term (Sprint 2)
7. **DPO retrain from identity checkpoint** — use the new clean identity model as `base_model`, NOT base Qwen
8. **Identity pair ratio minimum 20%** — DPO dataset must contain ≥200 identity pairs alongside utility pairs
9. **Implement identity eval gate** — `run_identity_eval.py` must test both WITH and WITHOUT system prompt

### Long-term
10. **Model versioning policy** — never promote a model to production without passing both:
    - Identity gate (with + without system prompt)
    - Utility eval gate
    - Human review for contamination

---

## 6. Model Inventory (Post-Recovery)

| Model | Status | Location | Notes |
|---|---|---|---|
| `migancore:0.7c` | ✅ Production | Ollama | Follows system prompt correctly |
| `migancore:0.3` | ✅ Fallback | Ollama | Pre-DPO stable |
| `qwen2.5:7b-instruct-q4_K_M` | ✅ Reference | Ollama | Base model |
| `identity_adapter_v0.4` | ❌ Contaminated | `/opt/ado/models/` | Anthropic refs in training data |
| `migancore_dpo_v1` adapter | ❌ Invalid base | `/opt/ado/data/models/` | Trained from base Qwen, not identity ckpt |
| `merged_identity_v0.4` HF | ❌ Contaminated | `/opt/ado/data/ollama/models/` | Will be archived then removed |

---

## 7. Lessons Learned

1. **Training base matters more than merge strategy.** A DPO adapter trained on base Qwen cannot be safely merged onto an identity-merged model.
2. **Data contamination is silent and deadly.** Anthropic references in training data didn't surface until the model was deployed and explicitly asked "Siapa kamu?"
3. **System prompt following is not enough.** A production model must have identity embedded in weights, not just rely on prompt injection.
4. **Disk space is a operational risk.** 100% disk during GGUF conversion caused corruption and delayed recovery.
5. **Always test without system prompt.** The true test of embedded identity is asking "Siapa kamu?" with NO system prompt.
