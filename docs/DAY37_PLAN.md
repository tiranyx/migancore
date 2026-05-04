# Day 37 Plan — Teacher API Activation + Onboarding Pivot
**Date:** 2026-05-04 (Day 37, Bulan 2 Week 5 Day 2)
**Drafted by:** Claude Sonnet 4.6
**Triggered by:** User mandatory protocol: "Oke gas + research-first + hypothesis/risk/benefit framework"
**Research source:** `docs/DAY37_TEACHER_API_ANALYSIS.md` + parallel research synthesis 2025-2026 trends

---

## 🧭 1. RESEARCH SYNTHESIS — Apa yang Berubah

### Trends yang harus diadopsi
| Domain | Pattern 2026 | Source |
|--------|--------------|--------|
| Synthetic data | **2-of-4 judge quorum** > single judge (-30% bad pairs) | Nemotron-4 340B recipe (arxiv 2406.11704) |
| Synthetic prompts | **Magpie self-extract** > human seeds | Magpie-Align (arxiv 2406.08464) |
| Preference learning | SimPO + **APO identity loss** (λ=0.1, anchor) | APO arxiv 2408.06266 |
| Onboarding UX | **Two-question** > template picker (Cursor/Claude killed multi-template Q1 2026) | Perplexity Spaces, Letta blog Mar 2026 |
| Reasoning | **R1 chain-of-thought distillation** (Cycle 2) | DeepSeek-R1 arxiv 2501.12948 |
| Distribution | **Smithery.ai listing** = free top-of-funnel | smithery.ai (2k+ servers) |

### Anti-patterns 2026
- ❌ Edge MoE pada CPU 32GB (Qwen3-30B-A3B = throughput collapse)
- ❌ KTO pada <5k pairs (loses to SimPO sampai 5k+)
- ❌ **Multi-template picker** (deprecated Q1 2026)

---

## 🎯 2. DAY 37 PIVOT — DARI CHECKPOINT KEMARIN

### Yang berubah dari `DAY36_CHECKPOINT.md`
| Item | Kemarin (CHECKPOINT) | Hari ini (DAY37 setelah riset) |
|------|----------------------|-------------------------------|
| Onboarding | Template picker (Customer Success/Research/Code Pair) | **Two-question + dynamic starter cards** |
| Synthetic judge | Gemini Flash sendirian | **Kimi+Gemini quorum** (consensus required) |
| Sourcing prompts | Hanya seed_bank.py 120 hardcoded | + **Magpie self-extract module** (Day 38) |
| Identity preservation | Cosine sim ≥0.85 setelah training | + **APO loss term** dalam training (Day 38) |

### Kenapa pivot?
- Multi-template picker = **investasi UI yang lab besar sudah deprecate**. Jangan build yang sudah dibatalkan industri.
- Single judge punya bias 30%. Quorum lebih murah dari 1× Claude tapi quality 2-3x lipat.
- APO identity loss adalah **murah** (1 line tambahan dalam SimPO loss) tapi kritis untuk pass identity gate.

---

## 📐 3. HIPOTESIS + RISK/BENEFIT FRAMEWORK (per-item)

### ITEM 1 — Two-Question Onboarding + Dynamic Starter Cards

**Hipotesis:** Beta user yang dapat 3 starter cards yang **dinamis berdasarkan answer mereka** akan punya first-message rate ≥80% (vs ~30% kalau chat kosong).

**Adaptasi kalau gagal:** Fallback ke 4 hardcoded starter cards (proven minimum). Two-question tetap dipertahankan karena memberi user VALUE bahkan kalau dynamic gen down (kita tahu use case + bahasa preference).

**Impact:** Onboarding bounce ≤30% (vs estimasi ≥80% saat ini).
**Benefit:** **Membuka exit-criteria Bulan 2 ("5 beta users active").** Tanpa ini, beta launch fail.
**Risk:**
- LOW — frontend-only, tidak ada DB migration
- MEDIUM — Gemini API call latency (1-2s) bisa terasa di first-run; mitigated by skeleton state + fallback hardcoded

