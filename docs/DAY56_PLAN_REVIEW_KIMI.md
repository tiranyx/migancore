# Day 56 Plan — Strategic Review oleh Kimi
**Date:** 2026-05-06 | **Reviewer:** Kimi Code CLI (docs/strategy scope)
**Plan under review:** `docs/DAY56_PLAN.md` oleh Claude
**Rule:** Review-only. Tidak edit file milik Claude. Findings = rekomendasi untuk Claude/user execute.

---

## Executive Summary

DAY56_PLAN.md adalah **plan yang solid** — H/R/B framework diterapkan, vision compliance 5/5 pass, lessons #57-#88 di-apply dengan benar. Namun ada **3 critical gaps** dan **4 medium gaps** yang perlu diperbaiki sebelum eksekusi dimulai. Tanpa perbaikan ini, Day 56 berisiko:
- Blocked di menit 0 (HF token belum rotate)
- Adapter berhasil convert tapi tidak punya identity (SOUL.md tidak dimasukkan ke Modelfile)
- User tidak merasakan Wikipedia fix (frontend belum deploy ke VPS)

---

## 🔴 CRITICAL GAPS (Must Fix Before Execute)

### GAP-1: HF Token Rotation — OVERDUE, Blocker untuk Upload
**Severity:** CRITICAL | **Owner:** Fahmi (user action) + Claude (save ke VPS)

Token `hf_<REDACTED_DAY54>` sudah exposed di chat history Day 54. Sampai token di-rotate:
- Siapapun dengan access ke history bisa push ke repo HF Tiranyx
- Upload GGUF ke HF (step A) tidak bisa dilakukan dengan token yang aman
- Ini adalah **prerequisite hard blocker** untuk seluruh Task A

**Rekomendasi:**
1. Fahmi HARUS revoke token lama + buat fine-grained token baru SEBELUM Claude spawn RunPod
2. Claude HARUS save token baru ke `/opt/secrets/migancore/hf_token` dengan `chmod 600`
3. Update plan: tambahkan HF token rotation sebagai **Task 0** (sebelum semua task lain)

---

### GAP-2: SOUL.md Tidak Dimasukkan ke Ollama Modelfile
**Severity:** CRITICAL | **Owner:** Claude

Plan menulis:
```bash
ollama create migancore:0.1 --from migancore-7b-soul-v0.1.q4_k_m.gguf
```

Tanpa `Modelfile` yang mendefinisikan `SYSTEM`, model tidak akan punya identity MiganCore. Adapter hanya men-tune weights — system prompt harus tetap di-pass sebagai context.

**Rekomendasi:**
Buat `Modelfile` sebelum `ollama create`:
```dockerfile
FROM ./migancore-7b-soul-v0.1.q4_k_m.gguf

SYSTEM """
[Isi SOUL.md dari docs/SOUL.md — bagian identity, voice, values]
"""

PARAMETER temperature 0.7
PARAMETER num_ctx 4096
```

Lalu:
```bash
ollama create migancore:0.1 -f Modelfile
```

**Tanpa ini, identity eval pada adapter akan FAIL** karena model tidak tahu siapa "MiganCore" tanpa system prompt.

---

### GAP-3: Frontend Linkify Fix Belum Deploy ke VPS
**Severity:** CRITICAL (UX) | **Owner:** Claude atau Fahmi (manual deploy)

Commit `ed5da81` (linkify) sudah di repo. Tapi file `frontend/chat.html` belum di-copy ke `/www/wwwroot/app.migancore.com/chat.html` di VPS. Sampai deploy:
- User masih melihat `[Soekarno](https://...)` sebagai raw text
- Day 55 Wikipedia fix tidak terasa end-to-end

**Rekomendasi:**
Tambahkan ke Day 56 pre-task:
```bash
# Deploy frontend fix (jika belum)
scp frontend/chat.html root@72.62.125.6:/www/wwwroot/app.migancore.com/
# Atau via aaPanel File Manager upload
```

---

## 🟡 MEDIUM GAPS (Should Fix Before Execute)

### GAP-4: Missing GGUF Integrity Check Post-Conversion
**Severity:** MEDIUM | **Owner:** Claude

Plan tidak ada step untuk verify GGUF file valid sebelum upload ke HF. Risiko:
- Convert bisa produce corrupt file (llama.cpp convert_hf_to_gguf bug)
- Upload 4.7GB corrupt file = waste bandwidth + time
- Ollama pull corrupt file = crash atau silent fail

**Rekomendasi:**
Tambahkan post-conversion verification:
```bash
# Test load dengan llama.cpp (quick inference test)
python3 -c "
from llama_cpp import Llama
llm = Llama('/workspace/migancore-7b-soul-v0.1.q4_k_m.gguf', n_ctx=512, verbose=False)
out = llm('Hello, my name is', max_tokens=10)
print('GGUF OK — output:', out['choices'][0]['text'])
"

# Atau minimal: check file size dan magic bytes
ls -lh /workspace/migancore-7b-soul-v0.1.q4_k_m.gguf
file /workspace/migancore-7b-soul-v0.1.q4_k_m.gguf
```

---

### GAP-5: Missing A/B Rollout Plan (100% Cutover Risk)
**Severity:** MEDIUM | **Owner:** Claude

Plan menulis: "If PROMOTE: API DEFAULT_MODEL updated" — ini adalah **100% traffic cutover** dalam 1 command. Jika adapter degrades identity, semua user terkena.

