#!/usr/bin/env python3
"""Download GGUF from HF to VPS /opt/ado/models/"""
import os, time, sys
os.makedirs("/opt/ado/models", exist_ok=True)

token = open("/opt/secrets/migancore/hf_token").read().strip()
print(f"Token: {token[:8]}...ok")

# Install/update huggingface_hub
import subprocess
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "huggingface_hub"], check=True)

from huggingface_hub import hf_hub_download
print("Downloading migancore-7b-soul-v0.1.q4_k_m.gguf (~4.68 GB)...")
t0 = time.time()
path = hf_hub_download(
    repo_id="Tiranyx/migancore-7b-soul-v0.1-gguf",
    filename="migancore-7b-soul-v0.1.q4_k_m.gguf",
    local_dir="/opt/ado/models",
    token=token
)
elapsed = time.time() - t0
size = os.path.getsize(path) / 1e9
print(f"DOWNLOADED: {path}")
print(f"Size: {size:.2f} GB in {elapsed:.0f}s")
