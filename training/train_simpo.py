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
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=5e-6)  # SimPO recommendation
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--simpo-beta", type=float, default=2.0)  # SimPO paper default
    parser.add_argument("--simpo-gamma", type=float, default=1.4)  # length normalization
    parser.add_argument("--dry-run", action="store_true", help="Validate config without training")
    args = parser.parse_args()

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

    config = SimPOConfig(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        warmup_ratio=0.1,
        logging_steps=10,
        save_strategy="epoch",
        max_length=args.max_seq_length,
        max_prompt_length=args.max_seq_length // 2,
        beta=args.simpo_beta,
        gamma=args.simpo_gamma,
        bf16=True,
        report_to="wandb" if os.environ.get("WANDB_API_KEY") else "none",
        remove_unused_columns=False,
    )

    trainer = SimPOTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=ds,
        args=config,
    )

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
        "method": "simpo",
        "lora_r": args.lora_r,
        "version": "v0.1-soul",
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
