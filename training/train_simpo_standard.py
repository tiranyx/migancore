#!/usr/bin/env python3
"""
MiganCore SimPO Training — Standard bf16, No Quantization
==========================================================
Lesson #106: Q RTX 8000 has 47.8 GB VRAM. Qwen2.5-7B in bf16 uses ~14 GB.
No bitsandbytes needed — it causes infer_schema(torch.Tensor) errors on
PyTorch 2.4.0 due to custom CUDA op schema registration mismatch.
Load model in bf16 directly. LoRA trains only ~25M params (rank 16),
optimizer states fit comfortably in remaining VRAM.

Compatible with: pytorch/pytorch:2.4.0-cuda12.1-cudnn9-devel
Requires pip:   trl>=0.9.6, peft, datasets, accelerate
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def check_env():
    import torch
    if not torch.cuda.is_available():
        print("ERROR: No CUDA GPU detected.", file=sys.stderr)
        sys.exit(1)
    vram = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"GPU  : {torch.cuda.get_device_name(0)}")
    print(f"VRAM : {vram:.1f} GB  (Qwen2.5-7B bf16 needs ~14 GB — {'OK' if vram >= 20 else 'WARN'})")
    print(f"Torch: {torch.__version__}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset",        required=True)
    parser.add_argument("--output-dir",     default="/root/cycle2_adapter")
    parser.add_argument("--base-model",     default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--epochs",         type=int,   default=1)
    parser.add_argument("--learning-rate",  type=float, default=5e-7)
    parser.add_argument("--simpo-beta",     type=float, default=2.5)
    parser.add_argument("--simpo-gamma",    type=float, default=1.0)
    parser.add_argument("--loss-type",      default="apo_zero",
                        choices=["sigmoid", "hinge", "ipo", "apo_zero", "apo_down"])
    parser.add_argument("--lora-r",         type=int,   default=16)
    parser.add_argument("--lora-alpha",     type=int,   default=16)
    parser.add_argument("--batch-size",     type=int,   default=2)
    parser.add_argument("--grad-accum",     type=int,   default=8)
    parser.add_argument("--max-seq-length", type=int,   default=2048)
    args = parser.parse_args()

    print("=" * 60)
    print("MIGANCORE SimPO TRAINING — bf16 direct (no quantization)")
    print("=" * 60)
    print(f"Base model  : {args.base_model}")
    print(f"Dataset     : {args.dataset}")
    print(f"Output      : {args.output_dir}")
    print(f"Epochs      : {args.epochs}")
    print(f"LoRA rank   : {args.lora_r}")
    print(f"SimPO beta  : {args.simpo_beta}")
    print(f"SimPO gamma : {args.simpo_gamma}")
    print(f"Loss type   : {args.loss_type}")
    print(f"LR          : {args.learning_rate}")
    print(f"Eff. batch  : {args.batch_size} × {args.grad_accum} = {args.batch_size * args.grad_accum}")
    print("=" * 60)

    check_env()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model, TaskType
    from datasets import load_dataset

    # Lesson #110: SimPOTrainer does not exist in TRL 0.9.6 (nor in 0.29.1).
    # Lesson #112: CPOTrainer with loss_type="simpo" in TRL 0.9.6 fails with
    #   TypeError: 'NoneType' cannot be interpreted as int in DataCollator
    #   (DataCollatorWithPadding receives None for a tokenized field during
    #   CPO-SimPO tokenize_row — root cause unresolved; skip CPO entirely).
    # ORPOTrainer (TRL 0.9.6): reference-free, SFT + odds-ratio preference loss.
    #   Equivalent quality to SimPO for identity/behavioral alignment.
    #   beta=0.1 (standard ORPO scale) = simpo_beta/25.
    # Priority: SimPO native → ORPO → CPO (last resort)
    import trl as _trl
    print(f"TRL version: {_trl.__version__}")
    _available_trainers = [x for x in dir(_trl) if "Trainer" in x]
    print(f"Available trainers: {_available_trainers}")

    TRAINER_MODE = None
    try:
        from trl import SimPOConfig, SimPOTrainer
        TRAINER_MODE = "simpo"
        print("Trainer mode: SimPOTrainer (native)")
    except ImportError:
        try:
            from trl import ORPOTrainer, ORPOConfig
            TRAINER_MODE = "orpo"
            print("Trainer mode: ORPOTrainer (reference-free, SFT+OR preference, TRL 0.9.6)")
        except ImportError:
            try:
                # CPO last: known to have DataCollator NoneType bug with loss_type=simpo
                from trl import CPOTrainer, CPOConfig
                TRAINER_MODE = "cpo_simpo"
                print("Trainer mode: CPOTrainer (last resort — may have DataCollator issues)")
            except ImportError:
                available = [x for x in dir(_trl) if "Trainer" in x]
                raise RuntimeError(f"No compatible preference trainer in TRL {_trl.__version__}. Available: {available}")

    # ── Load model in bf16 (no quantization — 47 GB VRAM is enough) ──
    print(f"\nLoading {args.base_model} in bf16 (no bitsandbytes quantization)...")
    t_load = time.time()

    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    tokenizer.padding_side = "right"  # required for ORPO/DPO causal training
    print(f"Model loaded in {time.time() - t_load:.0f}s")

    # ── Enable gradient checkpointing (reduce activation memory) ──────
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable()

    # ── Apply LoRA ────────────────────────────────────────────────────
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ── Dataset ───────────────────────────────────────────────────────
    print(f"\nLoading dataset {args.dataset}...")
    ds = load_dataset("json", data_files=args.dataset, split="train")
    print(f"Dataset: {len(ds)} pairs")
    print(f"Columns: {ds.column_names}")

    # ── Common training args ──────────────────────────────────────────
    _common = dict(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        warmup_ratio=0.1,
        logging_steps=10,
        save_strategy="steps",
        save_steps=50,
        max_length=args.max_seq_length,
        max_prompt_length=args.max_seq_length // 2,
        bf16=True,
        report_to="none",
        remove_unused_columns=False,
        gradient_checkpointing=True,
    )

    # ── Config + Trainer by mode ──────────────────────────────────────
    if TRAINER_MODE == "simpo":
        config = SimPOConfig(
            beta=args.simpo_beta,
            gamma=args.simpo_gamma,
            loss_type=args.loss_type,
            **_common,
        )
        trainer = SimPOTrainer(model=model, tokenizer=tokenizer, train_dataset=ds, args=config)

    elif TRAINER_MODE == "orpo":
        # ORPO: reference-free, beta=lambda controls preference strength.
        # ORPOConfig beta is typically 0.1; simpo_beta/25 scales proportionally.
        # (2.5 / 25 = 0.1 = standard ORPO recommendation)
        # ORPO jointly optimizes SFT loss + odds-ratio preference loss.
        # No reference model needed — memory-efficient on any GPU.
        orpo_beta = round(args.simpo_beta / 25.0, 3)  # 2.5/25 = 0.1
        config = ORPOConfig(beta=orpo_beta, **_common)
        trainer = ORPOTrainer(model=model, tokenizer=tokenizer, train_dataset=ds, args=config)
        print(f"ORPOConfig: beta={orpo_beta} (scaled from SimPO beta {args.simpo_beta})")

    elif TRAINER_MODE == "cpo_simpo":
        # CPO-SimPO: CPOTrainer with loss_type="simpo" = reference-free SimPO.
        # WARNING: TRL 0.9.6 CPOTrainer has a DataCollator NoneType bug (Lesson #112).
        # This branch is last resort only.
        _cpo_args = dict(beta=args.simpo_beta, loss_type="simpo", cpo_alpha=0.0, **_common)
        try:
            config = CPOConfig(simpo_gamma=args.simpo_gamma, **_cpo_args)
            print(f"CPOConfig: beta={args.simpo_beta} simpo_gamma={args.simpo_gamma}")
        except TypeError:
            config = CPOConfig(**_cpo_args)
            print(f"CPOConfig: beta={args.simpo_beta} (simpo_gamma not supported in this CPOConfig)")
        trainer = CPOTrainer(model=model, tokenizer=tokenizer, train_dataset=ds, args=config)

    else:
        raise RuntimeError(f"Unknown TRAINER_MODE: {TRAINER_MODE}")

    # ── Train ─────────────────────────────────────────────────────────
    print("\nStarting training...")
    t_train = time.time()
    trainer.train()
    train_elapsed = time.time() - t_train
    print(f"Training finished in {train_elapsed:.0f}s ({train_elapsed / 60:.1f} min)")

    # ── Save ──────────────────────────────────────────────────────────
    print(f"Saving adapter to {args.output_dir}...")
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    meta = {
        "base_model":    args.base_model,
        "dataset":       args.dataset,
        "dataset_size":  len(ds),
        "epochs":        args.epochs,
        "method":        f"{TRAINER_MODE}_bf16",
        "loss_type":     args.loss_type,
        "lora_r":        args.lora_r,
        "simpo_beta":    args.simpo_beta,
        "simpo_gamma":   args.simpo_gamma,
        "learning_rate": args.learning_rate,
        "train_elapsed": f"{train_elapsed:.0f}s",
        "version":       "v0.2-cycle2",
        "quantization":  "none (bf16 direct)",
    }
    with open(f"{args.output_dir}/training_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    print("=" * 60)
    print("TRAINING COMPLETE ✓")
    print("=" * 60)
    print(f"Adapter saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
