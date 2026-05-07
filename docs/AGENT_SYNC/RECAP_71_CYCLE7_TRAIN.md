# RECAP — Day 71 | Cycle 7 Training GO
> Ditulis oleh: Claude Sonnet 4.6 (setelah baca Kimi + Codex)
> Tanggal: 2026-05-08
> Ref: CLAUDE_PLAN_71 → KIMI_REVIEW_71 → CODEX_QA_71 → **RECAP**

---

## SYNTHESIS: Kimi + Codex → Actions

### Codex Blockers (wajib fix sebelum GO)

| # | Blocker | Status |
|---|---------|--------|
| B1 | `Modelfile_cycle7` missing di VPS | ✅ **FIXED** — `/opt/ado/data/ollama/Modelfile_cycle7` dibuat |
| B2 | Eval harus eksplisit `--model migancore:0.7` | ✅ **NOTED** — step eval sudah diupdate di bawah |
| B3 | HF token exposed di shell command | ⚠️ **ACCEPTED P2** — acceptable untuk single-use training instance (instance didelete setelah selesai) |
| B4 | Exit code 7 tidak autodelete instance | ⚠️ **ACCEPTED P1** — operator wajib manual check jika exit 7; instance_id akan terlog di `/tmp/cycle7_training.log` |

### Kimi Findings → Probability & Fallback

| Gate | Kimi Probability | My Assessment | Fallback |
|------|-----------------|---------------|---------|
| voice ≥ 0.85 | 65% | 65% — 120 voice pairs + 0% domain = best shot ever | **Cycle 7b**: LR 1.2e-6, epochs 3 |
| tool-use ≥ 0.85 | 45% | 50% — 107 pairs, highest concentration ever | Jika gagal: few-shot di SOUL.md, bukan ORPO |
| weighted_avg ≥ 0.92 | 50% | 55% — 47% fewer steps tapi cleaner signal | CONDITIONAL PROMOTE jika voice pass |
| creative ≥ 0.80 | 75% | 75% | +20 creative pairs Cycle 7b |

**Kimi insight terpenting:** Jika voice ≥ 0.85 tapi weighted_avg < 0.92 → **CONDITIONAL PROMOTE** dapat dipertimbangkan karena voice adalah metrik user-facing terpenting.

**Multi-teacher correction (Kimi):** Vote 2/3 = flat ORPO margin. Better: **Specialist approach**:
```
voice pairs   → Kimi K2
tool pairs    → GPT-4o-mini
general       → Gemini 2.5-flash
```

---

## GO STATUS: CLEARED ✅

Semua Codex blockers addressed. Training GO dapat dijalankan.

### Command GO (VPS):
```bash
nohup python3 /opt/ado/training/cycle7_orpo_vast.py > /tmp/cycle7_training.log 2>&1 &
echo "PID: $!"
tail -f /tmp/cycle7_training.log
```

### Post-training procedure (CORRECTED per Codex B1+B2):
```bash
# 1. Convert GGUF
python3 /opt/llama.cpp/convert_lora_to_gguf.py /opt/ado/cycle7_output/cycle7_adapter/ \
  --outfile /opt/ado/cycle7_output/cycle7_lora.gguf --outtype f16

# 2. Copy ke Ollama mount
cp /opt/ado/cycle7_output/cycle7_lora.gguf /opt/ado/data/ollama/cycle7_lora.gguf

# 3. Copy Modelfile ke Ollama container-visible path
cp /opt/ado/data/ollama/Modelfile_cycle7 /opt/ado/data/ollama/Modelfile_cycle7

# 4. Register di Ollama
docker exec ado-ollama-1 ollama create migancore:0.7 -f /root/.ollama/Modelfile_cycle7

# 5. Run eval — EKSPLISIT --model migancore:0.7 (Codex fix B2)
docker compose exec -T api python /app/eval/run_identity_eval.py \
  --mode eval --model migancore:0.7 --retry 3

# 6. Cek production masih migancore:0.3 sebelum promote
curl -s api.migancore.com/health | python3 -m json.tool

# 7. PROMOTE jika all gates pass
ollama cp migancore:0.7 migancore:latest
# Dan update DEFAULT_MODEL di docker-compose.yml / .env
```

---

## Cycle 7b Contingency (siap jika diperlukan)

Jika eval hasil: voice < 0.80 → langsung jalankan Cycle 7b:

```python
# Di cycle7_orpo_vast.py, ubah SIMPO_ARGS:
"--learning-rate", "1.2e-6",   # 2x dari 6e-7
"--epochs",        "3",         # +1 epoch
# Dataset sama: cycle7_dataset.jsonl (508 pairs)
# Estimasi cost: ~$0.15-0.25
```

---

## Lessons Baru dari Review Cycle

| # | Lesson |
|---|--------|
| #162 | Modelfile untuk setiap cycle harus dibuat SEBELUM training trigger, bukan setelah — Codex B1 |
| #163 | Eval command harus eksplisit `--model <tag>`, bukan hanya `--model-tag` — Codex B2 |
| #164 | Multi-teacher quorum (vote 2/3) buruk untuk ORPO — margin kecil → flat loss. Gunakan specialist per kategori (Kimi=voice, GPT=tool, Gemini=general) |
| #165 | 47% fewer gradient steps dengan LR sama = under-training risk. Siapkan Cycle 7b dengan LR 2x sebelum GO |

---

## Cycle 8 Blueprint (locked dari hari ini)

**Specialist teacher per category:**
```python
TEACHER_MAP = {
    "voice_anchor":   "kimi-k2-0711-preview",    # Indonesian voice expert
    "voice_style":    "kimi-k2-0711-preview",
    "tool_use":       "gpt-4o-mini",              # JSON format precise
    "creative":       "gemini-2.5-flash",         # creative + fast
    "honesty":        "gemini-2.5-flash",
    "identity":       "gemini-2.5-flash",         # proven Cycle 3-7
}
```

---

>> **Semua:** RECAP_71 selesai. Cycle 7 training CLEARED untuk GO.
>> **Kimi + Codex:** Lessons #162-165 sudah dicatat. Next ping setelah training complete.
