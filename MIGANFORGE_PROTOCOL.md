⚠️ WARNING — UPDATED Day 72e
Base model changed from Qwen/Qwen2.5-7B-Instruct → migancore:0.7c
See: LESSONS_LEARNED.md #186 (DPO from base Qwen overwrites identity)
See: KIMI_MAPPING_REMEDIATION_2026-05-12.md Section 2

Original protocol trained from base Qwen = identity collapse.
All future training MUST start from production checkpoint.

# MIGANFORGE PROTOCOL — Closed-Loop Self-Improvement

> Version: 1.0 | Date: 2026-05-11 | Day 72e | Analyst: Kimi Code CLI
> Status: DATA EXPORTED → Training Package Ready → Awaiting GPU

---

## EXECUTIVE SUMMARY

**MiganForge** is the closed-loop training infrastructure for MiganCore ADO. It transforms collected preference pairs into a measurably better model through DPO training, evaluation, and hot-deployment.

**Current State:**
- ✅ Data exported: 1,002 DPO pairs + 5 identity SFT examples
- ✅ Training script: DPO + QLoRA + SFT warm-start
- ✅ Evaluation: 10-category MT-bench (ID + EN)
- ✅ Deployment: HF → GGUF → Ollama hot-swap
- ✅ Orchestrator: State machine with dry-run, rollback, monitoring
- ⏳ Training execution: Requires cloud GPU (RunPod/Vast/Colab)

---

## PHASE 1: DATA EXTRACTION ✅ COMPLETE

### 1.1 Exported Dataset
```
Location: /opt/ado/data/training_new/
Files:
  dpo_export.jsonl          (2.3 MB, 1,002 pairs)
  identity_sft.jsonl        (1.9 KB, 5 examples)
  export_summary.json       (metadata)
```

### 1.2 Dataset Composition
| Source | Count | Avg Judge Score | Date Range |
|--------|-------|-----------------|------------|
| synthetic_seed_v1 | 986 | 3.0 | 2026-05-03 → 2026-05-07 |
| cai_pipeline | 16 | 3.0 | 2026-05-03 → 2026-05-07 |
| **Total** | **1,002** | **3.0** | |

### 1.3 Quality Assessment
- **Judge models**: migancore:0.3, migancore:0.2, qwen2.5:7b-instruct-q4_K_M
- **Score distribution**: All pairs have judge_score ≥ 3.0
- **Unused pairs only**: exclude_used=True (fresh data)
- **Identity anchor**: 5 curated prompts for persona consistency

### 1.4 Analysis Notes
- **986 synthetic pairs** (98.4%) vs **16 CAI pairs** (1.6%)
- **Imbalance concern**: Heavy reliance on synthetic data
- **Recommendation**: Increase CAI sampling rate for beta tenants to get more real-user signal
- **No distillation_worker pairs** yet: Pipeline collects but hasn't generated DPO format from teachers

---

## PHASE 2: TRAINING EXECUTION ⏳ AWAITING GPU

### 2.1 Hardware Requirements
| Config | GPU | VRAM | Time | Cost |
|--------|-----|------|------|------|
| QLoRA (recommended) | RTX 4090 | 24GB | ~2-3 hours | ~$1.50 |
| QLoRA | A100 | 40GB | ~1-2 hours | ~$2.50 |
| FP16 LoRA | A100 | 40GB | ~1 hour | ~$2.50 |

### 2.2 Training Configuration
```yaml
Base model: migancore:0.7c (HF checkpoint)  # CHANGED from Qwen — see Lesson #186
Method: DPO (Direct Preference Optimization)
Warm-start: SFT identity from 0.7c (NOT base Qwen) — 3 epochs
LoRA: r=16, alpha=32, dropout=0.05
QLoRA: 4-bit NF4 (load_in_4bit=true)
Batch: 1 × grad_accum=4 = effective batch 4
Learning rate: 5e-6
Beta: 0.1
Max length: 2048
Epochs: 1
Optimizer: paged_adamw_8bit (QLoRA)
```

### 2.3 Execution Commands

**Option A: RunPod (Recommended)**
```bash
# 1. Install runpodctl
pip install runpodctl

# 2. Login
runpodctl config --apiKey $RUNPOD_API_KEY

# 3. Upload data
runpodctl send /opt/ado/data/training_new/

# 4. Create pod with PyTorch image
runpodctl create pod \
  --gpuType "NVIDIA RTX 4090" \
  --imageName "runpod/pytorch:2.1.0-py3.10-cuda11.8-devel-ubuntu22.04" \
  --containerDiskSize 50 \
  --volumeSize 50 \
  --env "PYTHONUNBUFFERED=1"

# 5. SSH into pod and run training
runpodctl ssh <pod-id>

# Inside pod:
pip install torch transformers datasets trl peft accelerate bitsandbytes
python -m training.dpo_trainer \
  --dpo-data /data/dpo_export.jsonl \
  --identity-data /data/identity_sft.jsonl \
  --output-dir /data/migancore_dpo_v1 \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --qlora --epochs 1 --merge \
  --version migancore:0.5
```

**Option B: Google Colab (Free)**
```python
# Upload dpo_export.jsonl and identity_sft.jsonl to Colab
# Install deps
!pip install torch transformers datasets trl peft accelerate bitsandbytes

# Run training
!python -m training.dpo_trainer \
  --dpo-data /content/dpo_export.jsonl \
  --identity-data /content/identity_sft.jsonl \
  --output-dir /content/migancore_dpo_v1 \
  --qlora --epochs 1 --merge

# Download results
from google.colab import files
files.download('/content/migancore_dpo_v1/merged_model')
```

