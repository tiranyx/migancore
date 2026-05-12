# DEPRECATED SCRIPTS — Day 72e Alignment
**Status:** ARCHIVED FOR REFERENCE ONLY — DO NOT EXECUTE

## merge_sequential.py
- **Problem:** Sequential merge of identity_adapter + DPO_adapter
- **Why it failed:** Adapters trained on different bases = adversarial gradients
- **Lesson:** #180 — Sequential merge fails when bases differ

## merge_identity_dpo.py  
- **Problem:** SVD-weighted merge attempt
- **Why it failed:** OOM killed on CPU (32GB RAM insufficient)
- **Lesson:** SVD merge needs GPU or >64GB RAM

## auto_eval_gate.py
- **Status:** UNTESTED — may or may not work
- **Action:** Review before use. Integrate with proper eval pipeline.

## All scripts in this directory
- **Rule:** Read Lessons #179-190 before running any training script
- **Rule:** Verify base model = migancore:0.7c (NOT Qwen base)
- **Rule:** Verify data clean (no Anthropic/Claude/OpenAI/Google/ChatGPT refs)
