#!/bin/bash
# MiganCore SFT Identity Anchor — GPU Setup Script
# Run on: RunPod / Vast.ai / any Ubuntu 22.04+ with NVIDIA GPU
# Usage: bash setup_gpu.sh

set -euo pipefail

echo "=== MiganCore SFT Identity Anchor Setup ==="
echo "Date: $(date)"
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"

# 1. System deps
echo "[1/6] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq git curl wget python3-pip python3-venv unzip > /dev/null

# 2. Create workspace
echo "[2/6] Creating workspace..."
mkdir -p /root/migan_train
cd /root/migan_train

# 3. Python venv
echo "[3/6] Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip

# 4. Install PyTorch with CUDA 12.4
echo "[4/6] Installing PyTorch + CUDA..."
pip install -q torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124

# 5. Install training deps
echo "[5/6] Installing training dependencies..."
pip install -q -r requirements_train.txt

# 6. Verify
echo "[6/6] Verification..."
python3 -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}')"
python3 -c "import unsloth; print(f'Unsloth: OK')"

echo ""
echo "=== Setup Complete ==="
echo "Workspace: /root/migan_train"
echo ""
echo "Next steps:"
echo "  1. Upload dataset: identity_sft_200.jsonl"
echo "  2. Upload script: train_sft_identity.py"
echo "  3. Run training:"
echo "     source venv/bin/activate"
echo "     python train_sft_identity.py \\"
echo "       --dataset identity_sft_200.jsonl \\"
echo "       --output-dir ./identity_adapter \\"
echo "       --base-model Qwen/Qwen2.5-7B-Instruct \\"
echo "       --epochs 5 \\"
echo "       --lora-r 32 \\"
echo "       --merge \\"
echo "       --gguf"
echo ""
