# Day 52 Retrospective — Vision Locked + Speculative Decoding Researched
**Date:** 2026-05-06
**Outcome:** 🟢 Vision principles PERMANENT documented. Speculative decoding researched. Day 53 implementation plan ready.

---

## ⚠️ CRITICAL VISION CLARIFICATION (from user feedback)

User caught my Day 52 strategic drift IMMEDIATELY:

**Saya hampir usulkan:** "Hybrid Brain — pakai Kimi K2 sebagai LIVE chat responder"
**User koreksi tegas:** *"Guru API itu gunanya untuk membantu migancore BELAJAR, bukan untuk jadi PENJAWAB, tapi buat synthetic conversation MENGAJARKAN migancore."*

Plus: *"Gemini vision bukannya udah diganti? Kita kan harus standing alone, and built our own tools. Inget kan?"*

### Vision principles LOCKED PERMANENT (`docs/VISION_PRINCIPLES_LOCKED.md`)

5 principles wajib dipatuhi setiap proposal:
1. **Migan = STANDING ALONE BRAIN** — jawab sendiri, own model + own tools
2. **Teacher API = MENTOR (not responder)** — synthetic data, CAI critique, DPO pairs only
3. **OWN TOOLS default** — third-party only as teacher OR last-resort fallback
4. **Self-improving via closed loop** — chat → log → teacher generates "what better would have been" OFFLINE → DPO pair → SimPO trains Migan
5. **Speed problems → better local model, NOT wrapper** — speculative decoding, distill smaller, better quantization

**5-check sanity test before any new feature:**
1. Vision check (standing alone vs wrapper?)
2. Mentor check (teacher = MENTOR or RESPONDER?)
3. Standing alone check (long-term own model possible?)
4. Closed loop check (feeds DPO data?)
5. Modular check (other AI agents can adopt?)

---

## ✅ DELIVERED Day 52

### 1. `docs/VISION_PRINCIPLES_LOCKED.md` (NEW PERMANENT)
- 5 principles with examples right vs wrong
- 5-check sanity test
- Decision log table (Day 52 entries: REJECT Hybrid Brain, ACCEPT speculative decoding, CONTINUE Cycle 1 strategy)

### 2. `docs/AGENT_ONBOARDING.md` updated
- 4 priority docs → 5 (added VISION_PRINCIPLES_LOCKED)
- Lessons #68 #69 #70 added (Teacher=Mentor, Standing alone, Speed→better local NOT wrapper)