**Rekomendasi:**
Tambahkan gradual rollout:
1. **Phase 1:** Test endpoint terpisah (bukan production)
   ```bash
   curl -X POST http://localhost:18000/v1/agents/[id]/chat \
     -H "X-Test-Model: migancore:0.1" \
     -d '{"message":"Siapa kamu?"}'
   ```
2. **Phase 2:** A/B via header opt-in (10% traffic willing)
3. **Phase 3:** Full cutover only after 24h stable + eval pass

Atau minimal: document rollback command dengan timer:
```bash
# Auto-rollback timer — if eval fails dalam 30 menit
(sleep 1800 && docker exec ado-api-1 python3 eval/run_identity_eval.py ... || rollback)
```

---

### GAP-6: `<SNAPSHOT_ID>` Placeholder Belum Diisi
**Severity:** MEDIUM | **Owner:** Claude

Script merge menggunakan placeholder:
```python
base_path = "/workspace/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/<SNAPSHOT_ID>"
```

Snapshot ID perlu dicari dari volume sebelum script dijalankan. Jika salah, merge gagal.

**Rekomendasi:**
Tambahkan pre-merge discovery step:
```bash
SNAPSHOT=$(ls /workspace/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/ | head -1)
echo "Using snapshot: $SNAPSHOT"
```

---

### GAP-7: Budget Underestimation untuk Retry Scenario
**Severity:** LOW-MEDIUM | **Owner:** Claude

Plan budget: ~$1.20 (A100 45 min @ $1.49/hr).

Tapi jika:
- `merge_and_unload()` OOM → retry dengan params berbeda (+30 min)
- GGUF convert error → install dependencies ulang (+15 min)
- HF upload fail → retry (+10 min)

Realistic worst case: **~$2.50–3.00** (2x time + overhead).

**Rekomendasi:**
Update budget projection dengan retry buffer:
```
Optimistic: $1.20 (1-pass success)
Realistic:  $1.80 (1 retry)
Worst case: $3.00 (multiple retries)
```

Saldo RunPod $15.77 masih aman untuk worst case.

---

## 🟢 MINOR NOTES (Nice to Have)

### NOTE-1: `device_map="cpu"` vs `"auto"`
Plan pakai `device_map="cpu"` untuk merge — ini AMAN tapi LAMBAT (~20-30 min untuk 7B). A100 80GB bisa handle `device_map="auto"` (GPU-accelerated, ~5-8 min). Tradeoff: safety vs speed.

**Verdict:** Keep `cpu` — Lesson #83 (save to disk, avoid volume quota) lebih penting daripada speed.

### NOTE-2: DigitalOcean AMD Backup Belum Divalidasi
Plan menyebut DigitalOcean AMD MI300X sebagai backup ($100 credit). Tapi belum ada:
- Validated bahwa DO GPU droplet tersedia di region yang dekat
- Verified Axolotl bisa jalan di ROCm (AMD)
- Tested network speed ke DO dari Indonesia

**Verdict:** OK untuk sekarang — backup plan cukup disebutkan. Validate hanya jika RunPod gagal 2x.

### NOTE-3: STRATEGIC_VISION_2026_2027.md — Stale Uptime Metric
File menulis `Uptime: 0% (502)` di KPI table. Fakta saat ini: API v0.5.16 healthy (curl return `{"status":"healthy"}`).

**Rekomendasi:** Update ke `99%` (reflecting current stability post-Day 55 fix).

---

## Revised Priority Order untuk Day 56

```
Task 0 (NEW): HF token rotation — Fahmi revoke + create new → Claude save ke VPS
Task 0.5 (NEW): Frontend deploy — scp chat.html ke VPS (if not done)
Task A:  Adapter conversion (PEFT → GGUF → Ollama)
Task B:  Identity eval recalibration
Task C:  Synthetic pipeline check
Task D:  DAY56_RETRO.md + MEMORY.md update
```

---

## Risk Register Update

| Risk | Prob | Impact | Status | Mitigation (baru) |
|------|------|--------|--------|-------------------|
| HF token belum rotate | HIGH | HIGH | 🔴 NEW | Task 0 — user action prerequisite |
| Adapter tanpa SOUL.md | MED | HIGH | 🔴 NEW | Modelfile dengan SYSTEM prompt |
| Frontend belum deploy | MED | MED | 🔴 NEW | scp/aaPanel manual deploy |
| GGUF corrupt post-convert | LOW | MED | 🟡 NEW | Post-conversion inference test |
| 100% cutover degrade UX | LOW | HIGH | 🟡 NEW | Gradual rollout / header opt-in |

---

## Sign-Off

**Kimi Review:**
> DAY56_PLAN.md structurally solid, vision-aligned, budget-conscious. Tapi **3 critical gaps** (HF token, SOUL.md Modelfile, frontend deploy) harus diperbaiki sebelum eksekusi. Tanpa perbaikan ini, Day 56 berisiko blocked atau menghasilkan adapter tanpa identity.
>
> **Rekomendasi:** Claude perlu update plan dengan Task 0 (HF token + frontend deploy), dan pastikan Modelfile dibuat dengan SYSTEM prompt dari SOUL.md.

**Status:** REVIEWED — DEPLOY APPROVED setelah critical gaps di-fix.

---

*Review completed: 2026-05-06*
*Next: Validate Claude's Day 56 execution against revised priority*
