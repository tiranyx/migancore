#!/bin/bash
set -e
cd /root

echo "=== Fixing PyTorch and Starting Training ==="
echo "Current torch: $(python3 -c 'import torch; print(torch.__version__)')"

echo "[1/4] Installing deps (this may reinstall torch)..."
pip install -q transformers datasets trl unsloth peft accelerate bitsandbytes sentencepiece protobuf scipy scikit-learn tqdm huggingface_hub 2>&1 | tail -5

echo "[2/4] Force reinstalling PyTorch 2.5.1+cu124..."
pip install -q --force-reinstall torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124

echo "[3/4] Verifying CUDA..."
python3 -c "import torch; print('PyTorch', torch.__version__, 'CUDA', torch.cuda.is_available(), torch.cuda.get_device_name(0))"

echo "[4/4] Running SFT training..."
python3 train_sft_identity.py \
  --dataset identity_sft_200.jsonl \
  --output-dir ./identity_adapter \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --epochs 5 \
  --lora-r 32 \
  --merge \
  --gguf \
  2>&1 | tee training.log

echo "=== Training Complete ==="
tar czf migan_identity_results.tar.gz identity_adapter/ merged_model/ *.gguf eval_report.json 2>/dev/null || echo "Some files missing"
echo "Done!"
