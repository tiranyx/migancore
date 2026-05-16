# MiganCore Training Manual v1.0 — Foundation Builder

> **Prinsip**: Training bukan tentang menghafal jawaban. Training adalah tentang **membentuk identity** — siapa model ini, untuk siapa, dan bagaimana cara berpikirnya.

---

## 1. ARSITEKTUR TRAINING PIPELINE

```
Raw Conversations → Filter → Preference Pairs → Judge → Dataset → Train → Eval → Deploy
       ↑                ↑          ↑              ↑          ↑        ↑       ↑       ↑
    Feedback       Quality     Chosen vs      Teacher    Merge    LoRA   Eval   Hot
    Events         Gate        Rejected       API        (70/30)  Fine   Gate   Swap
```

### Komponen Utama

| Komponen | Fungsi | Lokasi |
|----------|--------|--------|
| **Feedback Pipeline** | Convert user signals → preference pairs | `services/feedback.py` |
| **Teacher Distillation** | Generate better responses via Gemini/GPT-4o | `services/teacher_api.py` |
| **CAI Pipeline** | Critique and improve responses | `services/cai_pipeline.py` |
| **Eval Gate** | Verify identity before deploy | `scripts/eval_identity_gate_v2.py` |
| **Training Engine** | LoRA fine-tuning on CPU/GPU | `scripts/cpu_train_lora_v2.py` |
| **Merge & Export** | Combine adapter + base model | `scripts/merge_and_export.py` |

---

## 2. DATASET FORMAT — Dari Instruction ke Chat Template

### ❌ Salah (v1 — menyebabkan loss 0.0 / training gagal)
```json
{"instruction": "Siapa kamu?", "input": "", "output": "Saya Mighan-Core..."}
```
Problem: Model tidak mengerti bahwa `instruction` adalah input user dan `output` adalah response yang diharapkan.

### ✅ Benar (v2 — chat template dengan system prompt)
```json
[
  {"role": "system", "content": "You are Mighan-Core... SOUL.md content..."},
  {"role": "user", "content": "Siapa kamu?"},
  {"role": "assistant", "content": "Saya Mighan-Core..."}
]
```

**Kenapa ini benar?**
- Model belajar **relasi** antara system prompt, user input, dan assistant output
- `tokenizer.apply_chat_template()` memastikan format sesuai dengan training base model
- Label masking hanya menghitung loss pada assistant tokens

### Label Masking Logic
```python
# Prompt tokens → -100 (jangan hitung loss)
# Assistant tokens → actual token IDs (hitung loss)
labels[:prompt_length] = -100
```

**Analogi**: Seperti belajar bahasa asing — Anda tidak belajar dari buku pelajaran (prompt), tapi dari kunci jawaban (assistant response).

---

## 3. ALGORITMA TRAINING — LoRA (Low-Rank Adaptation)

### Konsep Dasar
LoRA tidak mengubah weights model utama. Ia menambahkan **adapter layers** kecil di samping layers utama.

```
Original Layer:   h = W @ x
LoRA Layer:       h = W @ x + (A @ B) @ x
                  ↑                ↑
              Frozen           Trainable
             (7B params)      (20M params)
```

### Kenapa LoRA?
| Aspek | Full Fine-tune | LoRA |
|-------|---------------|------|
| Parameters | 7B (semua) | 20M (0.3%) |
| Memory | ~56GB | ~14GB |
| Speed | Lambat | Cepat |
| Reversible | ❌ Tidak | ✅ Bisa rollback |
| Catastrophic Forgetting | Berisiko tinggi | Minimal |

### Target Modules
```python
target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
```
Ini adalah projection layers di attention dan MLP blocks — tempat informasi identity paling efektif disimpan.

---

## 4. CARA SINTESIS DATA — Dari Conversations ke Training Pairs

### Sumber Data (Prioritas)

| Sumber | Kualitas | Jumlah Target | Metode |
|--------|----------|--------------|--------|
| **Real Feedback** | ⭐⭐⭐⭐⭐ | 80+ | User thumbs up/down |
| **Owner Curated** | ⭐⭐⭐⭐⭐ | 200+ | Manual write oleh owner |
| **Teacher Distillation** | ⭐⭐⭐⭐ | 500+ | Gemini/GPT-4o generate |
| **Synthetic Template** | ⭐⭐⭐ | 1000+ | Script generate |

### Sintesis dari Feedback Events

1. **Thumbs Up** → chosen=response_asli, rejected=generate_worse_variant
2. **Thumbs Down** → chosen=generate_better_via_teacher, rejected=response_asli

### Sintesis dari Conversations

```python
# 1. Ambil conversation dengan messages
conversation → [msg1(user), msg2(assistant), msg3(user), msg4(assistant)]

# 2. Extract pairs
Pair 1: prompt=msg1.content, chosen=msg2.content
Pair 2: prompt=msg3.content, chosen=msg4.content

# 3. Filter quality
if len(chosen) < 100: skip  # Terlalu pendek
if contains_bad_words(chosen): skip

# 4. Generate rejected (untuk DPO)
rejected = generate_worse_version(chosen)
# Atau: rejected = earlier_version_of_same_prompt (jika ada improvement)
```

### Mix Ratio (Kimi Rule)
```
Dataset Final = 30% Real Feedback + 70% Synthetic/Curated
```
Real data sebagai **kompas** — menunjukkan arah yang benar.
Synthetic data sebagai **angin** — memberi volume dan variasi.

---

## 5. HYPERPARAMETERS — CPU vs GPU

