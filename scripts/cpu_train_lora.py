#!/usr/bin/env python3
"""
CPU LoRA Training Pipeline — MiganCore Organic Growth Sprint
Trains identity LoRA adapter using CPU-only environment (32GB RAM VPS).
No GPU required. No cloud cost.

Based on: transformers + PEFT + bitsandbytes (CPU-compatible)
Target: 7B Qwen2.5 with LoRA rank 8-16 on CPU (slow but functional)

Usage:
    python scripts/cpu_train_lora.py \
        --dataset training_data/identity_sft_200_ORGANIC.jsonl \
        --output_dir training_data/adapters/cpu_identity_lora \
        --epochs 3 \
        --rank 8

WARNING: Training 7B on CPU is SLOW (~2-4 hours/epoch). Run overnight.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import torch
from torch.utils.data import Dataset

# Logging setup
LOG_PATH = Path("logs/organic_sprint/cpu_train_lora.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _log(msg: str) -> None:
    ts = datetime.now().isoformat()
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class IdentitySFTDataset(Dataset):
    """Simple dataset for instruction-following SFT."""
    
    def __init__(self, data_path: str, tokenizer, max_length: int = 512):
        self.samples = []
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line.strip())
                instruction = item.get("instruction", "")
                inp = item.get("input", "")
                output = item.get("output", "")
                
                # Qwen2.5 chat format
                if inp:
                    prompt = f"<|im_start|>user\n{instruction}\n{inp}<|im_end|>\n<|im_start|>assistant\n"
                else:
                    prompt = f"<|im_start|>user\n{instruction}<|im_end|>\n<|im_start|>assistant\n"
                
                full_text = prompt + output + "<|im_end|>"
                self.samples.append({"prompt": prompt, "output": output, "full_text": full_text})
        
        _log(f"Loaded {len(self.samples)} samples from {data_path}")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        encoding = self.tokenizer(
            sample["full_text"],
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        
        # Create labels: mask prompt tokens with -100
        prompt_encoding = self.tokenizer(
            sample["prompt"],
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        
        labels = encoding["input_ids"].clone()
        prompt_len = prompt_encoding["input_ids"].shape[1]
        labels[:, :prompt_len] = -100
        
        return {
            "input_ids": encoding["input_ids"].flatten(),
            "attention_mask": encoding["attention_mask"].flatten(),
            "labels": labels.flatten(),
        }


def train(args):
    _log("=" * 60)
    _log("CPU LoRA Training Pipeline Started")
    _log(f"  Dataset: {args.dataset}")
    _log(f"  Output: {args.output_dir}")
    _log(f"  Epochs: {args.epochs}")
    _log(f"  LoRA Rank: {args.rank}")
    _log(f"  Device: CPU (torch {torch.__version__})")
    _log("=" * 60)
    
    # Check dependencies
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
        from peft import LoraConfig, get_peft_model, TaskType
    except ImportError as e:
        _log(f"ERROR: Missing dependency: {e}")
        _log("Install: pip install transformers peft accelerate")
        return 1
    
    # Load tokenizer
    _log("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load model (CPU, 4-bit quantization if bitsandbytes available)
    _log("Loading base model (this may take 5-10 minutes on CPU)...")
    load_kwargs = {
        "torch_dtype": torch.float32,  # CPU needs float32
        "trust_remote_code": True,
        "device_map": "cpu",
        "low_cpu_mem_usage": True,
    }
    
    # Try 8-bit for memory savings if bitsandbytes available
    try:
        import bitsandbytes as bnb
        _log("bitsandbytes available — using 8-bit quantization")
        load_kwargs["load_in_8bit"] = True
    except ImportError:
        _log("bitsandbytes not available — using full precision (needs ~28GB RAM)")
    
    model = AutoModelForCausalLM.from_pretrained(args.base_model, **load_kwargs)
    
    # Apply LoRA
    _log(f"Applying LoRA config (rank={args.rank}, alpha={args.alpha})...")
    lora_config = LoraConfig(
        r=args.rank,
        lora_alpha=args.alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Load dataset
    _log("Loading dataset...")
    dataset = IdentitySFTDataset(args.dataset, tokenizer, max_length=args.max_length)
    
    if len(dataset) == 0:
        _log("ERROR: Dataset is empty!")
        return 1
    
    # Training args
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    training_args = TrainingArguments(
        output_dir=str(output_path),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        logging_steps=5,
        save_strategy="epoch",
        save_total_limit=2,
        fp16=False,  # CPU doesn't support fp16
        bf16=False,
        dataloader_num_workers=0,
        remove_unused_columns=False,
        report_to="none",
        max_grad_norm=0.3,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
    )
    
    # Trainer
    _log("Starting training...")
    start_time = time.time()
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
    )
    
    trainer.train()
    
    elapsed = time.time() - start_time
    _log(f"Training complete! Elapsed: {elapsed/60:.1f} minutes")
    
    # Save adapter
    adapter_path = output_path / "adapter"
    model.save_pretrained(str(adapter_path))
    tokenizer.save_pretrained(str(adapter_path))
    _log(f"Adapter saved to: {adapter_path}")
    
    # Save metadata
    metadata = {
        "base_model": args.base_model,
        "lora_rank": args.rank,
        "lora_alpha": args.alpha,
        "epochs": args.epochs,
        "dataset": str(args.dataset),
        "dataset_size": len(dataset),
        "train_time_minutes": round(elapsed / 60, 2),
        "finished_at": datetime.now().isoformat(),
    }
    with open(output_path / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    _log("=" * 60)
    _log("SUCCESS: LoRA adapter trained and saved.")
    _log("Next: Convert to GGUF and deploy to Ollama")
    _log("=" * 60)
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="CPU LoRA Training for MiganCore")
    parser.add_argument("--dataset", default="training_data/identity_sft_200_ORGANIC.jsonl")
    parser.add_argument("--output_dir", default="training_data/adapters/cpu_identity_lora")
    parser.add_argument("--base_model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--rank", type=int, default=8)
    parser.add_argument("--alpha", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--grad_accum", type=int, default=4)
    parser.add_argument("--max_length", type=int, default=512)
    
    args = parser.parse_args()
    return train(args)


if __name__ == "__main__":
    raise SystemExit(main())
