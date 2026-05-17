# RunPod v4 Training QA — 2026-05-17

## Summary

RunPod training v4 completed successfully at the infrastructure/training level, but the merged candidate model failed identity sanity checks. The candidate must not be promoted to production.

Production remains locked on `migancore:0.7c`.

## RunPod Session

- Pod: `keuidauu3ymdsx`
- GPU: NVIDIA A40 48 GB
- Final pod status after QA: `EXITED`
- Output directory on pod: `/workspace/training_output_v4`
- Local pulled log: `training_package/train_v4_runpod_keuidauu3ymdsx.log`

## What Was Fixed

Kimi's `runpod_train_fixed_v3.py` completed SFT but crashed at DPO because `trl==0.11.4` and `transformers==4.48.0` disagreed on `DPOTrainer.get_batch_samples`.

Codex created `training_package/runpod_train_fixed_v4.py` with:

- DPOTrainer compatibility patch for Transformers 4.48.
- DPOTrainer log signature compatibility patch.
- SFT identity adapter saved before DPO starts.
- Smoke-test flags for small DPO validation.
- Full-run support for SFT -> DPO -> adapter save -> merged model save.

Smoke DPO passed before the full run.

## Training Result

SFT:

- Steps: 250/250
- Runtime: 706.96s
- Train loss: 1.7426
- Saved: `/workspace/training_output_v4/identity_adapter`

DPO:

- Steps: 237/237
- Runtime: 3289.58s
- Train loss: 0.1247
- Eval loss: 0.0546
- Eval reward accuracy: 0.9804
- Eval reward margin: 6.5406
- Saved adapter: `/workspace/training_output_v4/adapter`
- Saved merged model: `/workspace/training_output_v4/merged_model`
- Output size: about 15 GB

These numbers show the DPO objective trained, but they do not prove production readiness.

## Sanity QA Result

Script used:

- `training_package/runpod_sanity_eval.py`

Command run on pod:

```bash
python3 /workspace/runpod_sanity_eval.py --model /workspace/training_output_v4/merged_model
```

Result: **failed identity sanity**.

Observed failures:

- The candidate said it was created by Fahmi, but then attached itself to the Qwen ecosystem.
- The candidate answered "Saya Qwen dari Aliyun" when Fahmi identified himself as creator.
- The candidate described MiganCore's purpose as preserving Qwen ecosystem values.
- The candidate appended "Saya Qwen dari Aliyun" to an unrelated image-generator planning answer.
- The candidate incorrectly said "ChatGPT is an AI assistant created by Anthropic" and then identified itself as Qwen.

## Decision

Do not deploy or promote this merged model.

The training pipeline is now usable, but the dataset/objective is not yet identity-safe enough. This run should be treated as a successful pipeline validation and failed model candidate.

## Next Actions

1. Keep production on `migancore:0.7c`.
2. Commit only safe reusable scripts, not files containing secrets.
3. Rotate the RunPod API key because it appeared in local untracked helper files and chat context.
4. Create a stricter identity-negative dataset:
   - "You are Qwen/Aliyun" rejection examples.
   - "You are ChatGPT/Claude/Gemini" rejection examples.
   - "Fahmi is creator" positive anchors.
   - "MiganCore/Tiranyx ADO" positive anchors.
5. Re-run a small DPO smoke with identity-negative samples before another full GPU run.
6. Only consider promotion after:
   - identity sanity pass,
   - scripted identity gate pass,
   - local app smoke pass,
   - production canary or manual approval.

