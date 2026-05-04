# Day 40 Plan — Frontend Multimodal UI + SimPO Cycle 1 Trigger
**Date:** 2026-05-04 (Day 40, Bulan 2 Week 5 Day 5)
**Drafted by:** Claude Sonnet 4.6 — full mandatory protocol
**Triggered by:** User: "OK!" (confirm Day 39 close + Day 40 lookahead)
**Research:** parallel agent `af9a26669` (4 areas: image attach, mic, SSE tool chips, WASM Whisper)

---

## 🧭 1. CONTEXT INHERITED

| Item | Value Day 40 morning |
|------|----------------------|
| API | v0.5.6 healthy (stream tool exec live, chat continuity fixed) |
| DPO pool | **352** (was 332 EOD Day 39 = +20 overnight) |
| Synthetic gen | running, ETA ≥500 = 7-10 hr from now (today afternoon) |
| RunPod saldo | $16.17 (Cycle 1 will spend ~$2.80) |
| Bulan 2 spend | $0.79 of $30 (2.6%) |
| Backend ready | analyze_image (Gemini Vision), POST /v1/speech/to-text (Scribe), SSE events tool_start/tool_result |
| ElevenLabs key | speech_to_text permission ENABLED ✅ (Fahmi confirmed) |
| Smithery | smithery.yaml ready, tutorial provided to Fahmi |

---

## 🔬 2. RESEARCH SYNTHESIS — 4 GAME-CHANGERS

| Finding | Source | Impact |
|---------|--------|--------|
| **Tool chips INSIDE assistant bubble**, collapsed once tool_result arrives | Vercel AI SDK useChat spec Apr 2026 + Cursor Composer reverse-eng Jan 2026 | Render pattern locked |
| **Toggle button beats push-to-talk** for mic on web (PTT breaks mobile keydown) | web.dev "Recording audio in 2025" + Anthropic Claude.ai mic Dec 2025 | Single click to start/stop |
| **Base64 inline <1MB**, paste handler on textarea = table stakes | Vercel AI Chatbot Mar 2026 + ChatGPT teardown Feb 2026 | Skip upload service for Day 40 |
| **SKIP Whisper.cpp WASM** for now | ggerganov/whisper.cpp v1.7.4 + xenova/transformers.js v3 | 40MB+ overhead, slower than Scribe (800ms RT) |

### 3 Common Pitfalls (from research)
1. `getUserMedia` di page load → Safari iOS langsung deny → request hanya on user gesture
2. Re-render tool chips per SSE token → keyed by tool_call_id + memoize
3. Base64 >2MB string di React state freezes input typing → downscale ke 1568px max-edge via OffscreenCanvas sebelum store

---

## 📐 3. DAY 40 TASK LIST — H/R/B FRAMEWORK

### TRACK A — Frontend Multimodal UI (must-ship Day 40)

#### A1 — SSE tool chips dalam assistant bubble ⭐ HIGHEST PRIORITY
**Hipotesis:** Render tool execution visible dalam UI → user paham AI sedang "berpikir" + apa tool yang dipakai → trust meningkat. Pattern: `parts[]` array di msg dengan type='tool'|'text'.
**Adaptasi gagal:** Fall back ke text-only (current). User masih bisa chat, sekedar kurang transparan.
**Impact:** Beta UX critical — backend sudah ship events Day 39, frontend belum render → events terbuang.
**Benefit:** Tool execution transparent → user trust + debugging easier.
**Risk:**
- LOW — frontend-only, no backend change
- MEDIUM — re-render performance (mitigated by memoize per tool_call_id)

**Effort:** ~2 jam (parts[] state model + ToolChip component + handle tool_start/tool_result events)

