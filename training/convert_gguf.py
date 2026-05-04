"""
Convert SimPO-trained adapter to GGUF Q4_K_M for Ollama hot-swap (Day 34).

Workflow (run on RunPod after train_simpo.py finishes):
  1. Merge LoRA adapter back to base model (full 16-bit weights)
  2. Convert to GGUF format (uses llama.cpp convert_hf_to_gguf.py)
  3. Quantize to Q4_K_M (best size/quality for CPU inference)
  4. Upload to HuggingFace Hub (free, public repo)

Then on production VPS:
  ollama pull migancore/migancore-7b-soul-v0.1
  # Update DEFAULT_MODEL env var
  # Restart api with --build

Usage:
    python convert_gguf.py \\
      --adapter /workspace/migancore-7b-soul-v0.1 \\
      --base Qwen/Qwen2.5-7B-Instruct \\
      --output migancore-7b-soul-v0.1.Q4_K_M.gguf \\
      --hf-repo migancore/migancore-7b-soul-v0.1
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: str = None) -> None:
    """Run shell command, fail on error."""
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=False)
    if result.returncode != 0:
        print(f"FAIL exit {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


def merge_adapter(adapter_path: str, base_model: str, output_dir: str):
    """Merge LoRA adapter into base model weights."""
    print(f"Merging adapter {adapter_path} into {base_model}...")

    from unsloth import FastLanguageModel
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=2048,
        load_in_4bit=False,  # need full precision for merge
    )

    from peft import PeftModel
    model = PeftModel.from_pretrained(model, adapter_path)
    model = model.merge_and_unload()  # merge LoRA weights into base

    print(f"Saving merged model to {output_dir}...")
    model.save_pretrained(output_dir, safe_serialization=True)
    tokenizer.save_pretrained(output_dir)


def convert_to_gguf(merged_dir: str, output_gguf: str):
    """Convert HF format to GGUF using llama.cpp script."""
    # llama.cpp must be cloned beforehand on the pod
    convert_script = "/workspace/llama.cpp/convert_hf_to_gguf.py"
    if not Path(convert_script).exists():
        print(f"Cloning llama.cpp (one-time)...")
        run(["git", "clone", "--depth=1", "https://github.com/ggerganov/llama.cpp.git", "/workspace/llama.cpp"])
        run(["pip", "install", "-r", "/workspace/llama.cpp/requirements.txt"])

    run([
        "python", convert_script,
        merged_dir,
        "--outfile", output_gguf,
        "--outtype", "f16",  # convert to f16 first, then quantize
    ])


def quantize_q4(input_gguf: str, output_gguf: str):
    """Quantize GGUF to Q4_K_M using llama.cpp quantize binary."""
    quantize_bin = "/workspace/llama.cpp/build/bin/llama-quantize"
    if not Path(quantize_bin).exists():
        print("Building llama.cpp quantize tool...")
        run(["cmake", "-B", "/workspace/llama.cpp/build", "-S", "/workspace/llama.cpp"])
        run(["cmake", "--build", "/workspace/llama.cpp/build", "--config", "Release", "-j"])

    run([quantize_bin, input_gguf, output_gguf, "Q4_K_M"])


def push_to_hf(local_path: str, hf_repo: str):
    """Upload GGUF to HuggingFace Hub."""
    if not os.environ.get("HF_TOKEN"):
        print("WARNING: HF_TOKEN not set, skipping push", file=sys.stderr)
        return
    run(["huggingface-cli", "upload", hf_repo, local_path, "--repo-type=model"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", required=True, help="Path to SimPO-trained adapter")
    parser.add_argument("--base", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--output", default="migancore-7b-soul-v0.1.Q4_K_M.gguf")
    parser.add_argument("--hf-repo", help="HF repo to push (e.g. migancore/migancore-7b-soul-v0.1)")
    parser.add_argument("--skip-merge", action="store_true")
    parser.add_argument("--skip-push", action="store_true")
    args = parser.parse_args()

    merged_dir = "/workspace/migancore-merged"
    f16_gguf = "/workspace/migancore-f16.gguf"

    if not args.skip_merge:
        merge_adapter(args.adapter, args.base, merged_dir)

    convert_to_gguf(merged_dir, f16_gguf)
    quantize_q4(f16_gguf, args.output)

    print(f"\n=== Quantized GGUF ready ===")
    print(f"  File: {args.output}")
    file_size_mb = Path(args.output).stat().st_size / (1024 * 1024)
    print(f"  Size: {file_size_mb:.1f} MB")

    if args.hf_repo and not args.skip_push:
        push_to_hf(args.output, args.hf_repo)
        print(f"  HF: https://huggingface.co/{args.hf_repo}")

    print("\n=== Next: Hot-swap on production VPS ===")
    print(f"  ssh root@72.62.125.6")
    print(f"  cd /opt/ado")
    print(f"  ollama pull {args.hf_repo or 'migancore/migancore-7b-soul-v0.1'}")
    print(f"  # Update DEFAULT_MODEL in .env")
    print(f"  docker compose up -d --build api")


if __name__ == "__main__":
    main()