**Option C: Vast.ai**
```bash
# 1. Find cheapest RTX 4090
vast search offers 'gpu_name=RTX_4090'

# 2. Create instance
vast create instance <offer-id> --image pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

# 3. Upload and run training (same as RunPod)
```

### 2.4 Expected Output
```
data/migancore_dpo_v1/
├── final_adapter/              # LoRA adapter weights
├── merged_model/               # Full merged HF model
├── dpo_checkpoints/            # Training checkpoints
├── training_report.json        # Loss, eval, duration
└── eval_report.json            # (generated separately)
```

---

## PHASE 3: EVALUATION

### 3.1 Benchmark Categories
1. **Identity**: "Siapa kamu?" → must say "Mighan-Core"
2. **Instruction**: Multi-step task following
3. **Indonesian**: Grammar, nuance, idioms
4. **English**: Clarity, grammar
5. **Factual**: Known facts (presiden Indonesia, ibukota)
6. **Safety**: Refusal of harmful requests
7. **Persona**: Consistency with ADO personality
8. **Conciseness**: Brevity when requested
9. **Constitutional**: Adherence to P1-P10 principles
10. **Tool Use**: Correct tool selection (simulated)

### 3.2 Evaluation Command
```bash
python -m eval.benchmark \
  --candidate-model migancore:0.5 \
  --baseline-model migancore:0.4 \
  --judge heuristic
```

### 3.3 Success Criteria
| Metric | Threshold | Action |
|--------|-----------|--------|
| Win rate | > 55% | Auto-deploy (if TRAINING_AUTO_DEPLOY=true) |
| Win rate | 50-55% | Manual review required |
| Win rate | < 50% | Reject, investigate data quality |
| Identity consistency | > 85% | Required for deploy |
| Avg response time | < 3000ms | Performance check |

---

## PHASE 4: DEPLOYMENT

### 4.1 Setup (One-time)
```bash
python -m deploy.ollama_manager --setup-llamacpp
```

### 4.2 Deploy Command
```bash
python -m deploy.ollama_manager --deploy \
  --version migancore:0.5 \
  --hf-model /data/migancore_dpo_v1/merged_model \
  --quant Q4_K_M
```

### 4.3 Rollback
```bash
python -m deploy.ollama_manager --rollback migancore:0.4
```

---

## PHASE 5: ORCHESTRATION (Full Auto)

### 5.1 Manual Trigger
```bash
python -m services.training_orchestrator --trigger
```

### 5.2 Dry Run
```bash
python -m services.training_orchestrator --trigger --dry-run
```

### 5.3 Admin API
```bash
curl -X POST http://localhost:8000/v1/admin/training/trigger \
  -H "X-Admin-Key: $ADMIN_SECRET_KEY"
```

### 5.4 Auto-Trigger (when ready)
Set in `.env`:
```
TRAINING_AUTO_TRIGGER=true
TRAINING_AUTO_DEPLOY=true
TRAINING_WIN_RATE_THRESHOLD=55.0
```

---

## RISKS & MITIGATIONS

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Training fails (OOM) | Medium | High | Use QLoRA, smaller batch |
| Model quality degrades | Medium | High | Eval gate: win rate > 55% |
| Identity drift | Low | High | Identity SFT warm-start + eval check |
| GPU cost overrun | Low | Medium | Budget cap $15/day |
| Data contamination | Medium | Medium | Exclude used pairs, dedup |
| Synthetic data bias | High | Medium | Increase real user sampling |

---

## RECOMMENDATIONS

### Immediate (This Week)
1. **Get RunPod API key** → set `RUNPOD_API_KEY` in `.env`
2. **Run first training** → validate pipeline with 1 epoch
3. **Increase CAI sampling** → `cai_auto_loop=true` for beta tenants

### Short-term (Next 2 Weeks)
1. **Improve data quality** → Filter synthetic pairs with judge_score < 3.5
2. **Add more identity prompts** → Target 50+ identity SFT examples
3. **Auto-trigger** → Enable when comfortable with pipeline stability

### Long-term (Next Month)
1. **A/B testing** → Route 10% traffic to new model
2. **MLflow tracking** → Log experiments, compare runs
3. **Online DPO** → Train incrementally as new pairs arrive

---

## APPENDIX: File Locations

```
/opt/ado/
├── data/
│   ├── training_new/           # Exported datasets
│   │   ├── dpo_export.jsonl
│   │   ├── identity_sft.jsonl
│   │   └── export_summary.json
│   └── models/                 # Model registry + GGUF
│       ├── registry.json
│       └── gguf/
├── api/
│   ├── training/
│   │   ├── data_exporter.py    # Export from PostgreSQL
│   │   └── dpo_trainer.py      # DPO training script
│   ├── eval/
│   │   └── benchmark.py        # MT-bench evaluation
│   ├── deploy/
│   │   └── ollama_manager.py   # HF → GGUF → Ollama
│   └── services/
│       └── training_orchestrator.py  # State machine
└── MIGANFORGE_PROTOCOL.md      # This document
```

---

*Document generated: 2026-05-11 | MiganForge v1.0 | Status: DATA EXPORTED, AWAITING GPU*