#### A2 — Image attach (paste + drop + picker) → analyze_image
**Hipotesis:** User attach image (paste from clipboard, drag-drop, atau picker) → thumbnail preview → klik send → AI deskripsi/answer. Pattern: thumbnails strip above input, max 4 images, base64 inline ≤1MB, downscale ke 1568px.
**Adaptasi gagal:** UI masih text-only, user pakai analyze_image via tool args manual (impractical).
**Impact:** Multimodal beta-ready → Bulan 2 Week 6 launch unblocked.
**Benefit:** Differentiator vs typed-only competitors. Beta testers bisa share screenshot/photos.
**Risk:**
- MEDIUM — image base64 di React state bisa freeze typing kalau >2MB → MUST downscale before store
- LOW — fallback to typing description manually

**Effort:** ~3 jam (paste handler + drop handler + picker + thumbnail strip + downscale via canvas + integrate to chat send)

#### A3 — Mic toggle → POST /v1/speech/to-text
**Hipotesis:** Click mic button → request permission once → start recording → click again to stop → upload to Scribe → text appended ke input field. Visual: pulsing red dot + animated bars (CSS-only).
**Adaptasi gagal:** Hide mic button kalau permission denied. User pakai keyboard.
**Impact:** Voice-first beta cohort ready. Differentiator (especially Indonesian users).
**Benefit:** Touchpoint untuk "AI yang ngerti gue" narrative.
**Risk:**
- LOW — backend Scribe endpoint ready (Day 38), key permission enabled
- MEDIUM — Safari iOS getUserMedia quirks (mitigated by user-gesture trigger only)

**Effort:** ~2 jam (mic button + MediaRecorder + permission + visual indicator + upload + insert text)

---

### TRACK B — Cycle 1 Trigger (autonomous, gated DPO ≥500)

#### B1 — SimPO Cycle 1 trigger
**Trigger condition:** DPO pool ≥500 (currently 352, ETA ~7-10 hr)
**Process:**
1. Pause synthetic + distillation (free Ollama for inference during eval)
2. Export DPO dataset to JSONL (50/30/20 mix per blueprint)
3. Pull RTX 4090 on-demand pod ($0.74/hr — NOT spot, anti-reclaim)
4. Upload dataset + run `train_simpo.py --use-apo --anchor-dataset eval/persona_consistency_v1.jsonl`
5. Monitor: reward margin (kill if <0.5 step 50), KL div (kill if >5.0)
6. Convert adapter → GGUF Q4_K_M
7. Identity eval v0.1 vs `baseline_day39.json` → cosine sim per category
8. **GATE ≥0.85 cosine** average → PROMOTE; else ROLLBACK + document failure mode

**Hipotesis:** Hyperparameters Day 39 (epochs 1, lr 8e-7, gamma 1.0, apo_λ 0.05) + 50 identity anchors → win_rate ≥55% vs base, identity ≥0.85.
**Risk:** RunPod spot interruption ($2.80 hangus) → use on-demand. Identity drift → APO loss caps.
**Cost:** $2.80 (4hr RTX 4090 with flash-attn 2.7+).
**Effort:** ~30min setup + 4hr compute (autonomous) + 30min eval.

---

### TRACK C — Distribution + Magpie

#### C1 — Smithery PR (Fahmi action)
- File `smithery.yaml` ready di repo root
- Tutorial step-by-step provided
- Publish via UI atau PR ke smithery-ai/registry
- ETA: ~10 menit Fahmi action + auto-validate

#### C2 — Magpie 300K full overnight
- Remove `MAGPIE_QUICK=1` from container env
- Re-run loader → downloads remaining 4 shards (~580MB total)
- Cache to `/app/.cache/magpie_300k_instructions.json` (~75MB JSON)
- After cache: switch `SEED_SOURCE=magpie_300k`
**Effort:** ~5 menit kick-off, ~1-2 hr download autonomous.

---

### DEFER Day 41+
- LangFuse self-hosted observability (post-Cycle-1, BEFORE hot-swap A/B)
- Whisper.cpp WASM (40MB overhead — Scribe better)
- Conversation export MD/JSON (Bulan 2 Week 6 polish)
- Smithery PR confirmation

