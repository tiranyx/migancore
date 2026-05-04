# Day 38 Plan — Beta Unblockers + Cycle 1 Trigger
**Date:** 2026-05-04 (Day 38, Bulan 2 Week 5 Day 3)
**Drafted by:** Claude Sonnet 4.6 after parallel research agent + 1230WIB recap
**Triggered by:** User mandatory protocol — "Catat plan Day 38, jangan lupa protokol"
**Research source:** `agent_aa797a1d` brief (vision/STT/speculative/Magpie 2025-2026 trends)

---

## 🧭 1. CONTEXT INHERITED FROM DAY 37

| Item | State Day 38 morning |
|------|----------------------|
| API version | v0.5.3 live |
| DPO pool | 286 (target 500 for SimPO trigger) |
| Synthetic gen | running, ~20-76 pairs/hr (variable load) |
| ETA 500 pairs | ~5-12 hours from restart (Day 38 mid-morning) |
| RunPod saldo | **$16.17** (key dropped Day 38) |
| Bulan 2 spend | ~$0.10 of $30 cap (0.3%) |
| Live recap (1230 WIB) | flagged image analysis as hidden Bulan 2 Week 6 BETA BLOCKER |

---

## 🔬 2. RESEARCH SYNTHESIS (3 game-changers + 4 verdicts)

### Game-changers
1. **Gemini 2.5 Flash Vision = $0.00008/image** — basically FREE. 1024px image = ~258 tokens. Bilingual ID+EN solid.
2. **Magpie-Qwen2.5-Pro-300K-Filtered** (HuggingFace dataset) — pre-filtered 300K instructions ready to download. **Skip writing extraction code entirely.**
3. **ElevenLabs Scribe v2 WER 2.4% vs Whisper-v3 7.7% Indonesian** — 3x more accurate, $0.0037/min batch.

### Verdicts
| Topic | Verdict | Action |
|-------|---------|--------|
| Vision API | Gemini 2.5 Flash > Claude (60x cheaper for text-out) | Ship Day 38 |
| STT | Scribe v2 batch mode for MVP, realtime defer Day 40 | Ship Day 38 batch |
| Speculative decoding | SKIP for CPU (overhead > savings); use llama.cpp server on RunPod 4090 instead of Ollama | Defer Day 40+ |
| Magpie self-extract | DON'T BUILD — HuggingFace dataset exists | Download instead |

### Surprise findings
- **Gemini Flash Image (Nano Banana)** $0.039/image vs fal.ai $0.05-0.10 — A/B candidate (defer Bulan 2 Week 7)
- **Qwen3 series released** — upgrade path Qwen2.5-7B → Qwen3-7B free quality bump (defer Day 50+)
- **llama.cpp ngram-cache speculative** = no second model needed, lower CPU overhead — alternative path (defer)

---

## 📐 3. DAY 38 TASK LIST — H/R/B FRAMEWORK

### TRACK A — Beta Unblockers (MUST SHIP, blocks Week 6)

#### A1 — `analyze_image` tool via Gemini Vision ⭐ HIGHEST PRIORITY
**Hipotesis:** User attach image → MiganCore can describe/extract text/answer questions about content, latency <3s, cost <$0.001/image.
**Adaptasi gagal:** Fallback ke Claude Vision (60x cost but reliable). Worst case skip image, log error.
**Impact:** Closes #1 Bulan 2 Week 6 beta blocker (recap finding).
**Benefit:** Multimodal MVP ready before beta launch in 5 days.
**Risk:**
- LOW — backend integration only, well-documented Gemini SDK
- MEDIUM — Gemini occasional 5xx; mitigated by Claude fallback + ENV flag

**Effort:** ~3 jam
- New `services/vision.py` (Gemini call wrapper)
- New tool handler `_analyze_image` in `tool_executor.py`
- Register in `TOOL_REGISTRY` + chat tool prompts
- Optional: MCP exposure (nice-to-have)

**Test:** Pass image URL + "Apa isi gambar ini?" → JSON description in <3s.

#### A2 — STT endpoint via ElevenLabs Scribe v2
**Hipotesis:** Voice input → Indonesian transcription with WER ≤5% in <2s for 10-second audio.
**Adaptasi gagal:** Skip STT for now; user types. Don't break chat.
**Impact:** Voice-first beta cohort ready (some users prefer voice).
**Benefit:** Differentiator vs typed-only competitors; matches "AI yang ngerti gue" narrative.
**Risk:**
- LOW — ElevenLabs API mature, key live
- MEDIUM — frontend mic capture (no implementation yet); ship backend first, frontend Day 39

