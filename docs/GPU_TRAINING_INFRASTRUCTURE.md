# MiganCore GPU Training Infrastructure

## Overview
Dokumentasi setup dan penggunaan GPU cloud untuk training MiganCore brain models.

## Platform

### Vast.ai (Primary)
- **Credit**: $8.26 (as of May 2026)
- **API Key**: `REDACTED_VASTAI_KEY`
- **Cost**: ~$0.41/hr (RTX 4090)
- **Docs**: https://cloud.vast.ai/cli/
- **Guides**: https://docs.vast.ai/guides/get-started

#### CLI Setup
```bash
pip install --upgrade vastai
vastai set api-key <api_key>
vastai search offers --limit 3
```

#### Create Instance
```bash
vastai create instance <offer_id> --image pytorch/pytorch --disk 50 --ssh --direct
```

#### SSH Access
```bash
ssh -p <ssh_port> root@<ssh_host>
```

### RunPod (Alternative)
- **Credit**: $14.37 (as of May 2026)
- **API Key**: `REDACTED_RUNPOD_KEY`
- **Cost**: ~$0.44/hr (RTX 4090 Community)
- **Docs**: https://docs.runpod.io/overview

#### Python SDK Setup
```bash
pip install runpod
```

#### Create Pod
```python
import runpod
runpod.api_key = 'your_api_key'

pod = runpod.create_pod(
    name='migan-training',
    image_name='pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime',
    gpu_type_id='NVIDIA GeForce RTX 4090',
    cloud_type='COMMUNITY',
    volume_in_gb=50,
    ports='22/tcp',
)
```

## Training Workflow

### 1. Prepare Training Package
```bash
# Generate dataset
docker compose exec api python /app/scripts/generate_identity_anchor_dataset.py \
  --output /app/workspace/identity_sft_200.jsonl

# Copy from container
docker compose cp api:/app/workspace/identity_sft_200.jsonl ./workspace/

# Create package
tar czf train_package.tar.gz train_package/
```

### 2. Deploy to GPU Instance
```bash
# Upload to instance
scp -P <port> train_package.tar.gz root@<host>:/root/

# Extract and setup
ssh -p <port> root@<host> 'tar xzf train_package.tar.gz && bash setup_gpu.sh'
```

### 3. Run Training
```bash
ssh -p <port> root@<host> 'source /opt/conda/bin/activate migan && \
  python3 train_sft_identity.py \
  --dataset identity_sft_200.jsonl \
  --output-dir ./identity_adapter \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --epochs 5 --lora-r 32 --merge --gguf'
```

### 4. Download Results
```bash
scp -P <port> root@<host>:/root/identity_adapter_pkg.tar.gz .
```

## Environment Best Practices

### Clean Conda Environment (Recommended)
Base images often have corrupted/incompatible PyTorch versions. Always create fresh env:
```bash
conda create -n migan python=3.11 -y
source /opt/conda/bin/activate migan
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 \
  --index-url https://download.pytorch.org/whl/cu124
pip install transformers==4.46.3 datasets trl peft accelerate bitsandbytes
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
```

### Disk Management
- 50GB disk fills up quickly with 7B models
- Clean checkpoints after training: `rm -rf checkpoint-*`
- Base model cache: `~/.cache/huggingface/hub/`
- Merged model: ~14GB (bf16)
- GGUF Q4_K_M: ~4GB

### Common Issues
1. **PyTorch version mismatch**: Use clean conda env
2. **torchao incompatibility**: Downgrade transformers to 4.46.3
3. **TRL API changes**: `tokenizer` → `processing_class`, `max_seq_length` → `max_length` in SFTConfig
4. **Disk full during merge**: Delete checkpoints first

## Cost Tracking

| Platform | GPU | Rate | 4hr Training | Notes |
|----------|-----|------|--------------|-------|
| Vast.ai | RTX 4090 | $0.41/hr | ~$1.64 | Cheaper, variable reliability |
| RunPod | RTX 4090 | $0.44/hr | ~$1.76 | Better UI, more reliable |
| Colab | T4 | FREE | $0 | May disconnect, 12hr limit |

## SSH Key Management

### RunPod
Add SSH public key in Settings → SSH public keys

### Vast.ai
Use `vastai attach ssh` or connect directly with instance credentials

## References
- Vast.ai CLI: https://cloud.vast.ai/cli/
- Vast.ai Docs: https://docs.vast.ai/guides/get-started
- RunPod Docs: https://docs.runpod.io/overview
- RunPod Python SDK: https://github.com/runpod/runpod-python
