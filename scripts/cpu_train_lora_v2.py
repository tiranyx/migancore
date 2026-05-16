#!/usr/bin/env python3
"""
CPU LoRA Training Pipeline v2 — MiganCore Foundation Builder
=============================================================
Fixed: proper chat template, system prompt, label masking, hyperparameters.

This script builds the FOUNDATION for training:
- Correct Qwen2.5 chat template via tokenizer.apply_chat_template()
- SOUL.md system prompt injected into every sample
- Label masking: only compute loss on assistant tokens
- Conservative hyperparameters for CPU (1 epoch, low LR)

Usage:
    python scripts/cpu_train_lora_v2.py \
        --dataset training_data/identity_sft_200_ORGANIC.jsonl \
        --system_prompt Master_doc/01_SOUL.md \
        --output_dir training_data/adapters/cpu_identity_lora_v2 \
        --epochs 1

After training:
    python scripts/merge_and_export.py \
        --adapter training_data/adapters/cpu_identity_lora_v2 \
        --output training_data/merged_model_v2
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import torch
from torch.utils.data import Dataset

LOG_PATH = Path("logs/organic_sprint/cpu_train_lora_v2.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _log(msg: str) -> None:
    ts = datetime.now().isoformat()
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_system_prompt(path: str) -> str:
    """Load SOUL.md or custom system prompt."""
    p = Path(path)
    if not p.exists():
        _log(f"WARNING: System prompt not found at {path}, using default.")
        return "You are Mighan-Core, an Autonomous Digital Organism."
    text = p.read_text(encoding="utf-8")
    # Extract just the identity section if it's SOUL.md
    lines = text.splitlines()
    # Simple extraction: take first ~30 non-empty lines as identity core
    core_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("|") and not stripped.startswith(">"):
            core_lines.append(stripped)
        if len(core_lines) >= 30:
            break
    result = " ".join(core_lines[:30])
    _log(f"Loaded system prompt ({len(result)} chars) from {path}")
    return result


class ChatDataset(Dataset):
    """Dataset that uses proper chat template with system prompt."""

    def __init__(self, data_path: str, tokenizer, system_prompt: str, max_length: int = 512):
        self.samples = []
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.system_prompt = system_prompt

        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line.strip())
                instruction = item.get("instruction", "")
                inp = item.get("input", "")
                output = item.get("output", "")

                # Build messages in OpenAI format
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{instruction}\n{inp}".strip() if inp else instruction},
                    {"role": "assistant", "content": output},
                ]

                # Apply chat template
                full_text = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=False,
                )

                # Build prompt-only text (for label masking)
                prompt_messages = messages[:-1]  # Exclude assistant
                prompt_text = tokenizer.apply_chat_template(
                    prompt_messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )

                self.samples.append({"full_text": full_text, "prompt_text": prompt_text})

        _log(f"Loaded {len(self.samples)} samples from {data_path}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]

        # Tokenize full text
        full_enc = self.tokenizer(
            sample["full_text"],
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )

        # Tokenize prompt-only
        prompt_enc = self.tokenizer(
            sample["prompt_text"],
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )

        input_ids = full_enc["input_ids"].squeeze(0)
        attention_mask = full_enc["attention_mask"].squeeze(0)

        # Labels: mask prompt tokens with -100 so loss only computed on assistant response
        labels = input_ids.clone()
        prompt_len = prompt_enc["input_ids"].shape[1]
        # Find actual prompt length (before padding)
        actual_prompt_len = (prompt_enc["attention_mask"].squeeze(0) == 1).sum().item()
        labels[:actual_prompt_len] = -100

        # Also mask padding tokens
        labels[attention_mask == 0] = -100

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


def train(args):
    from transformers import (
        AutoTokenizer,
        AutoModelForCausalLM,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling,
    )
    from peft import LoraConfig, get_peft_model, TaskType

    _log("=" * 60)
    _log("CPU LoRA Training Pipeline v2 — Foundation Builder")
    _log(f"  Dataset: {args.dataset}")
    _log(f"  Output: {args.output_dir}")
    _log(f"  Epochs: {args.epochs}")
    _log(f"  Rank: {args.rank}")
    _log(f"  Max Length: {args.max_length}")
    _log(f"  Device: CPU (torch {torch.__version__})")
    _log("=" * 60)

    # Load system prompt
    system_prompt = load_system_prompt(args.system_prompt)

    # Load tokenizer
    _log("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model
    _log("Loading base model...")
    load_kwargs = {
        "torch_dtype": torch.float32,
        "trust_remote_code": True,
        "device_map": "cpu",
        "low_cpu_mem_usage": True,
    }
    if torch.cuda.is_available():
        try:
            import bitsandbytes as bnb
            load_kwargs["load_in_8bit"] = True
            load_kwargs["device_map"] = "auto"
            _log("GPU available — using 8-bit quantization")
        except ImportError:
            _log("CPU only — using float32")
    else:
        _log("CPU only — using float32")

    model = AutoModelForCausalLM.from_pretrained(args.base_model, **load_kwargs)

    # Apply LoRA
    _log(f"Applying LoRA (rank={args.rank}, alpha={args.alpha})...")
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
    _log("Loading dataset with chat template...")
    dataset = ChatDataset(args.dataset, tokenizer, system_prompt, max_length=args.max_length)
    if len(dataset) == 0:
        _log("ERROR: Dataset is empty!")
        return 1

    # Training args
    output_path = Path(args.output_dir)
    training_args = TrainingArguments(
        output_dir=str(output_path),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=args.learning_rate,
        warmup_steps=args.warmup_steps,
        logging_steps=10,
        save_strategy="epoch",
        fp16=False,
        bf16=False,
        remove_unused_columns=False,
        dataloader_num_workers=0,
        report_to="none",
    )

    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    # Trainer
    _log("Starting training...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=data_collator,
    )

    start = time.time()
    trainer.train()
    elapsed = time.time() - start

    # Save adapter
    _log(f"Training complete! Elapsed: {elapsed / 60:.1f} minutes")
    model.save_pretrained(output_path / "adapter")
    tokenizer.save_pretrained(output_path / "adapter")
    _log(f"Adapter saved to: {output_path / 'adapter'}")

    # Save metadata
    meta = {
        "base_model": args.base_model,
        "dataset": str(args.dataset),
        "dataset_size": len(dataset),
        "epochs": args.epochs,
        "rank": args.rank,
        "alpha": args.alpha,
        "learning_rate": args.learning_rate,
        "max_length": args.max_length,
        "elapsed_minutes": round(elapsed / 60, 1),
        "system_prompt_length": len(system_prompt),
    }
    with open(output_path / "training_metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    _log("=" * 60)
    _log("SUCCESS: LoRA adapter trained and saved.")
    _log("Next: Run eval_adapter.py to verify identity.")
    _log("=" * 60)
    return 0


def main():
    parser = argparse.ArgumentParser(description="CPU LoRA Training v2 — Foundation Builder")
    parser.add_argument("--dataset", default="training_data/identity_sft_200_ORGANIC.jsonl")
    parser.add_argument("--system_prompt", default="Master_doc/01_SOUL.md")
    parser.add_argument("--output_dir", default="training_data/adapters/cpu_identity_lora_v2")
    parser.add_argument("--base_model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--rank", type=int, default=8)
    parser.add_argument("--alpha", type=int, default=16)
    parser.add_argument("--max_length", type=int, default=512)
    parser.add_argument("--learning_rate", type=float, default=5e-5)
    parser.add_argument("--warmup_steps", type=int, default=10)
    args = parser.parse_args()
    return train(args)


if __name__ == "__main__":
    raise SystemExit(main())
