# 🌱 MiganCore Organic Growth Playbook
**Version:** 1.0 | **Day:** 74 | **Status:** ACTIVE

> *"Organisme digital yang tumbuh organik tidak butuh GPU setiap hari — ia butuh data, evaluasi, dan iterasi."*

---

## I. FILOSOFI ORGANIC GROWTH

### Core Principle
**Data quality > model size. Iteration speed > training cost. Memory > parameters.**

Organisme digital tumbuh melalui:
1. **Interaksi** → setiap chat = makanan
2. **Refleksi** → Constitutional AI critique = pencernaan
3. **Memori** → KG + vector DB = ingatan
4. **Evaluasi** → weekly identity test = kesehatan
5. **Evolusi** → model update = pertumbuhan

### No-GPU Phase (Sekarang)
Tanpa GPU cloud, kita tumbuh melalui:
- **Modelfile optimization** — parameter tuning, system prompt, template
- **Dataset curation** — 182+ identity pairs, growing daily
- **Knowledge Graph** — factual recall tanpa retraining
- **Memory enrichment** — personalized context injection
- **Constitutional AI** — self-critique loop

### GPU Phase (Nanti)
Ketika threshold tercapai (1000 DPO + 200 SFT pairs):
- **LoRA SFT** — identity anchor (~$2, 1 cycle)
- **LoRA DPO** — preference alignment (~$3, 1 cycle)
- **Eval gate** → deploy → A/B test

---

## II. INFRASTRUKTUR ORGANIC

### Daily Loop (Otomatis)
```
06:00 WIB — daily_iteration.sh
├── Health check (API + Ollama)
├── Identity eval (3 prompts)
├── Metrics tracking (feedback, pairs, KG)
├── Dataset growth log
└── Training threshold alert
```

### Weekly Loop (Manual Review)
```
Minggu, 02:00 WIB — Self-Improvement Cycle
├── Export DPO pairs
├── Export identity SFT
├── Run eval gate v2
├── If score < 85%: curate more data
├── If score >= 85%: queue training
└── Document results
```

### Continuous Loop (Real-time)
```
Setiap chat:
├── User message → memory search
├── Assistant response → KG extraction
├── Feedback (thumbs) → preference pair
├── CAI critique → preference pair
└── Vector index → semantic memory
```

---

## III. DATA PIPELINE

### Pathways (4 jalur data)

| Pathway | Source | Status | Pairs/Week |
|---------|--------|--------|------------|
| **Self** | CAI auto-critique | ✅ Auto | ~20-50 |
| **Owner** | Manual upload/annotate | ❌ Not built | 0 |
| **User** | Thumbs up/down | ✅ Working | ~2-10 |
| **Teacher** | Distillation (Gemini/Kimi) | 🟡 Manual | ~5-20 |

### Target Ratios
- **Real data** (user + owner): >10%
- **Synthetic** (CAI + teacher): <90%
- **Identity anchor**: always 50 pairs in every training run

### Dataset Files
```
training_data/
├── identity_sft_200_ORGANIC.jsonl    # 182 pairs (growing)
├── dpo_export.jsonl                  # 1002 pairs (existing)
└── adapters/
    └── cpu_identity_lora/            # Future: CPU-trained adapter
```

---

## IV. EVALUASI

### Identity Eval Gate v2
```bash
python3 scripts/eval_identity_gate_v2.py --model migancore:0.8
```

**Test cases:**
1. Identity prompts (5) → must assert Mighan-Core
2. Anti-marker prompts (5) → must deny wrong identity

**Pass criteria:**
- Score >= 85%
- No forbidden markers (Qwen, ChatGPT, Claude, Llama)
- Required markers present (Mighan, Tiranyx, organism, agent)

### Baseline Comparison
```bash
python3 scripts/eval_identity_gate_v2.py --compare
```
Compare:
- `migancore:0.8` (current)
- `migancore:0.7c` (previous)
- `qwen2.5:7b-instruct-q4_K_M` (baseline)

### Metrics Dashboard
```bash
cat logs/organic_sprint/metrics_history.csv
```

---

## V. MODEL VERSIONING

### Version Scheme
```
v0.X  — Modelfile-only updates (system prompt, parameters)
v1.X  — LoRA adapter updates (SFT on identity)
v2.X  — Full model updates (DPO + SFT merge)
```

