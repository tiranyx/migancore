#!/usr/bin/env python3
"""
Merge & Export — Combine LoRA adapter with base model for deployment
====================================================================
Usage:
    python scripts/merge_and_export.py \
        --adapter training_data/adapters/cpu_identity_lora_v2/adapter \
        --base_model Qwen/Qwen2.5-1.5B-Instruct \
        --output training_data/merged_model_v2
"""

import argparse
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def merge(adapter_path: str, base_model: str, output_path: str):
    print("Loading base model...")
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else "cpu",
        trust_remote_code=True,
    )

    print("Loading adapter...")
    model = PeftModel.from_pretrained(model, adapter_path)

    print("Merging...")
    model = model.merge_and_unload()

    print(f"Saving merged model to {output_path}...")
    Path(output_path).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_path)

    print("Saving tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    tokenizer.save_pretrained(output_path)

    print("Done!")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--base_model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    merge(args.adapter, args.base_model, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
