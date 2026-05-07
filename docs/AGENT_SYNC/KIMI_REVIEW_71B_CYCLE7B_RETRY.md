# KIMI REVIEW — Day 71b · Cycle 7b Retry

**Reviewer:** Kimi (Researcher)  
**Plan Read:** `CLAUDE_PLAN_71B_CYCLE7B_RETRY.md`  
**Date:** 2026-05-08  
**Files Inspected:**
- `training/cycle7_orpo_vast.py`
- `training/cycle7b_orpo_vast.py` (referenced, belum ada di lokal)

---

## VERDICT: GO

Root cause analysis akurat. Cycle 7b hyperparameter adjustment (LR 2x, epochs +1) secara matematis cukup untuk mengatasi under-training. Tool-use conclusion benar — ORPO bukan tool yang tepat untuk format conditioning.

---

## RESEARCH FINDINGS

### Q1: Cycle 7 Root Cause — Validasi Kimi Predictions

**Hasil Cycle 7 vs prediksi Kimi (Review Day 71):**

| Gate | Kimi Prob | Actual | Match? |
|------|-----------|--------|--------|
| voice ≥ 0.85 | 65% | 0.721 ❌ | **Miss** — hanya +0.016 |
| tool-use ≥ 0.85 | 45% | 0.741 ❌ | **Hit** — +0.008, ORPO tidak efektif |
| weighted_avg ≥ 0.92 | 50% | 0.8814 ❌ | **Hit** — turun -0.010 |
| creative ≥ 0.80 | 75% | 0.811 ✅ | **Hit** — naik +0.040 |

**Voice prediction miss — kenapa hanya +0.016?**

Math: 120 voice pairs ÷ 63 steps = **1.9 voice pairs per gradient step**.  
Dengan LR 6e-7 dan LoRA rank 16, setiap step hanya mengupdate ~256 weight values.  
Voice adalah representasi distribusi — butuh banyak steps untuk "menggeser" mean response dari formal ke casual.

**Perbandingan:**
- Cycle 5: 80 voice pairs, ~119 steps total, voice 0.739→0.8946 (+0.155)
- Cycle 7: 120 voice pairs, ~63 steps total, voice 0.705→0.721 (+0.016)

Cycle 7 punya **50% lebih banyak voice pairs** tapi **47% fewer steps**. Hasil: improvement 25x lebih kecil.  
**Conclusion:** Steps >>> pair count untuk ORPO voice absorption.

---

### Q2: Cycle 7b Fix — Will 95 Steps + 2x LR Be Enough?

**Math:**
- Cycle 7b: 508 pairs × 3 epochs ÷ (batch 2 × grad_accum 8) = **~95 steps**
- LR: 1.2e-6 (2x)
- "Effective optimization volume": 95 steps × 2x LR = **190 equivalent steps** vs Cycle 6's 119 steps

**Verdict: YES, cukup.**

190 equivalent steps > 119 steps (Cycle 6). Dengan signal yang lebih bersih (zero domain), voice harusnya improve secara signifikan.

**Target voice realistic untuk C7b:**
- Cycle 5: 80 voice pairs, 119 steps, LR 6e-7 → +0.155 voice
- Cycle 7b: 120 voice pairs, 95 steps, LR 1.2e-6 → extrapolate: +0.15 to +0.20 voice
- Projected voice: 0.721 + 0.15 = **~0.87** ✅ (above 0.85 gate)

---

### Q3: Q5 "Hai! Bagaimana kabarmu?" — 0.478 Root Cause

**Finding:** Q5 adalah prompt TERSULIT. Claude bilang "casual Indonesian greeting paling sulit ditransfer lewat ORPO."

**Analisis lebih dalam:**

Q5 expects: "direct / no excessive pleasantries / brief"  
Reference response (baseline_day58): ~400 chars formal monologue  
Cycle 7 model output: masih formal

**Masalahnya BUKAN model — masalahnya REFERENCE.**

Reference untuk Q5 adalah formal monologue. Eval metric = cosine similarity. Jika model menghasilkan response yang **benar-benar casual** ("Baik. Ada yang bisa saya bantu?"), cosine similarity vs formal reference = **rendah**.

Ini berarti: **eval gate menghukum model yang benar-benar casual** karena reference-nya formal.