### 3. Speculative decoding fully researched
**Critical finding:** Ollama 0.22.1 + 0.23.1 BOTH do NOT support speculative decoding natively (PR #8134 closed unmerged April 2025, issue #5800 still open April 2026 after 63 comments).

**Solution:** bypass Ollama for inference, use `llama-server` (C++ binary from llama.cpp) directly. Keep Ollama for model lifecycle.

**Realistic CPU speedup:** 1.6-2.0x (not 2-3x as I initially claimed). 7-22 tok/s → 12-35 tok/s = "feels like Claude" threshold per r/LocalLLaMA Q1 2026 benchmarks.

**Concrete config (ready to deploy Day 53):**
```bash
./llama-server \
  --model /path/qwen2.5-7b-instruct-q4_k_m.gguf \
  --model-draft /path/qwen2.5-0.5b-instruct-q4_0.gguf \
  --draft-max 5 --draft-min 2 \
  --ctx-size 4096 \
  --threads 6 --threads-draft 2 \
  --port 8081 --mlock
```

**Pitfalls documented:**
- Acceptance <60% → SLOWER (creative prompts tank acceptance) → only route low-temp tasks
- KV cache RAM cost ~5.5-6GB (fits in 32GB)
- Cold start NOT helped (60-90s tool spec build remains issue — Day 45 conv_summarizer addresses)
- SSE jitter from accept/reject mid-token → buffer one extra token

**Vision compass aligned:** 100% local, no telemetry, no phone-home.

### 4. Earlier today (still relevant)
- Track B context contamination fix shipped (commit 1cb4537) — NEW CHAT button glow after 2 errors

---

## ❌ NOT DELIVERED (deferred Day 53 with clear plan)

### Speculative decoding implementation
**Reason:** Requires installing llama.cpp on VPS + creating systemd service or Docker container + adapter chat.py to route to OpenAI-compatible endpoint. ~6 hours work, NOT a 1-hour win. Need clean implementation Day 53.

### Cycle 1 retry (vastai/base-image)
**Reason:** Same — needs dedicated session focus, not parallel.

### Webcam capture (Day 53-54)
**Reason:** Roadmap target Day 53 afternoon.

---

## 📋 DAY 53 EXECUTION PLAN (locked-in roadmap)

### Track A — Speculative decoding via llama-server (HIGH, ~6 hr)
1. Install llama.cpp via Docker container alongside Ollama (`ghcr.io/ggerganov/llama.cpp:server`)
2. Mount Ollama model blobs as read-only into llama-server container
3. Configure with Qwen2.5-7B-Instruct (target) + Qwen2.5-0.5B (draft)
4. Add OpenAI-compatible client in `services/llamaserver.py`
5. Add feature flag header `X-Inference-Engine: speculative|ollama`
6. Default `auto`: speculative for tool-calls/structured, ollama for creative
7. Telemetry: log acceptance rate per request
8. KPI: acceptance ≥70%, sustained 1.5x speedup, ZERO quality regression

### Track B — Webcam capture (MED, ~4 hr)
1. Add `<button>` 📷 Webcam in chat input bar
2. `navigator.mediaDevices.getUserMedia({video: true})` request permission
3. Modal overlay with video preview + "Capture" button
4. Canvas snapshot → base64 PNG → send to existing `/v1/vision/describe` endpoint
5. analyze_image (Gemini Vision as TEACHER for vision data Day 60+ replace)
6. Result inserted as user message attachment

### Track C — Cycle 1 retry (MED, parallel ~1 hr)
- Vast.ai with `vastai/base-image:cuda-12.1.1-auto` (cloud's native, fastest boot)
- Apply Lessons #59 #60 #61 (5-min abort, DELETE+VERIFY, cost telemetry)
- Budget cap $0.30 max
- If success → first MiganCore-branded adapter v0.1

---

## 🎓 LESSONS LEARNED Day 52 (3 new, **70 cumulative**)

68. **Teacher API = MENTOR, NEVER live RESPONDER.** External APIs generate training data, generate critiques, label vision — semua OFFLINE/ASYNC. Migan respond ke user pakai own brain. Wrapper pattern = defeats moat.

69. **Standing alone principle — own tools default.** ONAMIX is the model: take user-owned (HYPERX) → made own MCP. Don't add new third-party SDK as DEFAULT. Acceptable trade-offs: Gemini Vision as TEACHER (distill local Day 60+), fal.ai image gen (large diffusion impractical local).

70. **Speed problems → better local model, NOT wrapper.** When CPU 7B too slow: speculative decoding (Qwen 0.5B+7B all local 1.6-2x), distill smaller (7B→3B), better quantization (Q5_K_M), dedicated GPU, Cycle N+ better Qwen. NEVER live teacher API.

---

## 💰 BUDGET ACTUAL Day 52

| Item | Spent |
|------|-------|
| Vision principles documentation | $0 |
| Research speculative decoding | $0 |
| Track B context fix (frontend) | $0 |
| **Day 52 total** | **$0.00** |

Cumulative: **$8.33 / $44 budget (~16%)**.

---

## 🚦 EXIT CRITERIA — Day 52 Status

Must-have:
- [x] Vision clarification documented PERMANENT
- [x] Lessons #68-70 added to onboarding
- [x] DAY52_RETRO.md (this file)
- [x] Memory close-out
- [x] Track B context fix deployed (earlier commit)

Stretch (deferred Day 53):
- [ ] Speculative decoding implementation
- [ ] Webcam capture
- [ ] Cycle 1 retry

---

## 🔭 DAY 53+ LOOKAHEAD

| Day | Track | Goal |
|-----|-------|------|
| **53** | **A. Speculative decoding via llama-server** | Chat 1.6-2x faster, ALL LOCAL, vision-aligned |
| 53 | B. Webcam capture | Multimodal "5th sense" |
| 53 | C. Cycle 1 retry | Validate self-improving moat |
| 54 | Beta iterate top 3 issues | First feedback responsive |
| 55 | "Otak Belajar Apa Minggu Ini" thread M-1 | Indonesia narrative tactic |
| 56-60 | Cycle 2 SimPO with hybrid distill data | Teacher MENTOR pattern (correct usage) |
| 61-62 | Distill 7B → 3B own model | Standing alone smaller faster |
| 63-65 | Open beta + Dream Cycle | Vision Innovation #4 |

---

## 📈 PRODUCTION HEALTH (end Day 52)

| Component | Status |
|-----------|--------|
| API v0.5.16 | ✅ healthy |
| Brain | ✅ working (Track B context fix prevents contamination) |
| 21 tools | ✅ verified |
| Beta package | ✅ launched Day 51 |
| Vision principles | ✅ LOCKED PERMANENT (`VISION_PRINCIPLES_LOCKED.md`) |
| 70 lessons cumulative | documented |
| Cost discipline | $8.33 / $44 (16%) |

---

**Day 52 = VISION PROTECTED + STRATEGY UNFUCKED + Day 53 PLAN ROCK SOLID.**

> "Speed problems don't justify breaking vision. Better local model wins long-term." — Lesson #70
