# FORENSIC ARCHIVE — Day 72c Identity Collapse
**Date:** 2026-05-12
**Status:** CONTAMINATED — DO NOT USE FOR TRAINING
**Incident:** IDENTITY_COLLAPSE_INCIDENT_2026-05-12.md

## Files in this Archive

### identity_adapter_v0.4 (HF model)
- **Status:** CONTAMINATED with Anthropic/Claude references
- **Symptom:** When asked " Siapa kamu?\ model says \Saya primanya Claude 2 asisten AI milik Anthropic\
- **Source:** Day 0-39 training data (identity_sft_200.jsonl) contained competitor data leakage
- **Action:** PURGE from all training pipelines. Do not merge. Do not quantize.

### migancore_0.8_fixed_q4_k_m.gguf (broken)
- **Status:** CORRUPTED during disk-full conversion (all zeros in header)
- **Cause:** Disk 100% full during llama-quantize
- **Action:** Already deleted. This archive documents the failure.

### migancore_0.8_fixed_f16.gguf (valid but useless)
- **Status:** Valid GGUF but model has total identity collapse
- **Symptom:** Claims to be ChatGPT by OpenAI
- **Action:** Already deleted.

## Root Causes
1. identity_sft_200.jsonl poisoned (Anthropic/Claude leakage)
2. DPO trained from base Qwen (not identity checkpoint)
3. Sequential merge of adapters with different bases = adversarial

## Lessons
#179 — Data contamination
#180 — Sequential merge failure
#186 — DPO from base Qwen overwrites identity

## Safe Alternative
Use migancore:0.7c as production baseline.
Future identity training: start from 0.7c, use CLEAN data only.
