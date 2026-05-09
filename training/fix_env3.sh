#!/bin/bash
set -e
cd /root

source /opt/conda/bin/activate migan || (conda create -n migan python=3.11 -y && source /opt/conda/bin/activate migan)

echo "Installing PyTorch 2.5.1+cu124..."
pip install -q torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124

echo "Installing deps without torchao..."
pip install -q transformers==4.46.3 datasets trl peft accelerate bitsandbytes sentencepiece protobuf scipy scikit-learn tqdm huggingface_hub

echo "Installing unsloth (compatible version)..."
pip install -q "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"

echo "Removing torchao if installed..."
pip uninstall -y torchao 2>/dev/null || true

echo "Verifying..."
python3 -c "import torch; print('torch:', torch.__version__, 'cuda:', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
python3 -c "import unsloth; print('unsloth OK')"

echo "Running training..."
python3 train_sft_identity.py \
  --dataset identity_sft_200.jsonl \
  --output-dir ./identity_adapter \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --epochs 5 \
  --lora-r 32 \
  --merge \
  --gguf \
  2>&1 | tee training.log

echo "Compressing..."
tar czf migan_identity_results.tar.gz identity_adapter/ merged_model/ *.gguf eval_report.json 2>/dev/null || echo "Some files missing"
echo "Done!"