**Effort:** ~4 jam (chat.html + new endpoint `/v1/onboarding/starters`)

---

### ITEM 2 — Kimi+Gemini Judge Quorum di CAI Pipeline

**Hipotesis:** Pair acceptance rate naik dari ~40% (Ollama 7B judge) → ~60% **dengan kualitas score gap meningkat 1.5x** (Nemotron paper data extrapolation untuk dataset 7B-scale).

**Adaptasi kalau gagal:** ENV `JUDGE_BACKEND=ollama` rollback instant. Semua judge call wrapped in try/fallback.

**Impact:**
- Velocity: synthetic gen 5-10x faster (judge 1-2s vs Ollama 10-20s)
- Cost: Kimi $0.60/1M in + Gemini $0.075/1M in × ~500 critique calls × ~1500 tokens = **~$0.50 untuk hit 500 pairs** (well under budget)
- Quality: Less reward hacking, less self-bias

**Benefit:** Hit 500 DPO pairs by Day 38 EOD (vs Day 39-40 dengan Ollama-only).
**Risk:**
- LOW — backend-only, ENV-flagged, fallback chain robust
- MEDIUM — Kimi K2.6 API rate limit (60 RPM tier 1); mitigated dengan exponential backoff sudah ada

**Effort:** ~3 jam (cai_pipeline.py + config + test)

---

### ITEM 3 — Identity Eval Baseline Dry-Run

**Hipotesis:** Baseline Qwen2.5-7B akan score cosine sim ~0.92-0.97 vs reference (high karena same model, but tests pipeline correctness).

**Adaptasi kalau gagal:** Fix script issue lokal (embedding model path, JSON format) sebelum trigger SimPO ($5.50 saved).

**Impact:** Confirm pipeline before paid run.
**Benefit:** Cegah waste $5.50 RunPod kalau eval pipeline broken.
**Risk:** LOW — only runs locally, no API cost.

**Effort:** ~30 menit (run script, document result)

---

### ITEM 4 (DEFER Day 38) — Magpie Self-Extract Module

**Hipotesis:** Magpie-style self-extract dari Qwen2.5-7B akan generate 200 prompts yang **better match training distribution** (in-distribution) → quality score gap 1.2x lebih tinggi vs hardcoded seeds.

**Why defer:** Item 1+2 sudah prioritas. Magpie membutuhkan riset implementasi lebih dalam (Llama-3 reference impl, arxiv 2406.08464).

---

### ITEM 5 (DEFER Day 38-39) — APO Identity Loss in SimPO

**Hipotesis:** APO λ=0.1 dengan 50 anchor prompts → identity preservation ≥0.90 cosine (vs SimPO-only yang sering drop ke 0.80-0.85).

**Why defer:** Cycle 1 belum trigger. Implementasi APO 2 jam, tapi cocok dilakukan **bareng** dengan trigger SimPO Day 39.

---

## 📊 4. KPI PER-DAY SPRINT (Day 37-42)

### Day 37 (Today)
| KPI | Target | Baseline | Verifikasi |
|-----|--------|----------|------------|
| chat.html v0.5.3 deploy | live | v0.5.2 | `curl /health` → 0.5.3 |
| Two-question onboarding | functional incognito test | not exists | Manual E2E |
| `/v1/onboarding/starters` endpoint | HTTP 200, returns 3 prompts | not exists | curl test |
| CAI judge quorum (`JUDGE_BACKEND=quorum`) | enabled, falls back gracefully | Ollama only | log shows `cai.judge.backend=quorum` |
| Identity eval baseline | result documented | never run | output JSON in `eval/` |
| Synthetic gen alive | running, last_24h ≥+30 pairs | 277 (last_24h=277) | `/v1/public/stats` |

### Day 38
| KPI | Target |
|-----|--------|
| DPO pool | ≥400 pairs |
| Magpie self-extract module | code shipped |
| Distillation Kimi small batch | 10 pairs added |
| Onboarding bounce metric | first beta tester E2E pass |

### Day 39
| KPI | Target |
|-----|--------|
| DPO pool | ≥500 pairs ⭐ TRIGGER SimPO |
| APO identity loss | added to train_simpo.py |
| RunPod budget locked | $7 cap |

