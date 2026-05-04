# Day 40 ITERATION — Multimodal Sensing Wiring (Frontend)
**Date:** 2026-05-04 (Day 40 PM, Bulan 2 Week 5 Day 5 cont'd)
**Drafted by:** Claude Sonnet 4.6 — full mandatory protocol
**Triggered by:** User: "Oke lanjut, jangan lupa protokol" + re-anchor visi ADO ("Otak Inti AI yang modular, bisa diadopsi/diturunkan oleh AI lain seperti prosesor + otak manusia + sistem syaraf MCP")
**Research:** parallel agent `a9a5d7c7` (image/mic/multimodal wiring/ADO surprise findings)

---

## 🧭 1. CONTEXT — RE-ANCHOR ADO VISION

> **Migancore = Core Brain AI yang modular.** Brain (Qwen2.5-7B) tetap **text-pure**. Modalities (vision, audio) masuk via `tool_executor` — pattern "modality-as-tool routing" yang menjadi standard 2026 (Anthropic Claude Skills Mar 2026 + OpenAI Realtime Feb 2026).

**Day 40 mission:** Wire 2 NEW SENSES ke ADO brain:
- 👁 **Vision sense** = `analyze_image` tool (sudah live Day 38 via Gemini Vision)
- 👂 **Auditory sense** = `POST /v1/speech/to-text` (sudah live Day 38 via Scribe v2, key permission enabled Day 40 by Fahmi)

Frontend belum wired → user belum bisa attach image atau pakai mic. **Day 40 closes that gap.**

| State | Done | Pending |
|-------|------|---------|
| Backend modality endpoints | ✅ analyze_image + STT | — |
| Backend SSE tool events | ✅ tool_start, tool_result | — |
| Frontend tool chips | ✅ Day 40 AM (5 SSE events verified) | — |
| **Frontend image attach UI** | — | **A2 today** |
| **Frontend mic toggle UI** | — | **A3 today** |

---

## 🔬 2. RESEARCH SYNTHESIS — 4 GAME-CHANGERS

| Finding | Source | Impact |
|---------|--------|--------|
| **CompressorJS via CDN** (12KB gzipped, single script) — bukan pica/OffscreenCanvas (Safari iOS issues) | github.com/fengyuanchen/compressorjs Jan 2025 | No build, EXIF-aware, Canvas-based |
| **Max 4 images** per message (Anthropic Claude.ai pattern; ChatGPT 10 = UX bloat) | Anthropic Vision docs Feb 2026 | Lock UI to 4 |
| **Max 1568px** (Anthropic Vision optimal — saves token cost too) | Anthropic Vision docs Feb 2026 | downscale before send |
| **Scribe v2 > WhisperWASM** for Indonesian (WER 8% vs 22%, 40MB cold-load avoided) | latenode benchmark + Scribe v2 docs Apr 2026 | Confirmed earlier research |
| **Mic permission on first CLICK** (not on-mount, Safari iOS denies) | Chrome devrel Mar 2025 | UX rule |
| **NO fake waveform** (trust loss per NN/g) | nngroup.com/articles/voice-input-ui Jan 2026 | Just dot pulsing + timer |
| **Modality-as-tool routing** = ALIGNS with ADO modular brain | Anthropic Claude Skills Mar 2026 | Vision validation |

### Surprise findings (defer but log)
- **Qwen3-MoE-A3B** (Apr 2026): 30B total / 3B active. Fits VPS, faster than dense 7B → **Cycle 3+ upgrade candidate** (Phase 5)
- **llama.cpp speculative decoding stable** with `--draft-model qwen3-0.5b` → 1.8x throughput → **post-Cycle-1 hot-swap candidate** (Day 41+)
- **Flower v1.10 federated learning** production-ready in healthcare → Phase 6

---

## 📐 3. DAY 40 ITERATION TASK LIST — H/R/B FRAMEWORK

### A3 — Mic toggle UX ⭐ FIRST (smallest LOC, validates STT roundtrip)

**Hipotesis:** User klik mic icon → request permission → record max 90s → release click → blob upload to `/v1/speech/to-text` → text inserted ke input field. Indonesian transcription accurate (Scribe v2 WER ≤5%).

**Adaptasi gagal:** Hide mic button if `getUserMedia` permission denied OR if STT endpoint returns 401 (key scope issue).

**Impact:** Voice-first beta cohort ready. Differentiator vs typed-only competitors. Especially Indonesian users (Scribe 3x more accurate than Whisper-v3).

**Benefit:** "AI yang ngerti gue" narrative — voice is most intimate input modality.

**Risk:**
- LOW — backend ready, key permission enabled, MediaRecorder API mature
- MEDIUM — Safari iOS getUserMedia quirks (mitigated: trigger on click only, fallback gracefully)

**Effort:** ~2 jam (mic button + MediaRecorder + permission + visual indicator + upload + insert text)

**Senses analogy:** This is wiring the **auditory cortex** to the brain.

---

### A2 — Image attach UX (paste + drop + picker → analyze_image)

**Hipotesis:** User attach image (3 ways: paste from clipboard / drag-drop onto chat / file picker) → thumbnail preview ABOVE input → klik send → image base64 attached to message → backend triggers analyze_image tool → AI describes/answers about image.

**Adaptasi gagal:** Skip thumbnails, fallback to "describe this image: <url>" pattern via tool args. UI degraded but functional.

**Impact:** Multimodal beta-readiness — MAIN Bulan 2 Week 6 blocker. Beta testers can share screenshots, photos, diagrams.

**Benefit:** Differentiator vs typed-only. Visual share = most common social pattern.

**Risk:**
- MEDIUM — base64 in React state can freeze typing if >2MB → MUST downscale via CompressorJS BEFORE store
- LOW — fallback paste-as-text if image upload fails

**Effort:** ~3 jam (CompressorJS CDN + paste/drop/picker handlers + thumbnail strip + downscale + integrate to send + analyze_image trigger)

**Senses analogy:** This is wiring the **visual cortex** to the brain.

---

### A4 — Status hierarchy extension (Day 36 → seeing/hearing)

**Hipotesis:** Extend Day 36 3-state status (Connecting/Thinking/Generating) dengan `Seeing image...` (saat analyze_image triggered) + `Listening...` (saat mic recording).

**Adaptasi gagal:** Skip — status hierarchy sudah cukup informative tanpa modality-specific.

**Impact:** Trust + transparency — user paham AI sedang process apa.

**Benefit:** ADO "self-aware" feel — brain announces which sense is active.

**Risk:** LOW — additive UI only.

**Effort:** ~30 menit (extend Msg component status logic)

---

### DEFER Day 41+
- A2.6 Episodic image memory (store hash + caption to Qdrant)
- LangFuse self-hosted observability
- Frontend re-design polish

---

### Autonomous (background)
- Synthetic gen running, DPO 360 → trigger SimPO when ≥500 (autonomous)
- Magpie 300K full overnight (just remove `MAGPIE_QUICK=1` env, autonomous)
- Smithery server LIVE PUBLIC at smithery.ai/server/fahmiwol/migancore (Day 40 AM done)

---

## 📊 4. KPI PER ITEM

| Item | Target | Verifikasi |
|------|--------|------------|
| A3 mic toggle | record 5s "halo" → text appears in input | manual incognito test |
| A2 image attach | drag-drop 1 image → thumbnail visible → send → AI describes | manual test all 3 paths (paste, drop, picker) |
| A4 status seeing/hearing | bubble shows "Seeing image..." or "Listening..." | manual visual check |
| **v0.5.8 deployed** | health 200 + new chat UI | curl /health + incognito test |
| **chat.html size** | <100 KB total | wc -c |

### Gate
- IF DPO ≥500 by Day 40 EOD → auto-trigger SimPO Cycle 1 (Track A)
- IF Magpie 300K cache complete → ENV switch SEED_SOURCE=magpie_300k

---

## 💰 5. BUDGET PROJECTION

| Item | Estimate |
|------|----------|
| A2/A3 frontend dev | $0 |
| analyze_image E2E test (10 imgs) | $0.001 |
| Scribe E2E test (5 audio) | $0.05 |
| Synthetic continued | $0.30 |
| Buffer | $0.05 |
| **Day 40 PM total** | **~$0.40** |

Cumulative Bulan 2: $0.79 + $0.40 = **$1.19 of $30 cap (4%)**.

If SimPO Cycle 1 triggers EOD: +$2.80 → **$3.99 of $30 (13%)**.

---

## 🚦 6. EXIT CRITERIA — Day 40 Iteration

Must-have:
- [ ] Mic toggle button visible, functional, transcript inserted to input
- [ ] Image attach (paste + drop + picker) functional, thumbnails visible, send works
- [ ] Image send triggers analyze_image tool (visible in tool chips)
- [ ] Status hierarchy extended (seeing/hearing states render)
- [ ] v0.5.8 deployed + healthcheck pass
- [ ] CompressorJS CDN loaded successfully
- [ ] `docs/DAY40_ITERATION_PROGRESS.md` + memory committed

Stretch:
- [ ] DPO ≥500 → SimPO Cycle 1 trigger auto
- [ ] Magpie 300K full cache loaded
- [ ] Smithery quality polish (homepage = migancore.com, README, badge link)

---

## 🛡️ 7. SCOPE BOUNDARIES (re-affirmed)

❌ **DON'T BUILD Day 40 PM:**
- WhisperWASM (40MB cold-load, slower than Scribe — confirmed research)
- Realtime mic streaming WebSocket (batch fine, defer Day 41+)
- Multi-image upload service (base64 inline ≤4 images cukup)
- Image editing/cropping in browser (just upload + describe)
- pica image library (CompressorJS lebih ringan via CDN)
- Image to base64 storage in DB (use Qdrant episodic later, defer)
- LangFuse (post-Cycle-1)
- Smithery deeper inspection (Day 41 polish)

✅ **STAY FOCUSED:**
- Wire 2 SENSES (vision + audio) ke chat UI
- Modality-as-tool routing (ADO alignment)
- ≤100 KB chat.html total

---

## 🎓 8. LESSONS APPLIED (cumulative 22 → 24+)

23. (Day 40 from earlier research): Don't reinvent paid services with WASM until offline-mode use case
24. **(NEW Day 40 PM):** Modality-as-tool routing pattern (Anthropic Claude Skills Mar 2026) is the canonical multimodal approach for modular brain architectures — DON'T bake modalities into the LLM, route via tools so brain stays text-pure and portable.

---

## 🔭 POST-DAY-40 LOOKAHEAD (re-anchored)

**Day 41:**
- LangFuse observability deploy (1GB RAM, Postgres-only)
- Hot-swap v0.1 if Cycle 1 PROMOTE
- Smithery quality polish (homepage migancore.com, README, badge)
- Admin Dashboard fix (proper /admin routing + API Keys UI)

**Day 42:**
- 24h A/B win-rate
- PROMOTE/ROLLBACK decision
- Week 5 Retro

**Day 43-49 (Week 6):** Beta launch — 5 invited users, full multimodal UI, post-Cycle-1 model

---

**THIS IS THE COMPASS for Day 40 ITERATION (PM). 3 must-have UI items, ~6 jam, ~$0.40. Wires 2 SENSES to ADO brain.**
