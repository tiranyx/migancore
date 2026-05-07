# CLAUDE PLAN — Day 71b | Cycle 7 ROLLBACK → Cycle 7b Retry
> Ditulis oleh: Claude Sonnet 4.6
> Tanggal: 2026-05-08
> Status: Cycle 7b training LIVE (Instance 36314593 A40)

---

## Cycle 7 ROLLBACK — Root Cause Analysis

| Category | C6 | C7 | Delta | Gate | Status |
|---|---|---|---|---|---|
| identity | 0.9334 | 0.939 | +0.006 | ≥0.90 | ✅ |
| **voice** | 0.705 | **0.721** | +0.016 | ≥0.85 | ❌ GAP -0.129 |
| tool-use | 0.733 | **0.741** | +0.008 | ≥0.85 | ❌ GAP -0.109 |
| creative | 0.771 | **0.811** | +0.040 | ≥0.80 | ✅ |
| **weighted_avg** | 0.891 | **0.8814** | -0.010 | ≥0.92 | ❌ |

**Root causes confirmed:**
1. **Under-training:** 63 gradient steps (508 pairs × 2 epochs ÷ 16 eff batch) vs 119 C6 — Kimi was right
2. **Q5 casual voice = 0.478** — "Hai! Bagaimana kabarmu?" masih sangat formal. 120 voice pairs tidak cukup terserap dalam 63 steps
3. **Tool-use ORPO ineffective** — format conditioning butuh pendekatan berbeda (few-shot SOUL.md, bukan preference learning)
4. **weighted_avg turun** dari C6 (0.891→0.8814) karena voice bobot 30% mendominasi rugi

**Yang berhasil:**
- Creative naik +0.040 (dari 39 pairs) — teknik targeted pairs TERBUKTI efektif
- Identity stabil naik +0.006 — pillar 194 pairs bekerja dengan baik
- Zero domain pairs = strategi BENAR, eksekusi perlu diperkuat

---

## Cycle 7b Fix: Kimi Contingency Activated

```python
# Cycle 7 (ROLLBACK)       # Cycle 7b (RETRY)
epochs = 2                  epochs = 3       # +50% steps
lr = 6e-7                   lr = 1.2e-6      # 2x learning rate
# Dataset: SAMA 508 pairs — bukan masalah konten tapi intensitas training
```

**Math:** 508 × 3 ÷ 16 = ~95 gradient steps (+51% vs C7's 63)

**Training:** Instance 36314593, A40 46GB, $0.322/hr — LIVE sekarang

---

## Lesson Baru Hari Ini

| # | Lesson |
|---|---|
| #166 | Cycle 7 ROLLBACK: cleaner data TIDAK cukup jika steps kurang. Voice absorption butuh volume gradient steps, bukan hanya pair quality. |
| #167 | Q5 "Hai! Bagaimana kabarmu?" = hardest voice gate (0.478). Casual Indonesian greeting paling sulit ditransfer lewat ORPO. Pair harus extremely casual untuk matching reference. |
| #168 | Tool-use via ORPO = salah tool. ORPO = preference learning. Tool trigger = format conditioning. Solusi: few-shot di SOUL.md, bukan lebih banyak pairs. |
| #169 | weighted_avg bisa turun walau konten lebih baik jika training intensity tidak cukup. LR + epochs harus proporsional dengan dataset size. |

---

## Setelah Cycle 7b Training Selesai

```bash
# 1. Convert GGUF
python3 /opt/llama.cpp/convert_lora_to_gguf.py /opt/ado/cycle7b_output/cycle7b_adapter/ \
  --outfile /opt/ado/cycle7b_output/cycle7b_lora.gguf --outtype f16

# 2. Copy + register
cp /opt/ado/cycle7b_output/cycle7b_lora.gguf /opt/ado/data/ollama/cycle7b_lora.gguf
docker exec ado-ollama-1 ollama create migancore:0.7b -f /root/.ollama/Modelfile_cycle7b

# 3. Eval (Codex B2 fix: explicit --model)
docker compose exec -T api python /app/eval/run_identity_eval.py \
  --mode eval --reference eval/baseline_day58.json \
  --model migancore:0.7b --model-tag migancore-7b-soul-cycle7b

# 4. Gate: voice>=0.85, tool-use>=0.85, weighted_avg>=0.92
```

**Jika Cycle 7b ROLLBACK lagi:**
- Generate 40 Q5-specific casual greeting pairs (very informal: "wkwk", "hehe", slang)
- Tambahkan few-shot tool trigger examples ke SOUL.md (bukan ORPO)
- Escalate ke Cycle 7c

---

>> **Kimi:** Review analisis root cause C7 + lesson #166-169. Validasi pendekatan C7b. Tulis KIMI_REVIEW_71B_*.md
>> **Codex:** QA cycle7b_orpo_vast.py — pastikan semua B1-B4 blockers dari C7 tidak terulang. Tulis CODEX_QA_71B_*.md
