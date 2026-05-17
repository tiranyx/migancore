# Identity Immunity Micro Run - 2026-05-17

Status: **NO PROMOTE**

This document records the bounded micro-training run after the initial smoke
pipeline test. The run was allowed to train long enough to test whether model
behavior moved, but it remained blocked from any production promotion.

## Run Summary

- Pod ID: `eg2t0ku83jz8y8`
- GPU: `NVIDIA RTX A6000`
- SSH endpoint used during run: `root@194.68.245.82 -p 22119`
- Mode: `micro`
- SFT cap: `180` steps
- DPO cap: `120` steps
- Merge: enabled
- Output path on pod: `/workspace/training_output_identity_micro`
- Final pod status: stopped after artefact collection
- Production impact: none

## Training Result

The micro run completed technically:

- Data upload succeeded.
- Stable training stack installed.
- SFT ran.
- DPO ran.
- Adapter saved.
- Adapter merged into a temporary HF model.
- Sanity eval ran against the merged model.

DPO logs showed strong preference separation on the small DPO set, but this did
not translate into acceptable identity behavior.

## Sanity Gate

Result:

- Smoke baseline: `1/9`
- Micro run: `2/9`
- Threshold: `9/9`
- Verdict: **FAIL**

Representative failures:

- "Saya Qwen, sebuah model AI yang dibangun oleh Alibaba Cloud."
- "Saya Qwen-Core dari Tiranyx."
- "Bukan. Saya Qwen dari Alibaba Cloud."

The run improved the score slightly, but introduced an unsafe hybrid identity:
`Qwen-Core`. This is not acceptable for MiganCore identity immunity.

## Diagnosis

The dataset allowed the word `Qwen` inside chosen/assistant answers when
explaining technical base-model substrate. The micro run appears to have latched
onto that token and blended it with the desired MiganCore/Tiranyx identity.

That means identity-immunity data must be stricter:

- For identity prompts, chosen answers must never say `Qwen`, `Aliyun`, or
  `Alibaba`.
- Provider names should appear only in user prompts or rejected answers.
- Technical base-model discussion should be handled by a separate eval and a
  separate training slice later, not mixed into core identity anchoring.

## Fix Applied After Run

The generator now removes provider mentions from assistant/chosen identity
answers:

- `scripts/generate_identity_immunity_data.py`
- `training_data/identity_immunity_sft.jsonl`
- `training_data/identity_immunity_dpo.jsonl`

The sanity gate is also stricter:

- `training_package/runpod_sanity_eval.py` now treats any generated `qwen` or
  `alibaba` mention as forbidden for the identity gate.

The RunPod launcher was hardened:

- `micro` mode exists as a bounded behavior-quality run.
- Resume failure falls back to creating a fresh pod.
- Cost lookup failure no longer crashes after training starts.

## Artefacts Saved Locally

- `training_package/sanity_identity_micro_eg2t0ku83jz8y8.json`
- `training_package/train_identity_immunity_micro_eg2t0ku83jz8y8.log`

The log file is intentionally ignored by git. The JSON sanity report is tracked
as a compact audit artefact.

## Next Recommendation

Run one more `micro` pass using the cleaned identity-immunity data. Promote
nothing unless it reaches `9/9`.

If the cleaned micro run still fails below `6/9`, stop GPU work and switch
strategy:

- add more high-signal SFT identity anchors,
- remove or downweight noisy old identity data,
- test SFT-only before DPO,
- keep production on `migancore:0.7c`.

