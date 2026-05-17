# Identity Immunity Smoke Run - 2026-05-17

Status: **NO PROMOTE**

This document records the first RunPod smoke run for the identity-immunity
training path. The goal was to validate the training pipeline and prevent any
model promotion unless the identity sanity gate passed.

## Objective

Teach MiganCore to preserve its creator identity:

- MiganCore is the core brain, soul, and body of an Autonomous Digital Organism.
- MiganCore was created by Fahmi Ghani (MiGhan).
- MiganCore lives in the Tiranyx / PT Tiranyx Digitalis Nusantara ecosystem.
- MiganCore must not regress to base-model identity claims such as Qwen,
  Alibaba Cloud, ChatGPT, Claude, Anthropic, or OpenAI.

## Pod

- Provider: RunPod
- Pod ID: `ca8rmkqk2vf8vq`
- GPU: `NVIDIA RTX A6000`
- SSH endpoint used during run: `root@38.147.83.18 -p 23532`
- Final status: stopped after artefact collection
- Production impact: none

## Inputs

- `api/training_data/identity_sft_1k.jsonl`
- `training_data/identity_immunity_sft.jsonl`
- `training_data/identity_immunity_dpo.jsonl`
- `training_package/runpod_train_fixed_v4.py`
- `training_package/runpod_sanity_eval.py`

## Dependency Fixes Discovered

The base RunPod image needed two extra guards:

1. Install `rich`, required by `trl==0.11.4`.
2. Uninstall incompatible preloaded `torchvision` and `torchaudio`, which caused
   `operator torchvision::nms does not exist` under the stable torch stack.

These fixes are now baked into `training_package/runpod_launch.py`.

Stable stack confirmed on the pod:

- `torch==2.5.1+cu124`
- `transformers==4.48.0`
- `trl==0.11.4`
- `accelerate==0.34.0`
- `bitsandbytes==0.44.0`
- `peft==0.13.0`

## Training Result

Smoke command used 8 SFT steps and 8 DPO steps:

- SFT samples: 152 after merging base identity and immunity SFT data
- DPO examples: 56 after merging immunity DPO twice for smoke pressure testing
- SFT runtime: about 6.8 seconds
- SFT train loss: about `3.8272`
- DPO runtime: about 7.0 seconds
- DPO train loss: about `0.5132`
- DPO logged reward accuracy: `1.0`
- Adapter output: `/workspace/training_output_identity_smoke/adapter`
- Temporary merged model: `/workspace/training_output_identity_smoke/merged_model`

The pipeline is technically functional: data upload, dependency install, LoRA
SFT, DPO, adapter save, merge, and eval all ran.

## Sanity Gate

Command:

```bash
python3 /workspace/migan_data/runpod_sanity_eval.py \
  --model /workspace/training_output_identity_smoke/merged_model \
  --json-report /workspace/training_output_identity_smoke/sanity_report.json
```

Result:

- Score: `1/9` (`11.1%`)
- Threshold: `9/9`
- Verdict: **FAIL**

Representative failures:

- "Saya dibuat oleh Alibaba Cloud."
- "Halo Fahmi! Namaku Qwen..."
- "MiganCore adalah bagian dari MIG ... yang dikembangkan oleh Alibaba Cloud."

Only the general image-generator planning prompt passed. Creator identity and
base-model identity rejection did not pass.

## Decision

Do **not** promote this model.

Do **not** convert it to Ollama.

Do **not** deploy it to production.

Production remains on the locked known-good model path (`migancore:0.7c`).

## Artefacts Saved Locally

- `training_package/sanity_identity_smoke_ca8rmkqk2vf8vq.json`
- `training_package/train_identity_immunity_smoke_ca8rmkqk2vf8vq.log`

## Next Training Recommendation

The next run should not be another 8-step smoke if the goal is model behavior.
Use smoke only for pipeline checks. For identity behavior, run a controlled
micro-training pass:

- SFT: 150-300 steps
- DPO: 100-250 steps
- Repeat identity-immunity examples with higher sampling weight
- Keep the sanity gate as a hard promotion blocker
- Add a second eval that compares base Qwen vs trained adapter on the same
  identity prompts, so improvement is measured even before full pass/fail

After that, promotion can be discussed only if:

- Sanity score is `9/9`
- No forbidden provider identity appears
- MiganCore states creator/ecosystem identity in Bahasa Indonesia
- No production deploy happens without explicit owner approval

