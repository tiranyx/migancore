# MiganCore SFT Identity Anchor — Training Package

## What's Inside
- `identity_sft_200.jsonl` — 200 clean SFT pairs (identity/constitutional/ecosystem/voice)
- `train_sft_identity.py` — Unsloth + QLoRA training script with eval gates
- `requirements_train.txt` — Python dependencies
- `setup_gpu.sh` — One-command setup for Ubuntu GPU instances

## Quick Start: RunPod / Vast.ai (Recommended)

### 1. Rent GPU Instance
**RunPod**:
- Go to https://www.runpod.io/console/pods
- Select "Community Cloud" or "Secure Cloud"
- Template: `PyTorch 2.5 / CUDA 12.4` or `RunPod Pytorch 2.4`
- GPU: RTX 4090 (24GB) or A100 (40GB)
- Cost: ~$0.44/hr (RTX 4090), ~$1.99/hr (A100)
- Expected time: 2-4 hours

**Vast.ai**:
- Go to https://cloud.vast.ai/
- Search: `RTX 4090`, filter: CUDA >= 12.0
- Select image: `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime`

### 2. Upload Files
```bash
# From your local machine (after git clone or download)
scp -r train_package/ root@<INSTANCE_IP>:/root/
```

### 3. Setup & Train
```bash
ssh root@<INSTANCE_IP>
cd /root/train_package

# Option A: Auto setup
bash setup_gpu.sh
source venv/bin/activate

# Option B: Manual (if auto fails)
pip install -q torch==2.5.1 --index-url https://download.pytorch.org/whl/cu124
pip install -q -r requirements_train.txt

# Run training
python train_sft_identity.py \
  --dataset identity_sft_200.jsonl \
  --output-dir ./identity_adapter \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --epochs 5 \
  --lora-r 32 \
  --merge \
  --gguf
```

### 4. Monitor
Training logs will show:
- Loss per step (should drop from ~2.5 to <0.5)
- MMLU score (must not drop >3 points from baseline)
- Identity cosine similarity (must be >0.85)

### 5. Download Results
```bash
# On instance, after training:
tar czf migan_identity_v0.4.tar.gz identity_adapter/ merged_model/ *.gguf eval_report.json

# Download to local/VPS
scp root@<INSTANCE_IP>:/root/train_package/migan_identity_v0.4.tar.gz .
```

### 6. Deploy to Ollama (VPS)
```bash
# On VPS
scp migan_identity_v0.4.tar.gz sidix-vps:/opt/ado/models/
ssh sidix-vps
cd /opt/ado/models
tar xzf migan_identity_v0.4.tar.gz
# Create Modelfile and import to Ollama
docker compose exec ollama ollama create migancore:0.4 -f ./Modelfile
```

## Google Colab (Free T4) — Fallback
Open `MiganCore_SFT_Identity.ipynb` in Google Colab:
https://colab.research.google.com/

Upload the notebook, then Runtime → Change runtime type → GPU (T4).

**Warning**: Colab free may disconnect after ~12 hours. Training should complete in ~3 hours.

## Go / No-Go Criteria

| Metric | Threshold | Action if Fail |
|--------|-----------|----------------|
| Identity cosine sim | > 0.85 | Increase rank to 64, retrain |
| MMLU delta | < -3 points | Abort, reduce LR or epochs |
| Loss at end | < 0.5 | Continue to DPO stage |
| GGUF export | Success | Deploy to staging |

## Cost Estimate
- RunPod RTX 4090 (3 hrs): ~$1.32
- Vast.ai RTX 4090 (3 hrs): ~$0.90
- Google Colab: FREE
- Teacher API (dataset already generated): $0

## Support
If training fails, check:
1. `nvidia-smi` shows GPU
2. `torch.cuda.is_available()` returns True
3. Dataset file exists: `wc -l identity_sft_200.jsonl` → 200
4. HuggingFace cache has space: `df -h ~/.cache/huggingface`
