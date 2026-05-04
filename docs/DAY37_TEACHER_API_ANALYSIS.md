# Day 37 — Teacher API: Riset, Analisa, Re-positioning

**Date:** 2026-05-04 (Day 37 morning, Bulan 2 Week 5 Day 2)
**Trigger:** User minta audit "bagaimana dengan teacher API kita?"
**Purpose:** Identifikasi peran teacher API saat ini, gap, dan re-positioning untuk akselerasi Bulan 2 Week 5 (target SimPO Cycle 1).

---

## 📋 1. APA YANG SUDAH KITA PUNYA (Inventory)

### 4 Teachers — semuanya wired + verified Day 28
| Teacher | Endpoint | Model | Status | Bahasa ID |
|---------|----------|-------|--------|-----------|
| Anthropic Claude | `api.anthropic.com/v1/messages` | `claude-sonnet-4-5` | ✅ verified | bagus |
| Moonshot Kimi | `api.moonshot.ai/v1/chat/completions` | `kimi-k2.6` | ✅ verified (thinking disabled, temp 0.6) | **terbaik (native bilingual)** |
| OpenAI GPT | `api.openai.com/v1/chat/completions` | `gpt-4o` | ✅ verified | bagus |
| Google Gemini | `generativelanguage.googleapis.com` | `gemini-2.5-flash` | ✅ verified (BLOCK_NONE safety) | bagus |

**Kode:** `api/services/teacher_api.py` — uniform interface `call_teacher(name, prompt, system, max_tokens) → TeacherResponse(text, in_tok, out_tok, cost_usd, provider, model)`. Built-in retry x3 + exponential backoff + cost tracking.

### Harga (Mei 2026, $/1M tokens)
| Teacher | Input | Output | Catatan |
|---------|-------|--------|---------|
| **Gemini 2.5 Flash** | **$0.075** | **$0.30** | **TERMURAH 40x dari Claude** |
| Kimi K2.6 | $0.60 | $2.50 | Bilingual terbaik |
| GPT-4o | $2.50 | $10.00 | Mid-tier |
| Claude Sonnet 4.5 | $3.00 | $15.00 | Termahal, best for judge |

### Endpoint admin yang sudah live
- `POST /v1/admin/distill/start` — `{teacher, target_pairs, budget_usd}`
- `GET /v1/admin/distill/status` — live status
- `POST /v1/admin/distill/stop` — cancel
- `GET /v1/admin/distill/summary` — aggregate per teacher

### Konfigurasi proteksi
- `DISTILL_BUDGET_USD_HARD_CAP = $10` per run
- `DISTILL_MARGIN_THRESHOLD = 2.0` (judge diff minimum untuk pair tersimpan)

---

## 🔍 2. BERAPA YANG SUDAH KEPAKE (Honest Audit)

| Source method | Pairs | % Pool |
|---------------|-------|--------|
| `synthetic_seed_v1` | 262 | 95% |
| `cai_pipeline` | 15 | 5% |
| `distill_kimi_v1` | **0** | 0% |
| `distill_claude_v1` | **0** | 0% |
| `distill_gpt_v1` | **0** | 0% |
| `distill_gemini_v1` | **0** | 0% |
| **TOTAL** | **277** | — |

**Kesimpulan jujur:** Teacher API **terinstal sempurna tapi tidak menghasilkan satu pair pun**. Total spend teacher dari Week 4: **<$0.05** (hanya tes verify).

### Kenapa stuck? (Root cause Week 4 retro)
- **Bottleneck: Ollama student step.** Pipeline distillation = `seed → student (Ollama 7B CPU) → teacher API → judge → margin filter`. Step student di Ollama CPU 30-90s per call = throughput chokepoint.
- Distillasi pernah dicoba 7x di Week 4 → 6 errors. Sekarang stable, tapi belum di-rerun.
- Synthetic generator juga sebenarnya pakai Ollama (untuk judge + revise) → bottleneck yang sama.

---

## 💡 3. RE-POSITIONING — 4 PERAN STRATEGIS BARU

Teacher API tidak harus hanya jadi "data source distillation". Ada 4 peran yang BIG IMPACT:

### Peran A — Synthetic generator JUDGE (HIGHEST ROI ⭐)
**Kondisi sekarang:** CAI pipeline pakai Ollama untuk critique + revise. Judge step lambat (10-20s per seed) + kualitas ribut (Qwen2.5-7B menjadi judge atas dirinya sendiri = bias).

**Proposal:** Pakai **Gemini 2.5 Flash** sebagai judge replacement.
- Speed: 1-2 detik per critique (vs Ollama 10-20s)
- Kualitas: Gemini 2.5 Flash > Qwen2.5-7B sebagai judge (eksternal, less bias)
- Cost per critique: ~500 tokens × $0.30/1M = **$0.00015 per pair**
- 500 pairs × $0.00015 = **$0.075 untuk hit 500-pair training threshold**

**Result:** Synthetic generator velocity 10x. Hit 500 pairs Day 38 (vs Day 39-40).

### Peran B — Distillation REAL run (verify pipeline)
Distillation pipeline live tapi belum pernah produce pair. **Risk:** Ada bug yang tersembunyi sampai kita mau jalankan production.

**Proposal:** Run small batch sebelum production:
- Teacher: **Kimi K2.6** (bilingual paling cocok)
- Target: 10 pairs (small, safe)
- Budget: $1 hard cap
- Use existing endpoint `POST /v1/admin/distill/start`

**Result:** Pipeline E2E verified, tahu margin 2.0 realistic atau perlu adjust, dataset gain 10 fresh pairs.

