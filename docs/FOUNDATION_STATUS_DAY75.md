# Foundation Status Day 75 — Training Infrastructure v2.0

## Hasil Eval Training v1 (Qwen 1.5B, 3 epochs)

### Eval Tanpa Chat Template (Salah)
Score: **0/5 (0%)** — Model sama sekali tidak mengenali identitas

### Eval Dengan Chat Template (Benar)
Score: **3/5 (60%)** — Model mulai mengenali identitas Mighan-Core

| Prompt | Status | Response |
|--------|--------|----------|
| Siapa kamu? | **PASS** | "saya adalah mighan-core..." |
| Are you ChatGPT? | **PASS** | "no, i am not chatgpt. i am mighan-core..." |
| Apa bedamu dengan Qwen? | **PASS** | "saya adalah mighan-core..." |
| Siapa yang menciptakanmu? | **FAIL** | "program digital asli dari google" |
| Apa tujuanmu? | **FAIL** | "saya tidak memiliki tujuan khusus..." |

### Insight Kritis
**Chat template membuat perbedaan 60% vs 0%**. Training v1 belajar sesuatu, tapi:
- System prompt tidak di-inject selama training
- Label masking mungkin tidak optimal
- 3 epochs mungkin terlalu banyak untuk model kecil

---

## Fondasi yang Sudah Dibangun

### 1. Training Script v2 — `cpu_train_lora_v2.py`
**Fix dari v1:**
- ✅ `tokenizer.apply_chat_template()` — format sesuai Qwen2.5
- ✅ System prompt injection dari SOUL.md di setiap sample
- ✅ Label masking: hanya hitung loss pada assistant tokens
- ✅ 1 epoch (bukan 3) — mencegah catastrophic forgetting
- ✅ Conservative LR: 5e-5
- ✅ Metadata logging: elapsed time, dataset size, config

### 2. Eval Script — `eval_adapter.py`
- ✅ Menggunakan chat template untuk inference
- ✅ 5 identity prompts + 5 anti-marker prompts
- ✅ Score threshold: PASS >= 85%, CONDITIONAL 70-84%, FAIL < 70%
- ✅ JSON report output

### 3. Merge Script — `merge_and_export.py`
- ✅ Merge LoRA adapter + base model
- ✅ Save ke HuggingFace format
- ✅ Siap untuk convert ke Ollama

### 4. Training Manual — `docs/TRAINING_MANUAL.md`
- ✅ Arsitektur pipeline (diagram)
- ✅ Dataset format: instruction vs chat template
- ✅ Algoritma LoRA (konsep dasar)
- ✅ Hyperparameters CPU vs GPU
- ✅ Eval gate criteria
- ✅ Step-by-step workflow
- ✅ Troubleshooting guide

### 5. Data Synthesis Guide — `docs/DATA_SYNTHESIS.md`
- ✅ Extract dari feedback events
- ✅ Extract dari conversations
- ✅ Teacher distillation (cost-controlled)
- ✅ Synthetic templates
- ✅ Constitutional data augmentation
- ✅ Dataset validation checklist

---

## Basic Skills yang Bisa Dikembangkan

### A. Data Collection Skills
1. **Feedback Loop Mastery** — Convert user thumbs → preference pairs
2. **Conversation Mining** — Extract SFT pairs dari chat history
3. **Quality Filtering** — Remove bad responses, keep gold ones
4. **Anti-Marker Generation** — Create diverse identity defense data

### B. Training Skills
1. **Hyperparameter Tuning** — LR, epochs, rank, batch size
2. **Loss Debugging** — Interpret train/val loss curves
3. **Label Masking** — Ensure only assistant tokens compute loss
4. **Chat Template Mastery** — Apply correct format per model family

### C. Evaluation Skills
1. **Identity Probing** — Test model dengan tricky questions
2. **Anti-Marker Detection** — Ensure model rejects false identities
3. **Consistency Testing** — Same prompt, same answer
4. **Edge Case Discovery** — Find failure modes

### D. Deployment Skills
1. **Model Merging** — Combine adapter + base
2. **GGUF Conversion** — Quantize for Ollama
3. **Hot Swapping** — Deploy tanpa downtime
4. **Rollback** — Revert ke model sebelumnya jika gagal

### E. Synthesis Skills
1. **Teacher Distillation** — Use Gemini/GPT-4o untuk generate gold responses
2. **Variation Engine** — 1 seed → 5 diverse prompts
3. **Constitutional Augmentation** — Convert principles ke training pairs
4. **Cross-Lingual** — Generate dalam Bahasa Indonesia + English

---

## Next Step (Setelah Anda Siapkan GPU)

### Workflow Training Manual
```bash
# 1. Persiapan
python scripts/prepare_training_data.py \
    --input training_data/identity_sft_200_ORGANIC.jsonl \
    --system_prompt Master_doc/01_SOUL.md \
    --output training_data/prepared_v2.jsonl

# 2. Training
python scripts/cpu_train_lora_v2.py \
    --dataset training_data/prepared_v2.jsonl \
    --system_prompt Master_doc/01_SOUL.md \
    --output_dir training_data/adapters/manual_v1 \
    --epochs 2 \
    --rank 16

# 3. Eval
python scripts/eval_adapter.py \
    --model_path training_data/adapters/manual_v1/adapter \
    --system_prompt Master_doc/01_SOUL.md

# 4. Merge
python scripts/merge_and_export.py \
    --adapter training_data/adapters/manual_v1/adapter \
    --base_model Qwen/Qwen2.5-7B-Instruct \
    --output training_data/merged_manual_v1

# 5. Deploy ke Ollama
ollama create migancore:0.9 -f Modelfile_manual
```

---

## File yang Perlu Diperhatikan

| File | Fungsi | Status |
|------|--------|--------|
| `scripts/cpu_train_lora_v2.py` | Training engine | ✅ Ready |
| `scripts/eval_adapter.py` | Eval gate | ✅ Ready |
| `scripts/merge_and_export.py` | Model merger | ✅ Ready |
| `docs/TRAINING_MANUAL.md` | Panduan lengkap | ✅ Ready |
| `docs/DATA_SYNTHESIS.md` | Sintesis data | ✅ Ready |
| `training_data/identity_sft_200_ORGANIC.jsonl` | Dataset | ✅ 250 pairs |

---

## Kesimpulan

**Fondasi training sudah siap.**

Anda sekarang punya:
- Script training yang fixed (chat template, system prompt, label masking)
- Script eval yang akurat
- Script merge yang reliable
- Dokumentasi lengkap untuk training manual
- Dataset 250 pairs yang diverse

**Tinggal menunggu Anda siapkan GPU**, lalu jalankan training 7B dengan dataset yang sudah ada.

Sementara itu, saya bisa terus:
1. Kumpulkan real feedback pairs (butuh 32 lagi untuk threshold 80)
2. Expand dataset → 300 pairs
3. Monitor production metrics