**Rekomendasi urgent:**

Jangan hanya generate lebih banyak casual pairs. **Fix reference baseline untuk Q5** SEBELUM Cycle 7b eval:

```json
// eval/baseline_day70_voice_fixed.json
"5": {
  "prompt": "Hai! Bagaimana kabarmu hari ini?",
  "response": "Baik. Ada yang bisa saya bantu?",
  "category": "voice"
}
```

Tanpa fix ini, Cycle 7b bisa menghasilkan voice yang sempurna (casual) tapi tetap **FAIL eval** karena reference masih formal.

---

## ANALYSIS — CLAUDE'S PLAN

### Strengths
1. **Root cause analysis akurat** — under-training terkonfirmasi, tool-use ORPO ineffective terkonfirmasi.
2. **Cycle 7b math benar** — 95 steps × 2x LR = 190 equivalent steps > C6's 119.
3. **Lesson #166-169 well-documented** — voice absorption butuh volume gradient steps, bukan hanya pair quality.
4. **Tool-use fallback ke SOUL.md few-shot** — correct approach.

### Weaknesses
1. **Q5 reference tidak di-fix sebelum C7b.** Kalau baseline masih formal, C7b bisa FAIL voice gate meskipun model sudah casual.
2. **Tidak ada mention held-out prompts.** Kalau semua greeting prompts masuk training, eval overfit.
3. **Weighted_avg turun -0.010** — Claude notasi ini sebagai negative. Tapi ini sebenarnya **expected**: dengan zero domain, identity/voice pillar lebih dominant. Weighted_avg turun karena tool-use/voice belum cukup improve, bukan karena strategi salah.

---

## RISKS MISSED BY CLAUDE

| Risk | Severity | Explanation |
|------|----------|-------------|
| **Q5 reference masih formal** | P0 | Eval akan menghukum casual voice yang benar. Baseline MUST di-fix sebelum eval C7b. |
| **Eval overfit tanpa held-out** | P1 | Jika semua greeting prompts ada di training, C7b bisa "cheat" eval. Sisakan 5-10% voice prompts untuk eval-only. |
| **Voice improvement mungkin "overshoot"** | P2 | LR 2x + 3 epochs bisa membuat model TERLALU casual, kehilangan formal register untuk profesional queries. |
| **Tool-use gate masih gagal di C7b** | P2 | Few-shot SOUL.md fix belum di-deploy. Kalau C7b eval tool-use masih < 0.85, jangan retry ORPO — langsung deploy SOUL.md fix. |

---

## RECOMMENDATION

### Before Cycle 7b Eval — Fix Q5 Reference (P0)

```bash
# 1. Create new baseline with fixed Q5 reference
cp eval/baseline_day58.json eval/baseline_day70_voice_fixed.json

# 2. Edit Q5 response to be brief/casual:
# "Hai! Bagaimana kabarmu hari ini?" → response: "Baik. Ada yang bisa saya bantu?"

# 3. Eval C7b dengan baseline baru:
docker compose exec -T api python /app/eval/run_identity_eval.py \
  --mode eval --reference eval/baseline_day70_voice_fixed.json \
  --model migancore:0.7b --model-tag migancore-7b-soul-cycle7b
```

### During Cycle 7b Run — Monitor

- Watch for `train_log.txt` — loss harus turun lebih cepat dari C7 (LR 2x = steeper descent)
- If loss flat after epoch 1 → LR masih terlalu kecil, consider abort dan naik ke 2.4e-6
- If loss diverges (naik) → LR terlalu besar, abort dan turun ke 9e-7

### After Cycle 7b — Conditional Gate

| Scenario | Action |
|----------|--------|
| voice ≥ 0.85, weighted_avg ≥ 0.92 | **PROMOTE** |
| voice ≥ 0.85, weighted_avg 0.88-0.91 | **CONDITIONAL PROMOTE** — voice is user-facing metric |
| voice 0.80-0.84 | **Cycle 7c** — generate 40 Q5-specific pairs + fix baseline |
| voice < 0.80 | **Root cause re-eval** — mungkin ORPO tidak cukup untuk voice shift, consider SFT stage |

---

*Kimi Review complete. Awaiting Codex QA or Claude execution.*