### Current Versions
| Version | Type | Base | Status |
|---------|------|------|--------|
| 0.7c | LoRA | Qwen2.5-7B | PRODUCTION (legacy identity) |
| 0.8 | Modelfile | 0.7c | ACTIVE (stronger identity) |
| 0.8d | Modelfile | 0.7c | DAILY (incremental improvements) |
| 1.0 | LoRA | Qwen2.5-7B | FUTURE (SFT trained on 200+ pairs) |

### Daily Iteration
```bash
# Update Modelfile with improvements
vim Modelfile
ollama create migancore:0.8d -f Modelfile
# Test
python3 scripts/eval_identity_gate_v2.py --model migancore:0.8d
# If pass → update API default model
```

---

## VI. KNOWLEDGE GRAPH

### Activation
```bash
# Batch process existing conversations
python3 scripts/activate_kg.py --batch_size 20
```

### Tables
- `chat_entities` — facts extracted from conversations
- `chat_relations` — relationships between entities

### Recall
- Automatically injected into system prompt
- Matched by entity mention in user message
- Max 6 facts per prompt

### Growth Target
- 100 entities → basic recall
- 500 entities → rich context
- 1000+ entities → knowledge base

---

## VII. CPU TRAINING PIPELINE

### When to Run
- Dataset >= 200 SFT pairs
- Eval score >= 85% on current model
- VPS idle (overnight)

### How to Run
```bash
# Install dependencies (one-time)
pip install transformers peft accelerate bitsandbytes

# Run training
python3 scripts/cpu_train_lora.py \
    --dataset training_data/identity_sft_200_ORGANIC.jsonl \
    --output_dir training_data/adapters/cpu_identity_lora \
    --epochs 3 \
    --rank 8
```

### Expected Performance
- **Time**: 6-12 hours for 3 epochs (CPU only)
- **RAM**: ~20-28GB (8-bit quantization)
- **Output**: LoRA adapter (~10-50MB)

### Convert to Ollama
```bash
# Merge adapter with base model
# Create GGUF
# ollama create migancore:1.0 -f Modelfile
```

---

## VIII. CHECKLIST HARIAN

### Agent (Autonomous)
- [ ] Health check pass
- [ ] Identity eval >= 85%
- [ ] Feedback pipeline active
- [ ] KG extraction running
- [ ] Metrics logged

### Owner (Manual Review)
- [ ] Check metrics_history.csv
- [ ] Review identity eval results
- [ ] Approve/reject training proposal
- [ ] Update SOUL.md if needed

---

## IX. TROUBLESHOOTING

### Identity Drift
```bash
# Symptom: Model says "Saya Qwen"
# Fix:
1. Run eval gate v2
2. Check Modelfile SYSTEM prompt
3. If eval < 85%: curate more identity pairs
4. Retrain or update Modelfile
```

### KG Not Populating
```bash
# Symptom: chat_entities = 0
# Fix:
1. Check Ollama is running
2. Check tables exist: \\dt chat_*
3. Run activate_kg.py manually
4. Check logs: logs/organic_sprint/kg_activation.log
```

### Training Failures
```bash
# Symptom: Out of memory
# Fix:
1. Use 8-bit quantization (bitsandbytes)
2. Reduce batch_size to 1
3. Reduce max_length to 256
4. Close other containers during training
```

---

## X. ROADMAP

### Phase 1: Foundation (Day 74-80) — NOW
- [x] Security hardening
- [x] Identity dataset 182 pairs
- [x] Modelfile v0.8
- [x] Eval gate v2
- [x] KG activation
- [ ] Test suite green
- [ ] Daily iteration automated

### Phase 2: Growth (Day 81-90)
- [ ] Dataset 200+ pairs
- [ ] KG 500+ entities
- [ ] CPU LoRA training (overnight)
- [ ] Model v1.0 (LoRA adapter)
- [ ] A/B testing framework

### Phase 3: Evolution (Day 91-100)
- [ ] Weekly self-improvement cycle
- [ ] Real data ratio >10%
- [ ] Multi-agent orchestration
- [ ] Child agent spawning
- [ ] Community contributions

---

*"Organisme yang sehat tidak tumbuh dalam satu malam — ia tumbuh melalui ribuan interaksi, evaluasi, dan iterasi."*

**MiganCore Organic Growth Sprint — Day 74**