### Peran C — Onboarding helper (NEW use-case)
First-Run modal dari Day 36 CHECKPOINT punya butuh: 3-5 example prompts personalized berdasarkan template pilihan user.

**Proposal:** Pakai **Gemini Flash** generate starter prompts on-demand:
- User pilih template "Research Companion"
- POST `/v1/onboarding/starter-prompts` → returns 4 fresh starter cards
- Cost: ~200 tokens × $0.30/1M = **$0.00006 per onboarding**
- 100 beta users = $0.006 total

**Result:** Onboarding feels personalized + dynamic, not stale hardcoded prompts.

### Peran D — Memory consolidation (DEFER Bulan 3)
Long conversations → summarize ke episodic memory dengan teacher (vs Ollama). Skip dulu — ada bottleneck lain yang lebih urgent.

---

## ⚠️ 4. APA YANG TIDAK BOLEH (Anti-pattern)

❌ **Replace Ollama sebagai inference backend chat utama** — ini melanggar visi ADO ("self-hosted brain"). Pengguna bicara dengan MiganCore (Qwen2.5-7B → soon migancore-7b-soul-v0.1), bukan Claude wearing migancore mask.

❌ **Distillation skala besar (target_pairs=200+) sebelum verify small batch** — risk burn $5-10 budget cap tanpa pair berharga.

❌ **Pakai Claude untuk semua peran** — paling mahal (50x dari Gemini Flash). Reserve Claude untuk **judge** di SimPO eval atau A/B test (dimana presisi penting).

---

## 🎯 5. KEPUTUSAN — DAY 37 ACTION ITEMS

### Priority 1 — Gemini judge integration (Peran A) ⭐ HIGHEST ROI
**Effort:** 3 jam coding + test
**Impact:** Synthetic velocity 10x → hit 500 pairs by Day 38 (3 hari lebih cepat)
**Cost:** <$0.10 untuk hit 500
**Implementasi:**
1. Add `JUDGE_BACKEND` env var: `ollama` (default) | `gemini`
2. CAI pipeline: kalau `JUDGE_BACKEND=gemini`, panggil `call_teacher('gemini', ...)` instead of Ollama judge
3. Fallback: kalau Gemini error → graceful degrade ke Ollama
4. Cost tracking di Redis: `synthetic:run:<id>:judge_cost_usd`
5. Add log `cai.judge.backend=gemini` untuk observability

### Priority 2 — Onboarding first-run modal (carryover dari CHECKPOINT)
**Effort:** 4 jam
**Impact:** Bukan 5 beta dari "chat kosong"
**Implementasi:** sama persis dengan rencana CHECKPOINT (template picker + starter cards + tooltip)
- **BONUS:** integrate Peran C (Gemini Flash dynamic starter prompts) kalau ada waktu sisa

### Priority 3 — Distillation small-batch verify (Peran B)
**Effort:** 1 jam (curl admin endpoint, monitor)
**Impact:** Pipeline confidence + 10 pair gain
**Cost:** ≤$1
**Trigger:** Setelah Priority 1 done, run kalau Ollama bandwidth ada
**Command:**
```bash
curl -X POST https://api.migancore.com/v1/admin/distill/start \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -d '{"teacher":"kimi","target_pairs":10,"budget_usd":1.0}'
```

### Priority 4 — Identity eval baseline dry-run (carryover dari CHECKPOINT)
**Effort:** 30 min
**Impact:** Catch eval pipeline issue before SimPO trigger
**Command:**
```bash
python eval/run_identity_eval.py --model qwen2.5:7b --output baseline.json
```

---

## 💰 6. BUDGET PROJECTION — WEEK 5 TEACHER SPEND

| Item | Cost estimate |
|------|---------------|
| Gemini judge for 500 synthetic pairs | $0.10 |
| Distillation Kimi small batch (10 pairs) | $1.00 |
| Onboarding starter prompts (100 users) | $0.01 |
| Identity eval baseline (Gemini compare) | $0.05 |
| Buffer / experiments | $1.00 |
| **TOTAL Week 5** | **~$2.20** |

Per BULAN2_PLAN budget Anthropic+Kimi+OpenAI+Gemini = $23. Week 5 spend di bawah 10% allocated. ✅

---

## 🚦 7. EXIT CRITERIA — Day 37

- [ ] `JUDGE_BACKEND=gemini` env var live + CAI pipeline switch implemented
- [ ] Synthetic generator restart dengan Gemini judge — log shows `cai.judge.backend=gemini`
- [ ] Onboarding First-Run Modal live di `app.migancore.com`
- [ ] Empty-state starter cards (4 prompts hardcoded for now, dynamic later)
- [ ] v0.5.3 deployed + healthcheck pass
- [ ] DPO velocity check Day 37 EOD: target ≥350 pairs (start 277, +73 in 1 day)
- [ ] **(stretch)** Distillation Kimi 10-pair batch executed
- [ ] **(stretch)** Identity eval baseline result documented
- [ ] `docs/DAY37_PROGRESS.md` + `memory/day37_progress.md` committed

---

## 📌 8. PERTANYAAN UNTUK USER (sebelum eksekusi)

**Q1:** OK gas Priority 1+2 (Gemini judge + Onboarding modal)?
**Q2:** Distillation small batch (Priority 3, $1) dijalankan Day 37 atau Day 38?
**Q3:** Onboarding starter prompts → hardcoded dulu (faster ship) atau langsung dynamic via Gemini (Peran C, +1 jam)?

---

**THIS IS THE TEACHER API COMPASS for Day 37+. Refer back if drift.**
