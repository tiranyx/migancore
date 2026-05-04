# MiganCore Training Pipeline (Day 32+)

This directory contains scripts for training MiganCore-7B from collected DPO preference pairs.

**Status:** Scripts ready. First run scheduled for Day 32 once DPO pool ≥ 500 pairs.

## Files

- `export_dataset.py` — Export `preference_pairs` table to JSONL (TRL-compatible format)
- `train_simpo.py` — Unsloth + QLoRA + SimPO training loop
- `convert_gguf.py` — Convert trained adapter to GGUF Q4_K_M for Ollama
- `runpod_template.md` — RunPod pod spec + setup commands

## Workflow (Per Original Blueprint Section 6)

```
1. Export:   python export_dataset.py --output dataset_v1.jsonl
                Filters: NULL used_in_training_run_id only
                Mix: 50% distill_* + 30% synthetic_* + 20% cai_pipeline (per DeepSeek-V3 paper)
                Plus: 50 identity-anchor samples (prevent persona drift)

2. Upload to RunPod:
                runpodctl send dataset_v1.jsonl <pod-id>:/workspace/

3. Train (on RunPod RTX 4090):
                python train_simpo.py \
                  --dataset /workspace/dataset_v1.jsonl \
                  --base qwen2.5-7b-instruct \
                  --epochs 2 \
                  --output /workspace/migancore-7b-soul-v0.1
                Cost: ~$5.50 ($0.69/hr × 8hr)

4. Eval gate:
                python ../eval/run_identity_eval.py \
                  --model /workspace/migancore-7b-soul-v0.1
                Pass: cosine sim ≥ 0.85 vs reference

5. Convert to GGUF:
                python convert_gguf.py \
                  --adapter /workspace/migancore-7b-soul-v0.1 \
                  --output migancore-7b-soul-v0.1.Q4_K_M.gguf

6. Push to HF Hub:
                hf upload migancore/migancore-7b-soul-v0.1 \
                  migancore-7b-soul-v0.1.Q4_K_M.gguf

7. Deploy to Ollama (hot-swap):
                ollama pull migancore/migancore-7b-soul-v0.1
                # Update DEFAULT_MODEL env in api .env
                # Restart api with --build
```

## Cost Discipline

- Hard cap per run: $10
- RunPod RTX 4090 Community Cloud: $0.34/hr (preferred, spot)
- RunPod RTX 4090 Secure: $0.69/hr (fallback)
- Eval inference: ~1hr ($0.34-0.69)

## Dataset Composition (Day 32 first run)

Per status check: 277 pairs collected. Need 500+ to trigger.
Expected by Day 32:
- synthetic_seed_v1: ~600 (resumed Day 29)
- distill_kimi_v1: ~50 (slow due to Ollama bottleneck)
- cai_pipeline: ~20
- **Total target: ~700 pairs** + 50 identity-anchor = 750 training samples

## References (per blueprint)

- SimPO paper: arXiv:2405.14734 (length-normalized, no reference model, +6.4 pts AlpacaEval2 vs DPO)
- Unsloth: 2× faster, 70% less VRAM (claim: github.com/unslothai/unsloth)
- Identity-preserving samples: blueprint Section 7.2 (50 anchors prevent catastrophic forgetting)
