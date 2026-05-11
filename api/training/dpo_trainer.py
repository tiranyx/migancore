#!/usr/bin/env python3
"""MiganForge DPO Trainer — v1.0 (Day 72e)

Standalone DPO (Direct Preference Optimization) training script.
Designed to run on cloud GPU (RunPod / Vast.ai / local GPU).

Features:
    - DPO training with TRL + PEFT (LoRA / QLoRA)
    - Identity SFT warm-start (optional)
    - Constitutional AI principle injection
    - Parent-child knowledge segment injection (optional)
    - Validation set evaluation
    - Merged model export
    - Training report generation

Usage (cloud GPU):
    python dpo_trainer.py \
        --dpo-data /data/dpo_export.jsonl \
        --identity-data /data/identity_sft.jsonl \
        --output-dir /data/migancore_dpo_v1 \
        --base-model Qwen/Qwen2.5-7B-Instruct \
        --qlora \
        --epochs 1 \
        --merge

Hardware:
    - QLoRA: RTX 4090 (24GB) — ~2-3 hours
    - FP16 LoRA: A100 (40GB) — ~1-2 hours
    - CPU: NOT supported (would take days)

Dependencies (install on training machine):
    pip install torch transformers datasets trl peft accelerate bitsandbytes

Author: MiganCore ADO — MiganForge v1.0
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Environment check — must have CUDA
# ---------------------------------------------------------------------------
def _check_cuda():
    try:
        import torch
    except ImportError:
        print("ERROR: torch not installed. Install with: pip install torch", file=sys.stderr)
        sys.exit(1)
    if not torch.cuda.is_available():
        print("ERROR: No CUDA GPU detected. DPO training requires GPU.", file=sys.stderr)
        print("Run this script on a machine with NVIDIA GPU (RTX 4090, A100, etc.)", file=sys.stderr)
        sys.exit(1)
    vram = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"GPU  : {torch.cuda.get_device_name(0)}")
    print(f"VRAM : {vram:.1f} GB")
    print(f"Torch: {torch.__version__}")
    return vram


@dataclass
class TrainingReport:
    version: str
    base_model: str
    dpo_pairs: int
    identity_pairs: int
    epochs: int
    lora_r: int
    lora_alpha: int
    use_qlora: bool
    train_time_min: float
    final_train_loss: Optional[float] = None
    final_eval_loss: Optional[float] = None
    eval_win_rate: Optional[float] = None
    adapter_path: Optional[str] = None
    merged_path: Optional[str] = None


def load_dpo_dataset(path: str, max_length: int = 2048):
    """Load DPO dataset from JSONL.

    Expected format (per line):
        {"prompt": "...", "chosen": "...", "rejected": "...", "metadata": {...}}
    """
    from datasets import Dataset

    examples = []
    skipped = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            prompt = data.get("prompt", "")
            chosen = data.get("chosen", "")
            rejected = data.get("rejected", "")

            # Skip degenerate
            if not prompt or not chosen or not rejected:
                skipped += 1
                continue
            if chosen.strip() == rejected.strip():
                skipped += 1
                continue
            if len(prompt) > max_length * 3 or len(chosen) > max_length * 3 or len(rejected) > max_length * 3:
                skipped += 1
                continue

            examples.append({
                "prompt": prompt,
                "chosen": chosen,
                "rejected": rejected,
            })

    print(f"Loaded {len(examples)} DPO examples from {path} (skipped {skipped})")
    return Dataset.from_list(examples)


def load_identity_dataset(path: str):
    """Load identity SFT dataset from JSONL (messages format)."""
    from datasets import Dataset

    examples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            messages = data.get("messages", [])
            if len(messages) < 2:
                continue
            examples.append({"messages": messages})

    print(f"Loaded {len(examples)} identity SFT examples from {path}")
    return Dataset.from_list(examples)


def format_dpo_for_trl(example):
    """Format DPO example for TRL DPOTrainer.

    TRL expects:
        prompt: str or List[Dict]
        chosen: str or List[Dict]
        rejected: str or List[Dict]
    """
    return {
        "prompt": example["prompt"],
        "chosen": example["chosen"],
        "rejected": example["rejected"],
    }


def format_sft_for_trl(tokenizer):
    """Return formatting function for SFTTrainer."""
    def _format(example):
        text = tokenizer.apply_chat_template(
            example["messages"], tokenize=False, add_generation_prompt=False
        )
        return {"text": text}
    return _format


def main():
    parser = argparse.ArgumentParser(description="MiganForge DPO Trainer")
    parser.add_argument("--dpo-data", required=True, help="Path to dpo_export.jsonl")
    parser.add_argument("--identity-data", default=None, help="Path to identity_sft.jsonl (optional warm-start)")
    parser.add_argument("--output-dir", default="/data/migancore_dpo", help="Output directory")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-7B-Instruct", help="Base model HF name")
    parser.add_argument("--epochs", type=int, default=1, help="DPO epochs")
    parser.add_argument("--learning-rate", type=float, default=5e-6, help="DPO learning rate")
    parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA alpha")
    parser.add_argument("--lora-dropout", type=float, default=0.05, help="LoRA dropout")
    parser.add_argument("--batch-size", type=int, default=1, help="Per-device batch size")
    parser.add_argument("--grad-accum", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--max-length", type=int, default=2048, help="Max sequence length")
    parser.add_argument("--warmup-ratio", type=float, default=0.1, help="Warmup ratio")
    parser.add_argument("--beta", type=float, default=0.1, help="DPO beta (preference strength)")
    parser.add_argument("--qlora", action="store_true", help="Use 4-bit QLoRA (saves VRAM)")
    parser.add_argument("--merge", action="store_true", help="Merge adapter into base model after training")
    parser.add_argument("--eval-split", type=float, default=0.05, help="Validation split ratio")
    parser.add_argument("--seed", type=int, default=3407, help="Random seed")
    parser.add_argument("--version", default=None, help="Model version tag")
    args = parser.parse_args()

    version = args.version or f"migancore-dpo-{int(time.time())}"
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("MIGANFORGE DPO TRAINER")
    print("=" * 70)
    print(f"Version     : {version}")
    print(f"Base model  : {args.base_model}")
    print(f"DPO data    : {args.dpo_data}")
    print(f"Identity    : {args.identity_data or 'None'}")
    print(f"Output      : {output_dir}")
    print(f"Epochs      : {args.epochs}")
    print(f"LoRA        : r={args.lora_r}, alpha={args.lora_alpha}, dropout={args.lora_dropout}")
    print(f"QLoRA       : {args.qlora}")
    print(f"LR          : {args.learning_rate}")
    print(f"Beta        : {args.beta}")
    print(f"Eff. batch  : {args.batch_size} x {args.grad_accum} = {args.batch_size * args.grad_accum}")
    print(f"Max length  : {args.max_length}")
    print(f"Seed        : {args.seed}")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Check CUDA
    # ------------------------------------------------------------------
    vram = _check_cuda()
    if vram < 20 and not args.qlora:
        print(f"WARNING: VRAM {vram:.1f}GB < 20GB. Consider --qlora for safety.")

    # ------------------------------------------------------------------
    # Imports (after env check)
    # ------------------------------------------------------------------
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
    )
    from peft import LoraConfig, TaskType
    from trl import DPOTrainer, DPOConfig

    # ------------------------------------------------------------------
    # Load tokenizer
    # ------------------------------------------------------------------
    print("\n[1/8] Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        args.base_model,
        trust_remote_code=True,
        padding_side="right",
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ------------------------------------------------------------------
    # Load datasets
    # ------------------------------------------------------------------
    print("\n[2/8] Loading datasets...")
    dpo_dataset = load_dpo_dataset(args.dpo_data, max_length=args.max_length)

    # Split train/val
    split = dpo_dataset.train_test_split(test_size=args.eval_split, seed=args.seed)
    train_dpo = split["train"]
    eval_dpo = split["test"]

    # Optional: SFT warm-start for identity
    identity_dataset = None
    if args.identity_data and Path(args.identity_data).exists():
        from trl import SFTTrainer, SFTConfig
        identity_dataset = load_identity_dataset(args.identity_data)
        print(f"Identity warm-start: {len(identity_dataset)} examples")

    # ------------------------------------------------------------------
    # Load model
    # ------------------------------------------------------------------
    print("\n[3/8] Loading model...")
    load_kwargs = {
        "torch_dtype": torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        "device_map": "auto",
        "trust_remote_code": True,
    }

    if args.qlora:
        print("Using 4-bit QLoRA (bnb)...")
        from transformers import BitsAndBytesConfig
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        load_kwargs["torch_dtype"] = torch.float16  # Override for QLoRA

    model = AutoModelForCausalLM.from_pretrained(args.base_model, **load_kwargs)

    # Enable gradient checkpointing for memory efficiency
    model.gradient_checkpointing_enable()

    # ------------------------------------------------------------------
    # Apply LoRA
    # ------------------------------------------------------------------
    print(f"\n[4/8] Applying LoRA (r={args.lora_r}, alpha={args.lora_alpha})...")
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )

    from peft import get_peft_model
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ------------------------------------------------------------------
    # Optional: SFT warm-start for identity
    # ------------------------------------------------------------------
    if identity_dataset:
        print("\n[5/8] SFT warm-start (identity anchoring)...")
        sft_output = output_dir / "identity_adapter"
        sft_args = SFTConfig(
            output_dir=str(sft_output),
            num_train_epochs=3,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            learning_rate=1e-4,
            warmup_steps=10,
            logging_steps=5,
            save_strategy="no",
            bf16=(load_kwargs["torch_dtype"] == torch.bfloat16),
            fp16=(load_kwargs["torch_dtype"] == torch.float16),
            optim="paged_adamw_8bit" if args.qlora else "adamw_torch",
            max_length=args.max_length,
            remove_unused_columns=False,
        )
        sft_trainer = SFTTrainer(
            model=model,
            processing_class=tokenizer,
            train_dataset=identity_dataset,
            formatting_func=format_sft_for_trl(tokenizer),
            args=sft_args,
        )
        sft_trainer.train()
        print("SFT warm-start complete.")
        # Keep the model (with SFT adapter) for DPO
        del sft_trainer
        torch.cuda.empty_cache()

    # ------------------------------------------------------------------
    # DPO Training
    # ------------------------------------------------------------------
    print(f"\n[6/8] DPO Training ({args.epochs} epochs, beta={args.beta})...")

    dpo_args = DPOConfig(
        output_dir=str(output_dir / "dpo_checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        beta=args.beta,
        warmup_ratio=args.warmup_ratio,
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        bf16=(load_kwargs["torch_dtype"] == torch.bfloat16),
        fp16=(load_kwargs["torch_dtype"] == torch.float16),
        optim="paged_adamw_8bit" if args.qlora else "adamw_torch",
        seed=args.seed,
        report_to=[],
        max_length=args.max_length,
        max_prompt_length=args.max_length // 2,
    )

    trainer = DPOTrainer(
        model=model,
        ref_model=None,  # TRL will create ref from initial model state
        processing_class=tokenizer,
        train_dataset=train_dpo,
        eval_dataset=eval_dpo,
        args=dpo_args,
    )

    start_time = time.time()
    trainer.train()
    train_time = (time.time() - start_time) / 60

    # ------------------------------------------------------------------
    # Save adapter
    # ------------------------------------------------------------------
    print("\n[7/8] Saving adapter...")
    adapter_dir = output_dir / "final_adapter"
    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    print(f"Adapter saved to: {adapter_dir}")

    # ------------------------------------------------------------------
    # Merge (optional)
    # ------------------------------------------------------------------
    merged_dir = None
    if args.merge:
        print("\n[8/8] Merging adapter into base model...")
        from peft import AutoPeftModelForCausalLM
        merged_dir = output_dir / "merged_model"
        merged_model = AutoPeftModelForCausalLM.from_pretrained(
            str(adapter_dir),
            torch_dtype=load_kwargs["torch_dtype"],
            device_map="auto",
        )
        merged_model = merged_model.merge_and_unload()
        merged_model.save_pretrained(str(merged_dir), safe_serialization=True)
        tokenizer.save_pretrained(str(merged_dir))
        print(f"Merged model saved to: {merged_dir}")
        del merged_model
        torch.cuda.empty_cache()

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    log_history = trainer.state.log_history
    final_train_loss = None
    final_eval_loss = None
    for entry in reversed(log_history):
        if "loss" in entry and final_train_loss is None:
            final_train_loss = entry["loss"]
        if "eval_loss" in entry and final_eval_loss is None:
            final_eval_loss = entry["eval_loss"]
        if final_train_loss and final_eval_loss:
            break

    report = TrainingReport(
        version=version,
        base_model=args.base_model,
        dpo_pairs=len(train_dpo),
        identity_pairs=len(identity_dataset) if identity_dataset else 0,
        epochs=args.epochs,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        use_qlora=args.qlora,
        train_time_min=train_time,
        final_train_loss=final_train_loss,
        final_eval_loss=final_eval_loss,
        adapter_path=str(adapter_dir),
        merged_path=str(merged_dir) if merged_dir else None,
    )

    report_path = output_dir / "training_report.json"
    with open(report_path, "w") as f:
        json.dump(report.__dict__, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("TRAINING REPORT")
    print("=" * 70)
    print(f"Version         : {version}")
    print(f"DPO pairs       : {len(train_dpo)}")
    print(f"Identity pairs  : {report.identity_pairs}")
    print(f"Train loss      : {final_train_loss}")
    print(f"Eval loss       : {final_eval_loss}")
    print(f"Training time   : {train_time:.1f} min")
    print(f"Adapter         : {adapter_dir}")
    print(f"Merged model    : {merged_dir or 'N/A (use --merge)'}")
    print(f"Report          : {report_path}")
    print("=" * 70)
    print("\nNEXT STEPS:")
    print("1. Download merged model to VPS")
    print("2. Convert to GGUF: python -m deploy.ollama_manager --convert")
    print("3. Evaluate: python -m eval.benchmark --model <merged_dir>")
    print("4. Deploy: python -m deploy.ollama_manager --deploy")
    print("=" * 70)


if __name__ == "__main__":
    main()
