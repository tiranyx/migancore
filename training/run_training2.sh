#!/bin/bash
set -e
cd /root
echo "=== MiganCore SFT Training Started at $(date) ===" | tee training.log

echo "[1/3] Installing dependencies..." | tee -a training.log
pip install -q transformers datasets trl unsloth peft accelerate bitsandbytes sentencepiece protobuf scipy scikit-learn tqdm huggingface_hub 2>&1 | tee -a training.log

echo "[2/3] Verifying environment..." | tee -a training.log
python3 -c "import torch; print('PyTorch', torch.__version__, 'CUDA', torch.cuda.is_available(), torch.cuda.get_device_name(0))" | tee -a training.log
python3 -c "import unsloth; print('Unsloth OK')" | tee -a training.log

echo "[3/3] Running SFT training..." | tee -a training.log
python3 train_sft_identity.py \
  --dataset identity_sft_200.jsonl \
  --output-dir ./identity_adapter \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --epochs 5 \
  --lora-r 32 \
  --merge \
  --gguf \
  2>&1 | tee -a training.log

echo "=== Training Complete at $(date) ===" | tee -a training.log

echo "Compressing results..." | tee -a training.log
tar czf migan_identity_results.tar.gz identity_adapter/ merged_model/ *.gguf eval_report.json 2>/dev/null || echo "Some files missing"

echo "Done! Results ready." | tee -a training.log
