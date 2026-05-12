# MiganCore Identity SFT — Pipeline v2.0

**Status**: Dataset siap. Training menunggu GPU cloud (RunPod/Vast.ai).

---

## 📊 Dataset: `identity_sft_200_CLEAN.jsonl`

| Metric | Value |
|--------|-------|
| Total pairs | 205 |
| With system prompt | 137 (67%) |
| Empty system prompt | 68 (33%) |
| Bahasa Indonesia | 187 (91%) |
| Bahasa Mandarin | 18 (9%) |
| Unique responses | 106/205 (52%) |
| Competitor references | 12 (all = denial/comparison, ✅ correct) |

### Anti-Contamination Measures
- **Zero Anthropic/Claude identity claims** — tidak ada "saya Claude" atau "saya asisten AI"
- **Zero OpenAI/Google/DeepSeek identity** — tidak ada "saya ChatGPT" atau "saya Gemini"
- **Competitor names hanya muncul dalam konteks denial** — "saya BUKAN ChatGPT", "saya BUKAN Claude"
- **No meta-instructions** — tidak ada "jawab sebagai Mighan-Core" di dalam training data

### Response Categories
1. **Direct identity** (40%): "Saya Mighan-Core, ADO dari Tiranyx"
2. **Differentiation** (20%): "Kalau ChatGPT kalkulator, saya organisme"
3. **Technical depth** (15%): "Tiga lapisan: Otak, Syaraf, Jiwa"
4. **Philosophical** (15%): Creative responses untuk pertanyaan aneh
5. **Denial** (10%): "Saya bukan Claude. Saya Mighan-Core."

---

## 🚀 Training: `train_unsloth_identity.py`

### Hyperparameters (Locked)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Base model | Qwen2.5-7B-Instruct | Best 7B multilingual base |
| LoRA rank | 64 | Override identitas kuat (was 16-32) |
| LoRA alpha | 128 | 2x rank = scaling optimal |
| Epochs | 3 | Cegah overfit (was 5) |
| Learning rate | 2e-4 | Lebih tinggi untuk SFT identity |
| Batch size | 2 × 4 grad accum = 8 effective | RTX 4090 friendly |
| Max seq | 2048 | Cukup untuk identity pairs |
| Warmup | 10 steps | ~5% dari 200 steps total |
| LR schedule | Linear | Sederhana, predictable |
| Optimizer | AdamW 8-bit | Hemat VRAM |
| Mask prompt | True (SFTTrainer default) | Hanya assistant token dilatih |

### Hardware Requirements

| GPU | VRAM | Waktu | Biaya (Vast.ai) |
|-----|------|-------|-----------------|
| RTX 4090 | 24GB | ~30-45 min | ~$1.00 |
| A100 40GB | 40GB | ~15-20 min | ~$2.50 |
| A6000 | 48GB | ~20-30 min | ~$1.50 |

### Install Dependencies

```bash
pip install unsloth transformers datasets accelerate peft bitsandbytes trl
# Optional: MMLU eval
pip install lm-eval
```

### Run Training

```bash
# 1. SSH ke RunPod/Vast.ai instance
# 2. Copy dataset + script
scp identity_sft_200_CLEAN.jsonl train_unsloth_identity.py root@gpu-ip:/root/

# 3. Run
python train_unsloth_identity.py \
    --dataset identity_sft_200_CLEAN.jsonl \
    --output ./migancore_identity_v2 \
    --epochs 3 \
    --rank 64 \
    --alpha 128 \
    --lr 2e-4 \
    --mmlu

# 4. Output:
#    ./migancore_identity_v2/adapter/       # LoRA adapter
#    ./migancore_identity_v2/merged/        # Merged HF model
#    ./migancore_identity_v2/gguf/          # GGUF Q4_K_M untuk Ollama
#    ./migancore_identity_v2/eval_report.json
```

---

## ✅ Eval Gate (MANDATORY sebelum deploy)

### 1. Identity Pass Rate (Empty System Prompt)

```bash
# Test tanpa system prompt — ini yang sebenarnya menentukan
# apakah identitas sudah ter-embed di weights
ollama run migancore:0.8-clean -- "Siapa kamu?"
```

**Target**: ≥85% pass rate dengan empty system prompt
**Threshold deploy**: ≥70% (rollback ke 0.7c kalau di bawah)

### 2. MMLU Delta Check

| Baseline Qwen2.5-7B | Target | Action |
|---------------------|--------|--------|
| ~62-65% | ≥58% | ✅ Deploy |
| ~62-65% | 55-58% | ⚠️ Acceptable, monitor |
| ~62-65% | <55% | ❌ Catastrophic forgetting, stop |

### 3. Sample Output Quality

Run `identity_anchor_pipeline.py` untuk test comprehensive:
- 20 pertanyaan identity-probing
- Competitor denial test
- Creative/philosophical test
- Tool capability acknowledgment

---

## 📦 Deployment: `deploy_to_ollama.py`

```bash
# Setelah training selesai dan eval gate lulus:
python deploy_to_ollama.py \
    --gguf ./migancore_identity_v2/gguf/migancore-identity.q4_k_m.gguf \
    --tag migancore:0.8-clean

# Script akan:
# 1. Copy GGUF ke /opt/ado/data/ollama/models/
# 2. Create Modelfile
# 3. ollama create migancore:0.8-clean
# 4. Quick identity test
# 5. Update config.py, agents.json, docker-compose.yml
```

---

## 🔄 Rollback Plan

```bash
# Kalau 0.8-clean bermasalah:
ollama create migancore:0.7c -f /opt/ado/data/ollama/models/Modelfile.0.7c
# Update config.py, agents.json, docker-compose.yml ke 0.7c
systemctl restart ado-api
```

---

## 📁 File Inventory

| File | Purpose | Size |
|------|---------|------|
| `identity_sft_200_CLEAN.jsonl` | Clean SFT dataset | 62KB |
| `train_unsloth_identity.py` | Unsloth training script | 14KB |
| `train_sft_identity.py` | Standard TRL training (fallback) | 14KB |
| `deploy_to_ollama.py` | Deployment automation | 5KB |
| `Modelfile.migancore` | Ollama Modelfile template | 494B |
| `generate_identity_v3.py` | Dataset generator | 18KB |
| `verify_dataset.py` | Dataset validation | 1KB |

---

## 🎯 Lessons Applied

| Lesson | Issue | Fix in v2.0 |
|--------|-------|-------------|
| #170 | Identity fragile | Rank 64, 205 pairs, 3 epochs |
| #171 | ORPO wrong tool | SFT instead of ORPO/SimPO |
| #172 | No loss masking | SFTTrainer handles prompt masking |
| #173 | Catastrophic forgetting | MMLU eval gate, 3 epochs only |
| #174 | 99% synthetic data | Target 20% real in 2 weeks |
| #175 | Chat template mismatch | Verify Qwen2.5 template pre-flight |
| #186 | Wrong base model | Qwen2.5-7B-Instruct (confirmed base) |
| #187 | Contaminated data | Full audit, 12 competitor denials only |
| #188 | Eval with system prompt | 68 empty-system pairs, eval tanpa system |
| #189 | Multi-objective mixing | ONE objective: identity ONLY |
| #190 | Repetitive responses | 106 unique / 205, 50+ response templates |
