#!/usr/bin/env bash
# =============================================================================
# MiganCore Day 56 — Adapter Merge + GGUF Convert Script
# Run this INSIDE RunPod A100 pod (volume 42hjavzigv mounted at /workspace)
# =============================================================================
# Expected duration: 35-50 min on A100 SXM 80GB
# Expected cost: ~$0.87-1.25 (A100 @ $1.49/hr)
# Output: /workspace/migancore-7b-soul-v0.1.q4_k_m.gguf (~4.7GB)
# Upload: HF repo Tiranyx/migancore-7b-soul-v0.1-gguf
# =============================================================================

set -e  # Exit on any error
# HF_TOKEN: set via environment variable BEFORE running this script.
# On RunPod pod, set it like: export HF_TOKEN="hf_..."
# Token saved on VPS at /opt/secrets/migancore/hf_token (for reference during VPS steps)
if [ -z "$HF_TOKEN" ]; then
    echo "ERROR: HF_TOKEN environment variable not set."
    echo "Run: export HF_TOKEN='hf_...' before executing this script."
    exit 1
fi

echo "================================================"
echo "MIGANCORE DAY 56 — MERGE + CONVERT"
echo "Start time: $(date)"
echo "================================================"

# --- PRE-FLIGHT CHECKS ---
echo ""
echo "[1/6] PRE-FLIGHT CHECKS"
echo "Disk space:"
df -h /workspace
echo ""

# Auto-discover snapshot ID
SNAPSHOT=$(ls /workspace/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/ 2>/dev/null | head -1)
if [ -z "$SNAPSHOT" ]; then
    echo "ERROR: Qwen base model not found in volume. Expected at:"
    echo "  /workspace/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/"
    echo "Listing /workspace/hub/:"
    ls /workspace/hub/ 2>/dev/null || echo "  (empty or missing)"
    exit 1
fi
BASE_PATH="/workspace/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/$SNAPSHOT"
echo "Base model snapshot: $SNAPSHOT"
echo "Base path: $BASE_PATH"

# Check adapter
ADAPTER_PATH="/workspace/r9_manual"
if [ ! -f "$ADAPTER_PATH/adapter_model.safetensors" ]; then
    echo "ERROR: Adapter not found at $ADAPTER_PATH"
    echo "Listing /workspace/:"
    ls /workspace/ 2>/dev/null
    exit 1
fi
echo "Adapter found: $ADAPTER_PATH/adapter_model.safetensors ($(du -sh $ADAPTER_PATH/adapter_model.safetensors | cut -f1))"

echo ""
echo "[2/6] INSTALL DEPENDENCIES"
pip install -q peft transformers accelerate bitsandbytes huggingface_hub
echo "Dependencies installed."

# Clone llama.cpp if not present
if [ ! -d "/workspace/llama.cpp" ]; then
    echo ""
    echo "[3/6] CLONE LLAMA.CPP"
    git clone --depth=1 https://github.com/ggerganov/llama.cpp /workspace/llama.cpp
    cd /workspace/llama.cpp && pip install -q -r requirements.txt
    echo "llama.cpp ready."
else
    echo "[3/6] llama.cpp already present — skipping clone"
    cd /workspace/llama.cpp && pip install -q -r requirements.txt
fi

# --- MERGE ---
echo ""
echo "[4/6] MERGE LoRA INTO BASE MODEL"
echo "This takes ~15-20 min on A100 80GB (CPU mode, bfloat16)"

python3 << 'PYEOF'
import os, sys, time, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE_PATH = None
SNAPSHOT = os.popen("ls /workspace/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/ | head -1").read().strip()
BASE_PATH = f"/workspace/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/{SNAPSHOT}"
ADAPTER_PATH = "/workspace/r9_manual"
OUT_PATH = "/workspace/merged_soul"

print(f"Base: {BASE_PATH}")
print(f"Adapter: {ADAPTER_PATH}")
print(f"Output: {OUT_PATH}")

print("\nLoading base model (bfloat16, CPU)...")
t0 = time.time()
base = AutoModelForCausalLM.from_pretrained(
    BASE_PATH,
    torch_dtype=torch.bfloat16,
    device_map="cpu",
    trust_remote_code=True,
)
print(f"Base loaded in {time.time()-t0:.0f}s. Params: {sum(p.numel() for p in base.parameters())/1e9:.2f}B")