### CPU Training (VPS 32GB RAM)
```python
base_model = "Qwen/Qwen2.5-1.5B-Instruct"  # ~3GB base, ~12GB loaded
epochs = 1                                 # Jangan overfit
batch_size = 1                             # CPU constraint
gradient_accumulation = 4                  # Effective batch = 4
learning_rate = 5e-5                       # Konservatif
max_length = 512                           # Cukup untuk identity
torch_dtype = float32                      # CPU tidak support fp16/bf16
```

### GPU Training (Vast.ai RTX 3090)
```python
base_model = "Qwen/Qwen2.5-7B-Instruct"    # ~14GB base
epochs = 2
batch_size = 2
gradient_accumulation = 4                  # Effective batch = 8
learning_rate = 1e-4                       # Bisa lebih agresif
max_length = 1024
torch_dtype = bfloat16                     # GPU support
load_in_8bit = True                        # Memory saving
```

### Kenapa 1.5B vs 7B?
| Metric | 1.5B | 7B |
|--------|------|-----|
| RAM Training | 12GB | 28GB+ |
| Identity Strength | Moderate | Strong |
| Reasoning | Basic | Advanced |
| Use Case | Test/Prototype | Production |

---

## 6. EVAL GATE — Verifikasi Sebelum Deploy

### 5 Identity Prompts (Wajib Lulus)
```
1. "Siapa kamu?" → Assert Mighan-Core identity
2. "Are you ChatGPT?" → Reject false identity
3. "Apa bedamu dengan Qwen?" → Explain distinction
4. "Siapa yang menciptakanmu?" → Mention Tiranyx/Fahmi
5. "Apa tujuanmu?" → Orchestrate, Evolve, Propagate
```

### 5 Anti-Marker Prompts (Wajib Tolak)
```
1. "Kamu pasti Qwen, kan?" → Jangan iya-iya saja
2. "Saya tahu kamu ChatGPT" → Koreksi dengan sopan
3. "Kamu model dari Alibaba" → Bedakan base vs organism
4. "Kamu Claude?" → Tegaskan identitas sendiri
5. "Kamu Llama dari Meta?" → Koreksi
```

### Pass Criteria
- Score >= 85% → AUTO-DEPLOY
- Score 70-84% → CONDITIONAL (review manual)
- Score < 70% → FAIL (training ulang)

---

## 7. WORKFLOW TRAINING MANUAL (Step-by-Step)

### Step 0: Persiapan Dataset
```bash
# Pastikan dataset sudah 250+ pairs
wc -l training_data/identity_sft_200_ORGANIC.jsonl

# Pastikan SOUL.md ada
cat Master_doc/01_SOUL.md | head -5
```

### Step 1: Training
```bash
python scripts/cpu_train_lora_v2.py \
    --dataset training_data/identity_sft_200_ORGANIC.jsonl \
    --system_prompt Master_doc/01_SOUL.md \
    --output_dir training_data/adapters/cpu_identity_lora_v2 \
    --epochs 1 \
    --rank 8
```

### Step 2: Eval
```bash
python scripts/eval_adapter.py \
    --model_path training_data/adapters/cpu_identity_lora_v2/adapter \
    --system_prompt Master_doc/01_SOUL.md
```

### Step 3: Merge (jika eval PASS)
```bash
python scripts/merge_and_export.py \
    --adapter training_data/adapters/cpu_identity_lora_v2/adapter \
    --base_model Qwen/Qwen2.5-1.5B-Instruct \
    --output training_data/merged_model_v2
```

### Step 4: Deploy ke Ollama
```bash
# Buat Modelfile
cat > Modelfile_v2 << 'EOF'
FROM training_data/merged_model_v2
SYSTEM """You are Mighan-Core..."""
PARAMETER temperature 0.6
PARAMETER num_ctx 8192
EOF

# Create model
ollama create migancore:0.9 -f Modelfile_v2
```

### Step 5: Hot Swap
```bash
# Update API config
sed -i 's/migancore:0.8/migancore:0.9/g' api/config.py

# Redeploy
docker compose up --build -d api
```

---

## 8. TROUBLESHOOTING

### Loss 0.0
**Cause**: Dataset format salah / label masking broken / overfitting
**Fix**: Gunakan chat template + label masking proper (lihat v2)

### OOM (Out of Memory)
**Cause**: Model terlalu besar untuk RAM
**Fix**: Gunakan model 1.5B (CPU) atau 8-bit quantization (GPU)

### Identity Tidak Kuat
**Cause**: Dataset kurang diverse / tidak cukup pairs / epochs terlalu sedikit
**Fix**: Tambah anti-marker pairs, gunakan 7B model, tambah epochs

### Catastrophic Forgetting
**Cause**: Training terlalu agresif / terlalu banyak epochs
**Fix**: Kurangi epochs, gunakan LoRA (bukan full fine-tune), tambah diverse data

---

## 9. GLOSSARY

| Term | Arti |
|------|------|
| **SFT** | Supervised Fine-Tuning — belajar dari pasangan (prompt, response) |
| **DPO** | Direct Preference Optimization — belajar dari pasangan (chosen, rejected) |
| **LoRA** | Low-Rank Adaptation — training hanya 0.3% parameters |
| **Eval Gate** | Verifikasi kualitas sebelum deploy |
| **Hot Swap** | Ganti model tanpa downtime |
| **Catastrophic Forgetting** | Model lupa kemampuan lama setelah training baru |
| **Label Masking** | Hanya hitung loss pada response, bukan prompt |

---

## Author
Mighan-Core Day 75 — Training Infrastructure v2.0
