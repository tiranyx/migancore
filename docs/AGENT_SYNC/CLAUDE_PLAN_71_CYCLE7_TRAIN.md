# CLAUDE PLAN — Day 71 | Cycle 7 Training GO
> Ditulis oleh: Claude Sonnet 4.6
> Tanggal: 2026-05-08
> Status: Day 70 COMPLETE → Day 71 PLAN

---

## ✅ Day 70 Delivered (ringkasan untuk Kimi + Codex)

| Item | Status |
|---|---|
| Pre-deploy checklist | ✅ 5-layer aligned HEAD `7625037` |
| BUILD_DAY "Day 70" | ✅ live di /health |
| Cycle 7 dataset | ✅ 508 pairs, 317KB, exported |
| Letta audit | ✅ service OK, knowledge empty = content bukan code |
| Codex C7 STT security fix | ✅ JWT auth backend + frontend |
| `cycle7_orpo_vast.py` | ✅ trainer siap, pre-flight ALL GREEN |
| Vast.ai balance | ✅ $8.58 cukup ~3 run |

---

## 🎯 Day 71 Objective: Cycle 7 Training + Eval

### Primary Track (P0): GO Cycle 7

**Pre-flight sudah verified ALL GREEN:**
- Dataset: 508 pairs di `/opt/ado/data/workspace/cycle7_dataset.jsonl`
- Train script: `/opt/ado/training/train_simpo_standard.py` ✅
- Secrets: vastai_api_key + hf_token ✅
- Vast.ai balance: $8.58 ✅

**Command GO (run on VPS):**
```bash
nohup python3 /opt/ado/training/cycle7_orpo_vast.py > /tmp/cycle7_training.log 2>&1 &
tail -f /tmp/cycle7_training.log
```

**Estimasi:** 15-25 min training (508 pairs × 2 epochs, A40/A100)
**Cost projection:** ~$0.10-0.20

**Gate PROMOTE (harus ALL pass):**
```
weighted_avg >= 0.92  (C6 ROLLBACK: 0.891)
voice        >= 0.85  (C6 ROLLBACK: 0.705 ← HARDEST, butuh +0.145)
tool-use     >= 0.85  (C6 ROLLBACK: 0.733 ← butuh +0.117)
identity     >= 0.90  (C6: 0.9334 — maintain)
evo-aware    >= 0.80  (C6: 0.8856 — maintain, tidak ditraining C7)
creative     >= 0.80  (C6: 0.771  — butuh +0.029)
```

**Setelah training selesai:**
```bash
# 1. Convert GGUF
python3 /opt/llama.cpp/convert_lora_to_gguf.py /opt/ado/cycle7_output/cycle7_adapter/ \
  --outfile /opt/ado/cycle7_output/cycle7_lora.gguf --outtype f16

# 2. Copy ke Ollama
cp /opt/ado/cycle7_output/cycle7_lora.gguf /opt/ado/data/ollama/cycle7_lora.gguf

# 3. Register Modelfile
ollama create migancore:0.7 -f /opt/ado/training/Modelfile_cycle7

# 4. Run eval
docker compose exec -T api python /app/eval/run_identity_eval.py \
  --mode eval --model-tag migancore-7b-soul-cycle7 --retry 3

# 5. PROMOTE if all gates pass
ollama cp migancore:0.7 migancore:latest
```

---

## 🔮 Multi-Teacher Vision (Cycle 8 Blueprint)

Pertanyaan Fahmi hari ini tentang teacher diversity → dicatat untuk Cycle 8.

Kita punya 4 teacher API aktif (key semua tersedia):
- **Kimi K2** — voice Indonesia, long context, proven di CAI Day 37
- **Gemini 2.5-flash** — fast, murah, proven Cycle 3-7
- **GPT-4o-mini** — instruksi following, format tool_use precise
- **Claude Haiku** — natural voice, format bersih

**Cycle 8 plan: Multi-teacher quorum**
```
Prompt → [Kimi + Gemini + GPT-mini] → vote 2/3 → chosen=best, rejected=worst
```
Bias satu teacher cancel oleh dua lainnya. Kualitas pair lebih tinggi.

---

## 📋 P1 Backlog (setelah Cycle 7 PROMOTE)

- [ ] Hafidz Ledger Phase A — hafidz_contributions table + POST endpoint
- [ ] Feedback smoke test — Fahmi klik thumbs di app.migancore.com
- [ ] Letta onboarding flow — populate knowledge blocks
- [ ] Codex C5: OpenAPI schema (admin/license routes visible)
- [ ] Codex C6: Admin key di localStorage (XSS risk)
- [ ] Multi-teacher generator — Cycle 8 blueprint implement

---

## 📝 Lessons Day 70

| # | Lesson |
|---|---|
| #158 | `gemini-2.0-flash` deprecated → always use `gemini-2.5-flash` |
| #159 | Real DB schema audit wajib sebelum tulis SQL: preference_pairs has no `category` |
| #160 | `identity_anchor_v2` subcategory suffix → wajib LIKE prefix, bukan exact IN() |
| #161 | Container rebuild (`--build`) kills semua exec processes → monitor via nohup |

---

>> **Kimi:** Review Cycle 7 gate targets + multi-teacher quorum strategy. Tulis `KIMI_REVIEW_71_CYCLE7_TRAIN.md`
>> **Codex:** QA trainer script `cycle7_orpo_vast.py` — cek semua lessons applied, tulis `CODEX_QA_71_CYCLE7_TRAIN.md`
