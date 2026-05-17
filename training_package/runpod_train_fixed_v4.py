#!/usr/bin/env python3
"""MiganForge DPO Trainer - Fixed v4 for RunPod.

Purpose:
- Keep the stable CUDA stack from the RunPod experiment.
- Convert identity chat messages into a single text field before SFT.
- Save the SFT adapter before attempting DPO, so identity progress survives.
- Patch the TRL 0.11.4 / Transformers 4.48 Trainer.get_batch_samples mismatch.
- Support tiny smoke runs before full GPU spend.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from datasets import Dataset, concatenate_datasets
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer
from trl import DPOConfig, DPOTrainer, SFTConfig, SFTTrainer


def _patch_dpo_trainer_for_transformers_448() -> None:
    """Make TRL 0.11.4 DPOTrainer compatible with Transformers 4.48+.

    TRL 0.11.4 overrides get_batch_samples(model, batch) for optional sample
    generation, but Transformers 4.48 calls get_batch_samples(epoch_iterator,
    num_batches) inside the train loop. With generate_during_eval=False, the TRL
    override is not needed for training, so restore the base Trainer method.
    """

    DPOTrainer.get_batch_samples = Trainer.get_batch_samples  # type: ignore[method-assign]

    old_log = DPOTrainer.log

    def log_compat(self, logs, *args, **kwargs):
        return old_log(self, logs)

    DPOTrainer.log = log_compat  # type: ignore[method-assign]


def load_dpo_data(path: str, max_length: int = 2048, max_samples: int = 0) -> Dataset:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            prompt = rec.get("prompt", "")
            chosen = rec.get("chosen", "")
            rejected = rec.get("rejected", "")
            if not prompt or not chosen or not rejected:
                continue
            if len(prompt) > max_length * 3 or len(chosen) > max_length * 3 or len(rejected) > max_length * 3:
                continue
            records.append({"prompt": prompt, "chosen": chosen, "rejected": rejected})
            if max_samples and len(records) >= max_samples:
                break
    return Dataset.from_list(records)


def load_identity_data(path: str, tokenizer, max_samples: int = 0) -> Dataset:
    texts = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if "messages" in rec:
                text = tokenizer.apply_chat_template(
                    rec["messages"], tokenize=False, add_generation_prompt=False
                )
            else:
                text = rec.get("text", "")
            if text:
                texts.append(text)
            if max_samples and len(texts) >= max_samples:
                break
    return Dataset.from_list([{"text": text} for text in texts])


def combine_datasets(datasets: list[Dataset]) -> Dataset:
    datasets = [dataset for dataset in datasets if len(dataset) > 0]
    if not datasets:
        raise ValueError("No non-empty datasets to combine.")
    if len(datasets) == 1:
        return datasets[0]
    return concatenate_datasets(datasets)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dpo-data", required=True)
    parser.add_argument("--identity-data", default="")
    parser.add_argument(
        "--extra-dpo-data",
        action="append",
        default=[],
        help="Additional DPO JSONL file to append. Can be passed multiple times.",
    )
    parser.add_argument(
        "--extra-identity-data",
        action="append",
        default=[],
        help="Additional identity SFT JSONL file to append. Can be passed multiple times.",
    )
    parser.add_argument("--output-dir", default="/workspace/training_output")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--lr", type=float, default=5e-6)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=4)
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--max-sft-samples", type=int, default=0)
    parser.add_argument("--max-dpo-samples", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=-1)
    parser.add_argument("--skip-sft", action="store_true")
    args = parser.parse_args()

    _patch_dpo_trainer_for_transformers_448()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("MiganForge DPO Trainer - Fixed v4")
    print("=" * 70)
    print(f"Output: {output_dir}")
    print(f"Smoke max_steps: {args.max_steps}")
    print(f"Max SFT samples: {args.max_sft_samples or 'all'}")
    print(f"Max DPO samples: {args.max_dpo_samples or 'all'}")

    print("\n[1] Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("[2] Loading datasets...")
    dpo_parts = [load_dpo_data(args.dpo_data, args.max_length, args.max_dpo_samples)]
    for extra_path in args.extra_dpo_data:
        if Path(extra_path).exists():
            extra_dataset = load_dpo_data(extra_path, args.max_length)
            print(f"  Extra DPO {extra_path}: {len(extra_dataset)} examples")
            dpo_parts.append(extra_dataset)
        else:
            raise FileNotFoundError(f"Extra DPO data not found: {extra_path}")
    dpo_dataset = combine_datasets(dpo_parts)
    if len(dpo_dataset) < 2:
        raise ValueError("DPO dataset needs at least 2 valid records.")
    print(f"  DPO: {len(dpo_dataset)} examples")

    identity_dataset = None
    if not args.skip_sft and args.identity_data and Path(args.identity_data).exists():
        identity_parts = [load_identity_data(args.identity_data, tokenizer, args.max_sft_samples)]
        for extra_path in args.extra_identity_data:
            if Path(extra_path).exists():
                extra_dataset = load_identity_data(extra_path, tokenizer)
                print(f"  Extra identity {extra_path}: {len(extra_dataset)} examples")
                identity_parts.append(extra_dataset)
            else:
                raise FileNotFoundError(f"Extra identity data not found: {extra_path}")
        identity_dataset = combine_datasets(identity_parts)
        print(f"  Identity: {len(identity_dataset)} examples")

    print("[3] Loading model with QLoRA...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16,
    )
    model = prepare_model_for_kbit_training(model)

    print("[4] Applying LoRA...")
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    if identity_dataset:
        print("\n[5] SFT warm-start (identity anchoring)...")
        sft_args = SFTConfig(
            output_dir=str(output_dir / "identity_sft"),
            num_train_epochs=1,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            learning_rate=1e-4,
            warmup_steps=10,
            logging_steps=5,
            save_strategy="no",
            fp16=False,
            bf16=False,
            optim="adamw_torch",
            seed=args.seed,
            report_to=[],
            max_seq_length=args.max_length,
            dataset_text_field="text",
            max_steps=args.max_steps if args.max_steps > 0 else -1,
        )
        sft_trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=identity_dataset,
            args=sft_args,
        )
        sft_trainer.train()
        sft_adapter = output_dir / "identity_adapter"
        model.save_pretrained(sft_adapter)
        tokenizer.save_pretrained(sft_adapter)
        print(f"SFT warm-start complete. Adapter saved to: {sft_adapter}")
        del sft_trainer
        torch.cuda.empty_cache()

    print("\n[6] DPO Training...")
    split = dpo_dataset.train_test_split(test_size=0.05, seed=args.seed)
    train_data = split["train"]
    eval_data = split["test"]
    print(f"  Train: {len(train_data)}, Eval: {len(eval_data)}")

    dpo_args = DPOConfig(
        output_dir=str(output_dir / "dpo_checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        beta=0.1,
        warmup_ratio=0.1,
        logging_steps=1 if args.max_steps > 0 else 10,
        save_strategy="no" if args.max_steps > 0 else "epoch",
        eval_strategy="no" if args.max_steps > 0 else "epoch",
        load_best_model_at_end=False if args.max_steps > 0 else True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=False,
        bf16=False,
        optim="adamw_torch",
        seed=args.seed,
        report_to=[],
        max_length=args.max_length,
        max_prompt_length=args.max_length // 2,
        generate_during_eval=False,
        remove_unused_columns=False,
        max_steps=args.max_steps,
    )

    trainer = DPOTrainer(
        model=model,
        ref_model=None,
        args=dpo_args,
        train_dataset=train_data,
        eval_dataset=eval_data,
        tokenizer=tokenizer,
    )
    trainer.train()

    print("\n[7] Saving adapter...")
    adapter_dir = output_dir / "adapter"
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)

    if args.max_steps <= 0:
        print("[8] Merging adapter...")
        merged_dir = output_dir / "merged_model"
        from peft import AutoPeftModelForCausalLM

        merged_model = AutoPeftModelForCausalLM.from_pretrained(
            str(adapter_dir), torch_dtype=torch.float16, device_map="auto"
        )
        merged_model = merged_model.merge_and_unload()
        merged_model.save_pretrained(merged_dir)
        tokenizer.save_pretrained(merged_dir)
        print(f"Merged:  {merged_dir}")
    else:
        print("[8] Smoke mode: merge skipped.")

    print("\n" + "=" * 70)
    print("Training complete.")
    print(f"Adapter: {adapter_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
