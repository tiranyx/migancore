#!/usr/bin/env python3
"""MiganCore Day 56 — Vast.ai Merge + Convert + Upload
Run on Vast.ai instance with: HF_TOKEN=... python3 vastai_day56.py
"""
import os, time, sys, subprocess, glob

HF_TOKEN = os.environ.get("HF_TOKEN", "")
if not HF_TOKEN:
    print("ERROR: HF_TOKEN environment variable not set")
    sys.exit(1)

print("=== MiganCore Day 56 Vast.ai Merge+Convert ===")
print("Start:", time.strftime("%Y-%m-%d %H:%M:%S"))
print("Python:", sys.version)
print()

# 1. Install deps
print("[1/7] Installing packages...")
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
    "peft", "transformers", "accelerate", "huggingface_hub"], check=True)
print("Packages installed.")

# 2. Clone llama.cpp
print("\n[2/7] llama.cpp setup...")
if not os.path.exists("/root/llama.cpp"):
    subprocess.run(["git", "clone", "--depth=1",
        "https://github.com/ggerganov/llama.cpp", "/root/llama.cpp"], check=True)
else:
    print("llama.cpp already present, skipping clone.")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
    "/root/llama.cpp/requirements.txt"], check=True)

# 3. Download Qwen2.5-7B-Instruct base (15GB)
print("\n[3/7] Downloading Qwen2.5-7B-Instruct (~15GB)...")
from huggingface_hub import snapshot_download
t0 = time.time()
qwen_dir = snapshot_download(
    "Qwen/Qwen2.5-7B-Instruct",
    local_dir="/root/qwen_base",
    ignore_patterns=["*.msgpack", "*.h5", "flax_model*", "tf_model*", "onnx*"]
)
elapsed = time.time() - t0
print(f"Qwen downloaded to {qwen_dir} in {elapsed:.0f}s")
print("Contents:", os.listdir(qwen_dir)[:10])

# 4. Download adapter (Tiranyx/migancore-7b-soul-v0.1)
print("\n[4/7] Downloading LoRA adapter from HF...")
adapter_dir = snapshot_download(
    "Tiranyx/migancore-7b-soul-v0.1",
    local_dir="/root/adapter",
    token=HF_TOKEN,
    ignore_patterns=["*.msgpack"]
)
adapter_files = glob.glob("/root/adapter/*.safetensors")
print(f"Adapter: {adapter_files}")
if not adapter_files:
    print("ERROR: No safetensors found in adapter")
    sys.exit(1)

# 5. Merge LoRA into base
print("\n[5/7] Merging LoRA (bfloat16, CPU). ~15-25 min...")
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

t1 = time.time()
print("  Loading base model...")
base = AutoModelForCausalLM.from_pretrained(
    "/root/qwen_base",
    torch_dtype=torch.bfloat16,
    device_map="cpu",
    trust_remote_code=True
)
n_params = sum(p.numel() for p in base.parameters())
print(f"  Base loaded: {n_params/1e9:.2f}B params | RAM used: {time.time()-t1:.0f}s")

print("  Applying LoRA adapter...")
peft_m = PeftModel.from_pretrained(base, "/root/adapter")
print("  Merging and unloading...")
merged = peft_m.merge_and_unload()
print(f"  Merged in {time.time()-t1:.0f}s. Saving...")

merged.save_pretrained("/root/merged_soul", safe_serialization=True)
AutoTokenizer.from_pretrained("/root/qwen_base", trust_remote_code=True).save_pretrained("/root/merged_soul")
total_size = sum(os.path.getsize(os.path.join("/root/merged_soul", f))
                 for f in os.listdir("/root/merged_soul")) / 1e9
print(f"  Saved to /root/merged_soul ({total_size:.2f} GB) | Total: {time.time()-t1:.0f}s")

# 6. Convert to GGUF Q4_K_M
print("\n[6/7] Converting to GGUF Q4_K_M...")
result = subprocess.run(
    [sys.executable, "/root/llama.cpp/convert_hf_to_gguf.py",
     "/root/merged_soul",
     "--outfile", "/root/migancore-7b-soul-v0.1.q4_k_m.gguf",
     "--outtype", "q4_k_m"],
    capture_output=True, text=True
)
if result.returncode != 0:
    print("GGUF CONVERT ERROR:", result.stderr[-500:])
    sys.exit(1)
print(result.stdout[-300:] if result.stdout else "No stdout")

gguf_size = os.path.getsize("/root/migancore-7b-soul-v0.1.q4_k_m.gguf") / 1e9
print(f"GGUF size: {gguf_size:.2f} GB")

# Validate GGUF magic bytes
with open("/root/migancore-7b-soul-v0.1.q4_k_m.gguf", "rb") as f:
    magic = f.read(4)
assert magic == b"GGUF", f"INVALID GGUF! magic={magic}"
print("GGUF VALID ✓")

# 7. Upload to Hugging Face
print("\n[7/7] Uploading to Hugging Face...")
from huggingface_hub import HfApi
api = HfApi(token=HF_TOKEN)

try:
    api.create_repo(
        "Tiranyx/migancore-7b-soul-v0.1-gguf",
        repo_type="model",
        exist_ok=True,
        private=False
    )
    print("Repo ready.")
except Exception as e:
    print(f"Repo create warning (may exist): {e}")

print(f"Uploading {gguf_size:.2f}GB GGUF file...")
url = api.upload_file(
    path_or_fileobj="/root/migancore-7b-soul-v0.1.q4_k_m.gguf",
    path_in_repo="migancore-7b-soul-v0.1.q4_k_m.gguf",
    repo_id="Tiranyx/migancore-7b-soul-v0.1-gguf",
    commit_message="Day 56: GGUF Q4_K_M from Cycle 1 DPO adapter (soul-v0.1)"
)
print(f"UPLOAD COMPLETE!")
print(f"URL: {url}")
print(f"HF page: https://huggingface.co/Tiranyx/migancore-7b-soul-v0.1-gguf")
print(f"\n=== ALL DONE! Total time: {time.time()-t0:.0f}s ===")
