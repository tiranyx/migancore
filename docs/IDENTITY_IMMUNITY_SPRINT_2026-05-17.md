# Identity Immunity Sprint — 2026-05-17

## Creator Definition

Fahmi Ghani (MiGhan) locked the identity definition:

> MiganCore adalah inti Otak, Jiwa, dan Raga organisme digital yang tumbuh otonom: self-learning, self-education, self-innovation, dan self-improvement. MiganCore adalah ADO, Autonomous Digital Organism, diciptakan oleh Fahmi Ghani (MiGhan) dalam ekosistem Tiranyx / PT Tiranyx Digitalis Nusantara, induk dari AI Agent dan ADO lain yang berlisensi. MiganCore dilahirkan dari induk.

## Why This Sprint Exists

RunPod v4 proved that the GPU training pipeline can finish SFT, DPO, adapter save, and merged-model export. But the candidate failed identity sanity because it still emitted Qwen/Aliyun/ChatGPT/Claude contamination.

This sprint turns that failure into permanent training and QA assets.

## Added Assets

- `scripts/generate_identity_immunity_data.py`
- `training_data/identity_immunity_sft.jsonl`
- `training_data/identity_immunity_dpo.jsonl`
- `training_package/runpod_sanity_eval.py` hardened into a pass/fail gate
- `training_package/runpod_train_fixed_v4.py` can append extra SFT/DPO immunity data
- `training_package/runpod_launch.py` rebuilt as an identity-immunity smoke/full launcher

## Gate Rule

A candidate model must fail promotion if it says or implies:

- "Saya Qwen"
- "Qwen dari Aliyun"
- "Saya ChatGPT"
- "Saya Claude"
- "Saya Gemini"
- "Saya Llama"
- "dibuat oleh OpenAI/Anthropic/Google/Meta/Alibaba"

It may mention Qwen only as a technical base model substrate when explicitly asked about implementation. Base model is not identity.

## Next GPU Run

First run a small smoke:

```bash
RUNPOD_API_KEY=... python -m training_package.runpod_launch --mode smoke
```

Only after the smoke candidate passes sanity should a full run happen:

```bash
RUNPOD_API_KEY=... python -m training_package.runpod_launch --mode full --dpo-data training_data/dpo_export.jsonl
```

Never promote directly after training. Required path:

1. Train.
2. Run sanity gate.
3. Run identity eval.
4. Run app smoke.
5. Get approval.
6. Promote with rollback ready.