### Day 40
| KPI | Target |
|-----|--------|
| SimPO Cycle 1 | training complete |
| migancore-7b-soul-v0.1 GGUF | converted Q4_K_M |
| Identity eval v0.1 | ≥0.85 cosine |

### Day 41
| KPI | Target |
|-----|--------|
| Hot-swap v0.1 | live OR rollback documented |
| A/B framework | enabled (10% traffic) |
| Smithery listing | live (or in-review) |

### Day 42
| KPI | Target |
|-----|--------|
| 24h A/B metrics | win-rate documented |
| Promote OR rollback | decision made |
| Week 5 Retro | committed |

---

## 💰 5. BUDGET WEEK 5 (with Teacher API activation)

| Item | Estimate |
|------|----------|
| CAI judge quorum (Kimi+Gemini, 500 pairs) | $0.50 |
| Distillation Kimi small batch (Day 38) | $1.00 |
| Onboarding starter prompts (Gemini, ~200 sessions) | $0.05 |
| Identity eval (Gemini compare augment) | $0.05 |
| RunPod SimPO Cycle 1 | $5.50 |
| Buffer | $1.00 |
| **TOTAL** | **~$8.10** |

Per BULAN2_PLAN budget: $30 → spend Week 5 = 27%. ✅ Under budget.

---

## 🧪 6. TESTING + VALIDATION PROTOCOL (Post-Execution)

Setelah deploy v0.5.3:
1. **Smoke test:**
   - `curl /health` → version 0.5.3
   - `curl /v1/onboarding/starters?usecase=research&lang=id` → 3 prompts JSON
   - Incognito browser → onboarding modal muncul → 2 pertanyaan → starter cards
2. **CAI quorum test:**
   - Force one chat turn → check logs `cai.judge.backend=quorum, kimi_score=X, gemini_score=Y, consensus=true|false`
   - If `consensus=false` → pair skipped, log `cai.no_consensus`
3. **Synthetic gen restart with quorum:**
   - SSH VPS: kill old run, restart `start_synthetic_generation(target_pairs=1000)`
   - Monitor 1hr → expect ≥10 new pairs (vs ~5 with Ollama-only)
4. **Identity eval baseline:**
   - `python eval/run_identity_eval.py --model qwen2.5:7b > eval/baseline.json`
   - Document score in `docs/DAY37_PROGRESS.md`

---

## ✅ 7. EXIT CRITERIA — Day 37 (must-have before commit "Day 37 done")

- [ ] Two-question onboarding live (incognito E2E pass)
- [ ] Dynamic starter cards (3 prompts) atau hardcoded fallback
- [ ] `/v1/onboarding/starters` endpoint functional
- [ ] CAI quorum mode flagged via `JUDGE_BACKEND=quorum` (default `ollama` for safety)
- [ ] Quorum fallback chain tested (kalau Kimi gagal → Gemini sendiri; kalau dua gagal → Ollama)
- [ ] v0.5.3 deployed + healthcheck pass
- [ ] Synthetic generator alive verified
- [ ] Identity eval baseline result committed
- [ ] `docs/DAY37_PROGRESS.md` written
- [ ] `memory/day37_progress.md` + MEMORY.md index updated

---

## 🎓 8. LESSONS APPLIED (dari sprint sebelumnya)

1. ✅ Compass doc anti scope-creep (DAY36_CHECKPOINT pattern)
2. ✅ Research first sebelum invest UI besar (Day 36 lesson — multi-template picker would have been wasted)
3. ✅ ENV flag rollback (Day 36 nginx — safe iteration)
4. ✅ Cost discipline >$1 = stop+ask (Week 4 lesson)
5. ✅ Container `--build` mandatory (Day 28 lesson)
6. ✅ Friendly error mapping (Day 36) — apply same pattern in onboarding errors
7. ✅ Document hypothesis/risk/benefit per-item (kickoff doc protocol)

---

**THIS IS THE COMPASS for Day 37. Execute Item 1+2+3 hari ini, defer 4+5 ke Day 38-39.**
