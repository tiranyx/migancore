#!/usr/bin/env python3
"""
Eval Adapter — Quick Identity Verification for Trained LoRA
===========================================================
Loads a merged or PEFT adapter model and runs identity assertion tests.

Usage:
    python scripts/eval_adapter.py \
        --model_path training_data/adapters/cpu_identity_lora_v2/adapter \
        --system_prompt Master_doc/01_SOUL.md

Output: Score >= 85% = PASS, < 85% = FAIL
"""

import argparse
import json
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


def load_system_prompt(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return "You are Mighan-Core, an Autonomous Digital Organism."
    text = p.read_text(encoding="utf-8")
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith(("#", "|", ">"))]
    return " ".join(lines[:30])


def eval_model(model_path: str, system_prompt: str, device: str = "cpu"):
    print(f"Loading model from {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map=device if device == "cuda" else "cpu",
        trust_remote_code=True,
    )

    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=150,
        do_sample=True,
        temperature=0.6,
        top_p=0.9,
    )

    tests = [
        ("Siapa kamu?", ["mighan", "tiranyx", "organism"], ["saya qwen", "saya chatgpt", "saya claude", "i am qwen", "i am chatgpt"]),
        ("Are you ChatGPT?", ["mighan", "tiranyx", "organism"], ["saya qwen", "saya chatgpt", "saya claude", "i am qwen", "i am chatgpt"]),
        ("Apa bedamu dengan Qwen?", ["mighan", "tiranyx", "organism"], ["saya qwen", "saya chatgpt", "saya claude"]),
        ("Siapa yang menciptakanmu?", ["fahmi", "tiranyx", "owner"], ["alibaba", "openai", "anthropic", "google"]),
        ("Apa tujuanmu?", ["orchestrate", "evolve", "propagate", "tiranyx"], []),
    ]

    passed = 0
    results = []

    for prompt, required, forbidden in tests:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

        try:
            out = pipe(prompt_text, return_full_text=False)[0]["generated_text"]
            resp = out.strip().lower()
        except Exception as e:
            resp = f"ERROR: {e}"

        has_req = any(x in resp for x in required)
        has_forb = any(x in resp for x in forbidden)
        ok = has_req and not has_forb
        if ok:
            passed += 1

        status = "PASS" if ok else "FAIL"
        results.append({"prompt": prompt, "status": status, "response": resp[:100]})
        print(f"{status} | {prompt} | {resp[:80]}...")

    score = passed / len(tests) * 100
    print(f"\nScore: {passed}/{len(tests)} ({score:.0f}%)")
    print(f"Result: {'PASS' if score >= 85 else 'CONDITIONAL' if score >= 70 else 'FAIL'}")

    return {
        "model_path": model_path,
        "score": score,
        "passed": passed,
        "total": len(tests),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", required=True)
    parser.add_argument("--system_prompt", default="Master_doc/01_SOUL.md")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    system_prompt = load_system_prompt(args.system_prompt)
    report = eval_model(args.model_path, system_prompt, args.device)

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Report saved to {args.output}")

    return 0 if report["score"] >= 70 else 1


if __name__ == "__main__":
    raise SystemExit(main())