print("\nApplying LoRA adapter...")
peft_m = PeftModel.from_pretrained(base, ADAPTER_PATH)

print("Merging and unloading...")
merged = peft_m.merge_and_unload()
print(f"Merged. Total params: {sum(p.numel() for p in merged.parameters())/1e9:.2f}B")

print(f"\nSaving merged model to {OUT_PATH}...")
merged.save_pretrained(OUT_PATH, safe_serialization=True)
tok = AutoTokenizer.from_pretrained(BASE_PATH, trust_remote_code=True)
tok.save_pretrained(OUT_PATH)
print(f"Merge complete. Total time: {time.time()-t0:.0f}s")
print(f"Merged model size: {sum(os.path.getsize(os.path.join(OUT_PATH,f)) for f in os.listdir(OUT_PATH))/1e9:.2f} GB")
PYEOF

echo "Merge done. Checking output:"
ls -lh /workspace/merged_soul/

# --- CONVERT TO GGUF ---
echo ""
echo "[5/6] CONVERT TO GGUF (Q4_K_M)"
echo "This takes ~8-12 min on A100"

python3 /workspace/llama.cpp/convert_hf_to_gguf.py \
    /workspace/merged_soul \
    --outfile /workspace/migancore-7b-soul-v0.1.q4_k_m.gguf \
    --outtype q4_k_m

echo ""
echo "GGUF created:"
ls -lh /workspace/migancore-7b-soul-v0.1.q4_k_m.gguf

# Quick sanity: GGUF magic bytes check
python3 -c "
f = open('/workspace/migancore-7b-soul-v0.1.q4_k_m.gguf','rb')
magic = f.read(4)
f.close()
print('GGUF magic bytes:', magic.hex(), '| Expected: 47475546')
assert magic == b'GGUF', f'INVALID GGUF! magic={magic}'
print('GGUF file VALID.')
"

# --- UPLOAD TO HF ---
echo ""
echo "[6/6] UPLOAD TO HUGGING FACE"
echo "Repo: Tiranyx/migancore-7b-soul-v0.1-gguf"

python3 << PYEOF
from huggingface_hub import HfApi
import os

TOKEN = "$HF_TOKEN"
api = HfApi(token=TOKEN)

# Create repo if doesn't exist
try:
    api.create_repo(
        repo_id="Tiranyx/migancore-7b-soul-v0.1-gguf",
        repo_type="model",
        exist_ok=True,
        private=False,
    )
    print("Repo ready: Tiranyx/migancore-7b-soul-v0.1-gguf")
except Exception as e:
    print(f"Repo create warning (may already exist): {e}")

# Upload GGUF
gguf_path = "/workspace/migancore-7b-soul-v0.1.q4_k_m.gguf"
size_gb = os.path.getsize(gguf_path)/1e9
print(f"Uploading {gguf_path} ({size_gb:.2f} GB)...")
url = api.upload_file(
    path_or_fileobj=gguf_path,
    path_in_repo="migancore-7b-soul-v0.1.q4_k_m.gguf",
    repo_id="Tiranyx/migancore-7b-soul-v0.1-gguf",
    repo_type="model",
    commit_message="Day 56: GGUF Q4_K_M from Cycle 1 DPO adapter (soul-v0.1)",
)
print(f"Upload complete! URL: {url}")
PYEOF

echo ""
echo "================================================"
echo "DONE. Summary:"
echo "- Merged model: /workspace/merged_soul/ (~15GB, can delete after verify)"
echo "- GGUF: /workspace/migancore-7b-soul-v0.1.q4_k_m.gguf"
echo "- HF repo: https://huggingface.co/Tiranyx/migancore-7b-soul-v0.1-gguf"
echo ""
echo "NEXT STEP (on VPS):"
echo "  huggingface-cli download Tiranyx/migancore-7b-soul-v0.1-gguf \\"
echo "    migancore-7b-soul-v0.1.q4_k_m.gguf --local-dir /opt/ado/models/"
echo "  ollama create migancore:0.1 -f /opt/ado/Modelfile"
echo "  docker exec ado-ollama-1 ollama list"
echo ""
echo "End time: $(date)"
echo "================================================"
