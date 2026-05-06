#!/usr/bin/env python3
"""MiganCore Day 56 — GGUF Fix: convert f16 + quantize Q4_K_M + upload
Run on Vast.ai after merge step completed.
Merged model already at /root/merged_soul (15.24 GB)
"""
import os, sys, time, subprocess, glob

HF_TOKEN = os.environ.get("HF_TOKEN", "")
if not HF_TOKEN:
    # Try reading from file
    try:
        with open("/root/hf_token") as f:
            HF_TOKEN = f.read().strip()
    except Exception:
        pass
if not HF_TOKEN:
    print("ERROR: HF_TOKEN not set")
    sys.exit(1)

print("=== MiganCore Day 56 GGUF Fix ===")
print("Start:", time.strftime("%Y-%m-%d %H:%M:%S"))

MERGED = "/root/merged_soul"
F16_GGUF = "/root/migancore-7b-soul-v0.1.f16.gguf"
Q4_GGUF = "/root/migancore-7b-soul-v0.1.q4_k_m.gguf"
LLAMA_CPP = "/root/llama.cpp"

# Verify merged model exists
assert os.path.isdir(MERGED), f"Merged model not found at {MERGED}"
size = sum(os.path.getsize(os.path.join(MERGED, f))
           for f in os.listdir(MERGED)) / 1e9
print(f"Merged model found: {size:.2f} GB at {MERGED}")

# Step 1: Convert to f16 GGUF
print("\n[1/4] Converting merged model to f16 GGUF...")
t0 = time.time()
result = subprocess.run(
    [sys.executable, f"{LLAMA_CPP}/convert_hf_to_gguf.py",
     MERGED,
     "--outfile", F16_GGUF,
     "--outtype", "f16"],
    capture_output=True, text=True
)
if result.returncode != 0:
    print("CONVERT f16 ERROR:", result.stderr[-1000:])
    sys.exit(1)
f16_size = os.path.getsize(F16_GGUF) / 1e9
print(f"f16 GGUF created: {f16_size:.2f} GB in {time.time()-t0:.0f}s")

# Step 2: Build llama-quantize
print("\n[2/4] Building llama-quantize...")
t1 = time.time()
# Try cmake build first
cmake_result = subprocess.run(
    ["cmake", "-B", f"{LLAMA_CPP}/build", "-S", LLAMA_CPP,
     "-DGGML_CUDA=ON", "-DCMAKE_BUILD_TYPE=Release"],
    capture_output=True, text=True, cwd=LLAMA_CPP
)
if cmake_result.returncode == 0:
    build_result = subprocess.run(
        ["cmake", "--build", f"{LLAMA_CPP}/build",
         "--target", "llama-quantize", "-j", str(os.cpu_count())],
        capture_output=True, text=True, cwd=LLAMA_CPP
    )
    quantize_bin = f"{LLAMA_CPP}/build/bin/llama-quantize"
    if build_result.returncode != 0:
        print("cmake build failed, trying make...")
        cmake_result = subprocess.CompletedProcess([], 1)

if cmake_result.returncode != 0:
    # Fallback: make
    make_result = subprocess.run(
        ["make", "llama-quantize", f"-j{os.cpu_count()}"],
        capture_output=True, text=True, cwd=LLAMA_CPP
    )
    quantize_bin = f"{LLAMA_CPP}/llama-quantize"
    if make_result.returncode != 0:
        print("Make also failed:", make_result.stderr[-500:])
        sys.exit(1)

print(f"llama-quantize built in {time.time()-t1:.0f}s at {quantize_bin}")
assert os.path.isfile(quantize_bin), f"Binary not found: {quantize_bin}"

# Step 3: Quantize to Q4_K_M
print("\n[3/4] Quantizing f16 → Q4_K_M...")
t2 = time.time()
q_result = subprocess.run(
    [quantize_bin, F16_GGUF, Q4_GGUF, "Q4_K_M"],
    capture_output=True, text=True
)
if q_result.returncode != 0:
    print("QUANTIZE ERROR:", q_result.stderr[-1000:])
    print("STDOUT:", q_result.stdout[-500:])
    sys.exit(1)
q4_size = os.path.getsize(Q4_GGUF) / 1e9
print(f"Q4_K_M GGUF: {q4_size:.2f} GB in {time.time()-t2:.0f}s")

# Validate GGUF magic
with open(Q4_GGUF, "rb") as f:
    magic = f.read(4)
assert magic == b"GGUF", f"INVALID GGUF! magic={magic}"
print("GGUF VALID ✓")

# Clean up f16 to save disk space
print(f"Removing f16 GGUF ({f16_size:.2f} GB) to free disk...")
os.remove(F16_GGUF)
print("Cleaned up.")

# Step 4: Upload to HF
print("\n[4/4] Uploading Q4_K_M to Hugging Face...")
from huggingface_hub import HfApi
api = HfApi(token=HF_TOKEN)

try:
    api.create_repo("Tiranyx/migancore-7b-soul-v0.1-gguf",
                    repo_type="model", exist_ok=True, private=False)
    print("Repo ready.")
except Exception as e:
    print(f"Repo create warning: {e}")

print(f"Uploading {q4_size:.2f} GB GGUF...")
t3 = time.time()
url = api.upload_file(
    path_or_fileobj=Q4_GGUF,
    path_in_repo="migancore-7b-soul-v0.1.q4_k_m.gguf",
    repo_id="Tiranyx/migancore-7b-soul-v0.1-gguf",
    commit_message="Day 56: GGUF Q4_K_M from Cycle 1 DPO adapter (soul-v0.1)"
)
print(f"UPLOAD COMPLETE in {time.time()-t3:.0f}s!")
print(f"URL: {url}")
print(f"HF page: https://huggingface.co/Tiranyx/migancore-7b-soul-v0.1-gguf")
print(f"\n=== ALL DONE! Total time: {time.time()-t0:.0f}s ===")