**Effort:** ~3 jam
- `POST /v1/speech-to-text` endpoint (multipart audio upload, model_id=scribe_v2)
- Service wrapper `services/stt.py`
- Test with sample WAV/MP3 ID + EN
- Frontend mic UI defer Day 39

**Test:** Upload 10-sec ID audio → text response.

---

### TRACK B — Cycle 1 Pre-flight (saves $5.50 if pipeline broken)

#### B1 — Identity eval baseline
**Hipotesis:** Baseline Qwen2.5-7B → cosine sim ~0.92-0.97 (high because self-comparison; tests pipeline correctness).
**Adaptasi gagal:** Fix script issues locally before SimPO trigger. Save $5.50.
**Impact:** Catches eval bugs before paid run.
**Benefit:** $5.50 saved if pipeline broken; baseline data point for v0.1 comparison.
**Risk:** LOW — local Ollama only, no API cost.

**Effort:** ~30 min (run script + commit `eval/baseline.json`)

**Trigger:** Run when DPO pool ≥450 (close to threshold) to balance Ollama load with synthetic.

#### B2 — APO identity loss term in `train_simpo.py`
**Hipotesis:** APO λ=0.1 + 50 anchor prompts → identity preservation ≥0.90 cosine post-training (vs SimPO-only that often drops to 0.80-0.85).
**Adaptasi gagal:** Skip APO, run vanilla SimPO. Identity might drop but recoverable.
**Impact:** Identity gate pass rate higher → fewer rollbacks.
**Benefit:** Pre-wire for SimPO trigger.
**Risk:** LOW — additive loss term, doesn't break vanilla SimPO.

**Effort:** ~1 jam (read APO paper section + add `apo_loss = beta * neg_logp_anchor.mean()` + add `--use_apo` CLI flag)

---

### TRACK C — Quality Multiplier (game-changer SHORTCUT)

#### C1 — Download Magpie-Qwen2.5-Pro-300K-Filtered as seed pool 🎁
**Hipotesis:** 300K Magpie prompts (3x diversity vs hardcoded 120 seed_bank.py) → CAI quorum produces 10-100x more pairs over time.
**Adaptasi gagal:** Keep using hardcoded seed_bank.py (still works, just slower).
**Impact:** Removes Day 19/21 seed-bank ceiling. Long-term DPO pool growth unblocked.
**Benefit:** Dataset diversity covers ~99% MMLU domains (vs ~40% hardcoded) → less identity drift, better generalization.
**Risk:** LOW — just a dataset swap, existing CAI pipeline handles it.

**Effort:** ~1 jam
- Download `Magpie-Align/Magpie-Qwen2.5-Pro-300K-Filtered` (Parquet, ~200MB)
- Add loader option in `seed_bank.py`: `SEED_SOURCE=magpie_300k|hardcoded`
- ENV flag, default keeps hardcoded for safety

**Test:** Trigger 1 round with magpie source → 50+ pairs stored.

#### C2 — Distillation Kimi small batch (10 pairs $1 cap)
**Hipotesis:** Pipeline produces 5-10 pairs from 10-seed batch (50% pass margin threshold ≥2.0).
**Adaptasi gagal:** Document failures, debug; pipeline already 476 lines untested in production.
**Impact:** First distillation pairs in pool (currently 0), confirms teacher path works E2E.
**Benefit:** Pipeline confidence + 5-10 fresh pairs.
**Risk:** LOW — $1 hard cap.

**Effort:** ~1 jam (curl admin endpoint, monitor, document)

---

## 📊 4. KPI PER ITEM (Day 38)

| Item | Target | Verifikasi |
|------|--------|------------|
| A1 analyze_image live | tool returns JSON description | curl test 3 sample images (ID, EN, screenshot) |
| A2 STT endpoint | HTTP 200 with transcript | upload 3 sample audios |
| B1 identity baseline | `eval/baseline.json` committed | file exists with 20 entries |
| B2 APO loss in trainer | `--use_apo` flag added | grep `apo_loss` in train_simpo.py |
| C1 Magpie loaded | 1 synthetic round produces ≥30 pairs | DB count by source_method |
| C2 Distill Kimi 10-pair | distill_kimi_v1 ≥5 pairs in DB | `/v1/admin/distill/summary` |
| **DPO pool EOD** | **≥500** | `/v1/public/stats` |

