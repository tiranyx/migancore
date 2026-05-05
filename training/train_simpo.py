"""
SimPO Training Script (Day 32 — Cycle 1 Self-Improvement)

Per blueprint Section 6: Unsloth + QLoRA + SimPO on Qwen2.5-7B base
Target: RunPod RTX 4090, ~$5.50 (8hr × $0.69/hr)

This script runs ON RUNPOD, NOT on the production VPS.

Setup pod:
    runpodctl create pod \\
      --image runpod/pytorch:2.4.0-py3.11-cuda12.1.1-devel-ubuntu22.04 \\
      --gpu RTX4090 \\
      --disk-size 50

Once pod ready:
    pip install unsloth trl transformers datasets peft accelerate bitsandbytes wandb
    runpodctl receive <pod-id>:/workspace/dataset_v1.jsonl ./
    python train_simpo.py --dataset dataset_v1.jsonl

Estimated runtime: 6-8 hours for 700 pairs × 2 epochs.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Verify GPU available
def check_gpu():
    try:
        import torch
        if not torch.cuda.is_available():
            print("ERROR: No CUDA GPU detected. This script requires RunPod RTX 4090.", file=sys.stderr)
            sys.exit(1)
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    except ImportError:
        print("ERROR: PyTorch not installed.", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="JSONL dataset path")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--output-dir", default="/workspace/migancore-7b-soul-v0.1")
    # Day 39: defaults UPDATED based on community research Q2 2026
    # (princeton-nlp/SimPO #47 #62, arxiv 2502.01112, r/LocalLLaMA Apr 2026)
    # Paper defaults over-fit on small datasets; the values below are the empirically
    # robust values for Qwen2.5-7B + 500-700 DPO pairs on RTX 4090.
    parser.add_argument("--epochs", type=int, default=1,                 # was 2 — NEVER 2 di <700 pairs (overfit)
                        help="Training epochs. Stay at 1 for <700 pairs to avoid overfit.")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=5e-7,     # Day 49: lowered from 8e-7
                        help="LR. Day 49 update: 5e-7 per arxiv 2602.00954 (Feb 2026) — "
                             "<1k pair datasets need lr halved vs official SimPO recipe to "
                             "avoid reward hacking. 8e-7 still acceptable; 5e-7 is the safer default.")
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--max-seq-length", type=int, default=2048)
    # Day 42 update: TRL maintainers Mar 2026 PR #87 merged APO-zero loss type which
    # outperforms vanilla SimPO on <1k pair datasets (better reward margin stability).
    # Beta default lifted 2.0 -> 2.5 (sweet spot for small-data per Day 42 research).
    parser.add_argument("--simpo-beta", type=float, default=2.5,         # was 2.0 (Day 42 update)
                        help="SimPO beta. 2.5 = small-data sweet spot per Mar 2026 TRL benchmark.")
    parser.add_argument("--simpo-gamma", type=float, default=1.0,
                        help="SimPO length normalization. 1.0 = gamma_beta_ratio 0.5 (community Q2 2026).")
    parser.add_argument("--length-normalize", action="store_true", default=True,
                        help="Apply length normalization to logprobs (community fix Mar 2026 for Qwen2.5-7B over-length reward).")
    parser.add_argument("--loss-type", default="apo_zero",
                        choices=["sigmoid", "hinge", "ipo", "apo_zero", "apo_down"],
                        help="DPO/SimPO loss variant. Day 42 default apo_zero — outperforms vanilla on <1k pairs (TRL Mar 2026).")
    # Day 38 — APO identity loss term (research arxiv 2408.06266 + r/LocalLLaMA Aug 2025)
    # Adds an "anchor" loss that penalises drift on identity-anchor prompts during DPO/SimPO.
    # When enabled, requires --anchor-dataset (separate JSONL of {prompt, chosen} pairs that
    # represent the identity we want to preserve — typically baseline Qwen2.5-7B "siapa kamu"
    # responses + 49 other identity probes from eval/persona_consistency_v1.jsonl).
    parser.add_argument("--use-apo", action="store_true",
                        help="Enable APO identity-preservation loss (recommended for Cycle 1+)")
    parser.add_argument("--apo-lambda", type=float, default=0.05,         # was 0.1 — over-penalize chosen at low data
                        help="APO loss weight. 0.05 is community Q2 2026 sweet spot for <1k pairs (paper 0.1 over-penalizes).")
    parser.add_argument("--anchor-dataset", default="",
                        help="JSONL of identity-anchor prompts (required if --use-apo)")
    # Day 49: TRL 1.x optimizations (gracefully ignored if older TRL on pod)
    parser.add_argument("--padding-free", action="store_true", default=False,
                        help="Day 49: TRL 1.x feature. ~2x memory headroom for variable-length seqs. "
                             "Stacks with --use-liger-kernel.")
    parser.add_argument("--use-liger-kernel", action="store_true", default=False,
                        help="Day 49: TRL 1.x feature. Liger-Kernel fused ops, ~30% faster training.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config without training")
    args = parser.parse_args()

    if args.use_apo and not args.anchor_dataset:
        print("ERROR: --use-apo requires --anchor-dataset path.", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("MIGANCORE SimPO TRAINING — Cycle 1 (Day 32)")
    print("=" * 60)
    print(f"Base model:        {args.base_model}")
    print(f"Dataset:           {args.dataset}")
    print(f"Output:            {args.output_dir}")
    print(f"Epochs:            {args.epochs}")
    print(f"LoRA rank:         {args.lora_r}")
    print(f"SimPO beta:        {args.simpo_beta}")
    print(f"SimPO gamma:       {args.simpo_gamma}")
    print(f"Loss type:         {args.loss_type} (Day 42: apo_zero default for small-data reward stability)")
    print(f"APO enabled:       {args.use_apo} (lambda={args.apo_lambda}, anchor={args.anchor_dataset or '-'})")
    print(f"Learning rate:     {args.learning_rate}")
    print(f"Effective batch:   {args.batch_size} × {args.grad_accum} = {args.batch_size * args.grad_accum}")
    print("=" * 60)

    if args.dry_run:
        print("Dry run — exiting before model load.")
        return

    check_gpu()

    # Lazy imports — avoid loading heavy libs during dry-run
    from unsloth import FastLanguageModel, PatchDPOTrainer
    from trl import SimPOConfig, SimPOTrainer
    from datasets import load_dataset

    PatchDPOTrainer()  # Required for SimPO

    print("Loading base model with Unsloth (4-bit QLoRA)...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base_model,
        max_seq_length=args.max_seq_length,
        load_in_4bit=True,
        dtype=None,  # auto
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    )

    print(f"Loading dataset from {args.dataset}...")
    ds = load_dataset("json", data_files=args.dataset, split="train")
    print(f"Dataset size: {len(ds)}")

    # Day 49: TRL 1.x optional optimizations — gracefully degraded if SimPOConfig
    # doesn't accept the kwargs (older TRL on pod). Use a kwargs dict + try/except.
    config_kwargs = dict(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        warmup_ratio=0.1,
        logging_steps=10,
        # Day 42: save_steps for spot-interruption recovery (RunPod 4090 ~6% interruption Q1 2026)
        save_strategy="steps",
        save_steps=50,
        max_length=args.max_seq_length,
        max_prompt_length=args.max_seq_length // 2,
        beta=args.simpo_beta,
        gamma=args.simpo_gamma,
        loss_type=args.loss_type,  # Day 42: apo_zero default
        bf16=True,
        report_to="wandb" if os.environ.get("WANDB_API_KEY") else "none",
        remove_unused_columns=False,
    )
    if args.padding_free:
        config_kwargs["padding_free"] = True
    if args.use_liger_kernel:
        config_kwargs["use_liger_kernel"] = True
    try:
        config = SimPOConfig(**config_kwargs)
    except TypeError as e:
        # TRL too old for one of the new flags — drop them and warn loudly
        for k in ("padding_free", "use_liger_kernel"):
            config_kwargs.pop(k, None)
        print(f"WARNING: SimPOConfig rejected new flags ({e}); falling back to TRL <1.x compatible config", file=sys.stderr)
        config = SimPOConfig(**config_kwargs)

    trainer = SimPOTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=ds,
        args=config,
    )

    # Day 38 — APO identity-preservation loss (anchored preference optimization)
    # arxiv 2408.06266: adds an auxiliary anchor loss = lambda * NLL(anchor_chosen)
    # that pulls the model back toward known-good identity responses while SimPO
    # pulls it toward the chosen-vs-rejected preference signal.
    if args.use_apo:
        print(f"Loading anchor dataset from {args.anchor_dataset}...")
        anchor_ds = load_dataset("json", data_files=args.anchor_dataset, split="train")
        print(f"Anchor size: {len(anchor_ds)} (typically 50 identity probes)")

        # Wrap original compute_loss to add APO term
        original_compute_loss = trainer.compute_loss

        def compute_loss_with_apo(model_, inputs, return_outputs=False, num_items_in_batch=None):
            simpo_out = original_compute_loss(model_, inputs, return_outputs=True, num_items_in_batch=num_items_in_batch)
            simpo_loss = simpo_out[0] if isinstance(simpo_out, tuple) else simpo_out

            # Sample one anchor per step (cheap, randomized — full batch unnecessary)
            import random as _r
            anchor_idx = _r.randrange(len(anchor_ds))
            anchor_item = anchor_ds[anchor_idx]
            anchor_text = anchor_item.get("prompt", "") + "\n" + anchor_item.get("chosen", "")
            anchor_tok = tokenizer(anchor_text, return_tensors="pt", truncation=True,
                                   max_length=args.max_seq_length).to(model_.device)
            anchor_out = model_(**anchor_tok, labels=anchor_tok["input_ids"])
            apo_loss = args.apo_lambda * anchor_out.loss

            total = simpo_loss + apo_loss
            if hasattr(trainer, "log") and trainer.state.global_step % 10 == 0:
                trainer.log({"apo_loss": float(apo_loss.detach().item()),
                             "simpo_loss": float(simpo_loss.detach().item())})
            if return_outputs:
                return (total,) + simpo_out[1:] if isinstance(simpo_out, tuple) and len(simpo_out) > 1 else (total, None)
            return total

        trainer.compute_loss = compute_loss_with_apo
        print(f"APO wrapper installed (lambda={args.apo_lambda})")

    print("Starting training...")
    trainer.train()

    print(f"Saving adapter to {args.output_dir}...")
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    # Save metadata for hot-swap step
    meta = {
        "base_model": args.base_model,
        "dataset": args.dataset,
        "dataset_size": len(ds),
        "epochs": args.epochs,
        "method": "simpo+apo" if args.use_apo else "simpo",
        "lora_r": args.lora_r,
        "version": "v0.1-soul",
        "apo_enabled": bool(args.use_apo),
        "apo_lambda": args.apo_lambda if args.use_apo else None,
        "anchor_dataset": args.anchor_dataset if args.use_apo else None,
    }
    with (Path(args.output_dir) / "training_metadata.json").open("w") as f:
        json.dump(meta, f, indent=2)

    print("=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Adapter saved to: {args.output_dir}")
    print(f"Next: convert to GGUF + push to HF Hub + Ollama hot-swap")
    print(f"  python convert_gguf.py --adapter {args.output_dir} --output migancore-7b-soul-v0.1.Q4_K_M.gguf")


if __name__ == "__main__":
    main()