---

## 📊 4. KPI PER ITEM

| Item | Target | Verifikasi |
|------|--------|------------|
| A1 tool chips | tool_start + tool_result render in bubble | Manual: trigger memory_write via stream, see chip |
| A2 image attach | thumbnail visible, send → analyze_image returns description | Manual: paste image, send "describe ini" |
| A3 mic toggle | record → upload → text inserted | Manual: hold record 5s "halo", text appears |
| B1 SimPO Cycle 1 | adapter saved + identity ≥0.85 OR documented failure | RunPod logs + eval/v0.1.json |
| C1 Smithery | PR open or listing live | smithery.ai/server/migancore |
| C2 Magpie 300K | full cache 280K+ instructions | docker exec ... ls -la /app/.cache/magpie_300k_instructions.json |
| **DPO EOD** | ≥500 OR Cycle 1 in-progress | /v1/public/stats |
| **v0.5.7** | health + new chat UI | curl /health + incognito test |

---

## 💰 5. BUDGET PROJECTION Day 40

| Item | Estimate |
|------|----------|
| Frontend dev (no API) | $0 |
| analyze_image E2E test (10 imgs) | $0.001 |
| Scribe E2E test (5 audio) | $0.05 |
| SimPO Cycle 1 RunPod | $2.80 |
| Synthetic continued | $0.20 |
| Buffer | $0.10 |
| **Day 40 total** | **~$3.20** |

Cumulative Bulan 2: $0.79 + $3.20 = **$3.99 of $30 cap (13%)**.

---

## 🚦 6. EXIT CRITERIA — Day 40

Must-have:
- [ ] Tool chips render dalam stream chat assistant bubble
- [ ] Image attach (paste/drop/picker) functional + thumbnail visible
- [ ] Mic toggle functional + transcript inserted
- [ ] v0.5.7 deployed + healthcheck pass
- [ ] DPO pool ≥500 OR SimPO Cycle 1 triggered
- [ ] `docs/DAY40_PROGRESS.md` + memory committed

Stretch:
- [ ] SimPO Cycle 1 complete + identity eval ≥0.85 → PROMOTE v0.1
- [ ] Smithery listing live (Fahmi action)
- [ ] Magpie 300K full cache loaded

---

## 🛡️ 7. SCOPE BOUNDARIES (re-affirmed)

❌ **DON'T BUILD Day 40:**
- Whisper.cpp WASM (40MB overhead, slower than Scribe)
- Realtime mic streaming WebSocket (Scribe batch fine for MVP)
- Multi-image batch send (max 4 inline, ship single first)
- LangFuse observability (Day 41 post-Cycle-1)
- Conversation export (Bulan 2 Week 6)
- New tools

✅ **STAY FOCUSED:**
- Multimodal UI shipped to chat.html
- Cycle 1 Trigger when DPO ≥500
- Magpie full cache pre-loaded for Cycle 2

---

## 🎓 8. LESSONS APPLIED (cumulative 22 → 23+)

23. (Day 40, derived from research): Don't reinvent paid services with WASM until you have offline-mode use case. Whisper.cpp WASM = 40MB + slower than already-paid ElevenLabs Scribe.

---

## 🔭 POST-DAY-40 LOOKAHEAD

**Day 41:**
- LangFuse self-hosted setup (Postgres-only, 1GB RAM, free OSS)
- Hot-swap v0.1 to Ollama (if Cycle 1 PROMOTE)
- A/B framework: 10% traffic to v0.1 via X-Model-Version header

**Day 42:**
- 24h A/B win-rate metrics (LangFuse)
- PROMOTE / ROLLBACK decision
- Week 5 Retro committed

**Day 43-49 (Week 6):** Beta launch — 5 invited users with multimodal UI, post-Cycle-1 model

---

**THIS IS THE COMPASS for Day 40. 3 must-have UI items + 1 autonomous training trigger. ~7hr work + ~$3.20.**