### Gate-and-Trigger
- IF DPO ≥500 by Day 38 EOD → **TRIGGER SimPO Cycle 1** Day 39 morning
- IF DPO <500 → continue synthetic, trigger Day 39 EOD
- IF identity baseline FAILS → fix before any RunPod spend

---

## 💰 5. BUDGET PROJECTION Day 38

| Item | Cost estimate |
|------|---------------|
| Gemini Vision (50 test images) | $0.005 |
| ElevenLabs STT (30 min test audio) | $0.11 |
| Distillation Kimi 10-pair | $1.00 |
| HuggingFace dataset download | $0 |
| Synthetic gen continued (~14 hr quorum) | $0.30 |
| Buffer | $0.55 |
| **Day 38 total** | **~$2.00** |

Cumulative Bulan 2: $0.10 + $2.00 = **$2.10 of $30 cap (7%)**.

If SimPO Cycle 1 triggers Day 38 EOD: +$5.50 → $7.60 cumulative (25% of cap). Still safe.

---

## 🚦 6. EXIT CRITERIA — Day 38

Must-have:
- [ ] `analyze_image` tool live + 3-image E2E test pass
- [ ] STT endpoint HTTP 200 + 3-audio test pass
- [ ] `eval/baseline.json` committed (when DPO ≥450)
- [ ] APO loss term wired (untested but pre-flighted)
- [ ] DPO pool ≥500 OR autonomous on track for Day 39 morning
- [ ] At least one new source_method showing in pool (distill_kimi_v1 OR magpie_seed_v1)
- [ ] `docs/DAY38_PROGRESS.md` + `memory/day38_progress.md` committed

Nice-to-have (stretch):
- [ ] Frontend mic UI for STT (Day 39)
- [ ] MCP exposure of analyze_image
- [ ] Smithery.ai listing (Day 39)

---

## 🛡️ 7. SCOPE BOUNDARIES (re-affirmed)

❌ **DON'T BUILD:**
- Speculative decoding for Ollama CPU (research: net-negative)
- Magpie self-extract code (research: HF dataset exists, don't reinvent)
- WebSocket realtime STT (defer Day 40 with frontend mic UI)
- Realtime image upload UI (Day 39 after backend tool stable)
- Qwen3-7B upgrade (defer Day 50+ post-Cycle 1 stable)
- Gemini Image gen (Nano Banana) replace fal.ai (defer Bulan 2 Week 7 A/B)

✅ **STAY FOCUSED:**
- Multimodal beta-readiness (vision + STT)
- Cycle 1 pre-flight (eval + APO)
- Quality multiplier via Magpie 300K shortcut

---

## 🎓 8. LESSONS APPLIED (from Day 36 + 37)

1. ✅ Compass doc per sprint (this file)
2. ✅ Research-first prevents wasted UI work (Magpie 300K shortcut found via research)
3. ✅ ENV flag rollback on every new feature (`SEED_SOURCE`, `--use_apo`)
4. ✅ Fallback chain priority (Gemini Vision → Claude Vision)
5. ✅ Hardcoded fallback as feature (seed_bank.py default keeps hardcoded)
6. ✅ Live deploy with WIP code beats "perfect locally" (Day 37 lesson 11)
7. ✅ Empirical velocity > theoretical projection (use real Day 37 numbers, not theory)
8. ✅ Stop building what others ship (Magpie filtered dataset = community gift, use it)

---

## 🔭 9. POST-DAY-38 LOOKAHEAD

**Day 39:** Trigger SimPO Cycle 1 ($5.50 RunPod) + frontend mic UI for STT + Smithery.ai listing prep
**Day 40:** SimPO complete + GGUF Q4 convert + identity eval v0.1 ≥0.85 gate + llama.cpp speculative on 4090
**Day 41:** Hot-swap v0.1 to production OR rollback documented + A/B 10% traffic
**Day 42:** 24h A/B win-rate + decision (promote/rollback) + Week 5 Retro

**Bulan 2 Week 6 (Day 43-49):** Beta launch — 5 invited users, 1-on-1 onboarding sessions

---

**THIS IS THE COMPASS for Day 38. 6 items, ~10 jam, $2 budget. Beta-ready by EOD.**
