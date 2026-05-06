#!/usr/bin/env python3
"""MiganCore Day 56 — Final GGUF convert + upload.
Skips merge (merged_soul already at /root/merged_soul).
Skips cmake (llama-quantize already at /root/llama.cpp/build/bin/llama-quantize).
"""
import os, sys, time, subprocess

LOG = open("/root/final_log.txt", "w", buffering=1)  # line-buffered

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()

log("=== MiganCore Day 56 Final: GGUF Convert + Upload ===")

HF_TOKEN = os.environ.get("HF_TOKEN", "")
if not HF_TOKEN:
    try:
        HF_TOKEN = open("/root/hf_token").read().strip()
    except Exception:
        pass
if not HF_TOKEN:
    log("ERROR: HF_TOKEN not set and /root/hf_token not found")
    sys.exit(1)
log(f"HF_TOKEN: {HF_TOKEN[:8]}...ok")

MERGED = "/root/merged_soul"
F16_GGUF = "/root/migancore-soul-v0.1.f16.gguf"
Q4_GGUF = "/root/migancore-7b-soul-v0.1.q4_k_m.gguf"
QUANTIZE = "/root/llama.cpp/build/bin/llama-quantize"
CONVERT = "/root/llama.cpp/convert_hf_to_gguf.py"

# Pre-flight
assert os.path.isdir(MERGED), f"merged_soul not found at {MERGED}"
assert os.path.isfile(QUANTIZE), f"llama-quantize not found at {QUANTIZE}"
assert os.path.isfile(CONVERT), f"convert_hf_to_gguf.py not found at {CONVERT}"
ms_size = sum(os.path.getsize(os.path.join(MERGED, f))
              for f in os.listdir(MERGED)) / 1e9
log(f"merged_soul: {ms_size:.2f} GB — OK")

# Step 1: Convert to f16 GGUF
log(f"[1/3] Converting merged_soul → f16 GGUF...")
t0 = time.time()
r = subprocess.run(
    [sys.executable, CONVERT, MERGED,
     "--outfile", F16_GGUF, "--outtype", "f16"],
    capture_output=False  # let it stream directly
)
if r.returncode != 0:
    log(f"CONVERT FAILED (exit {r.returncode})")
    sys.exit(1)
f16_size = os.path.getsize(F16_GGUF) / 1e9
log(f"f16 GGUF: {f16_size:.2f} GB in {time.time()-t0:.0f}s")

# Step 2: Quantize f16 → Q4_K_M
log(f"[2/3] Quantizing f16 → Q4_K_M...")
t1 = time.time()
r2 = subprocess.run([QUANTIZE, F16_GGUF, Q4_GGUF, "Q4_K_M"],
                    capture_output=False)
if r2.returncode != 0:
    log(f"QUANTIZE FAILED (exit {r2.returncode})")
    sys.exit(1)
q4_size = os.path.getsize(Q4_GGUF) / 1e9
log(f"Q4_K_M GGUF: {q4_size:.2f} GB in {time.time()-t1:.0f}s")

# Validate magic bytes
with open(Q4_GGUF, "rb") as f:
    magic = f.read(4)
assert magic == b"GGUF", f"INVALID GGUF magic: {magic}"
log("GGUF VALID ✓")

# Free f16
log(f"Removing f16 GGUF ({f16_size:.2f} GB)...")
os.remove(F16_GGUF)
log("f16 removed.")

# Step 3: Upload to HF
log(f"[3/3] Uploading {q4_size:.2f} GB to Hugging Face...")
from huggingface_hub import HfApi
api = HfApi(token=HF_TOKEN)
try:
    api.create_repo("Tiranyx/migancore-7b-soul-v0.1-gguf",
                    repo_type="model", exist_ok=True, private=False)
    log("Repo ready.")
except Exception as e:
    log(f"Repo warning: {e}")

t2 = time.time()
url = api.upload_file(
    path_or_fileobj=Q4_GGUF,
    path_in_repo="migancore-7b-soul-v0.1.q4_k_m.gguf",
    repo_id="Tiranyx/migancore-7b-soul-v0.1-gguf",
    commit_message="Day 56: GGUF Q4_K_M from Cycle 1 DPO adapter"
)
log(f"UPLOAD COMPLETE in {time.time()-t2:.0f}s")
log(f"URL: {url}")
log(f"HF: https://huggingface.co/Tiranyx/migancore-7b-soul-v0.1-gguf")
log(f"=== DONE total={time.time()-t0:.0f}s ===")
LOG.close()
