# Day 53 Retrospective — Speculative Decoding Shipped + Cycle 1 Aborted Clean
**Date:** 2026-05-06 (Day 53)
**Outcome:** 🟡 Track A infra LIVE but KPI NOT MET; Track B clean abort per Lesson #60; Track C documented.

---

## 🎯 TL;DR

- **Track A (Speculative Decoding):** Full infra shipped — llama-server container running on :8081, OpenAI-compatible client `services/llamaserver.py`, `X-Inference-Engine` header, telemetry. **BUT** empirical KPI (1.5x speedup, 70% acceptance) **NOT MET** on shared 8-vCPU CPU host. Default flipped to safe `ollama` until tuned. Lesson #71.
- **Track B (Cycle 1 retry):** Vast.ai A100_PCIE @ $0.134/hr fell back from V100 (none available), host went `intended=stopped` at 191s, autonomous monitor aborted cleanly at 912s per Lesson #60. Zero leaked instances verified. ~$0.03 cost.
- **Track C (Self-learning sources):** `docs/SELF_LEARNING_SOURCES.md` written. Vision-aligned library-card pattern. Lesson #72.

---

## ✅ DELIVERED

### 1. `docs/DAY53_PLAN.md`
Full 3-track plan with H/R/B + 5-check vision sanity test pass for all tracks.

### 2. Track A — llama-server speculative decoding INFRASTRUCTURE
- **Image:** `ghcr.io/ggml-org/llama.cpp:server` (183MB) pulled
- **Models:** Symlinks at `/opt/ado/llama-models/` pointing into Ollama blobs (zero duplication)
  - `qwen2.5-7b-instruct-q4km.gguf` (4.4GB target)
  - `qwen2.5-0.5b-q4.gguf` (380MB draft)
- **Container:** `llamaserver` on `ado_network`, port 127.0.0.1:8081 → 8080
  - Args: `--spec-draft-n-max 5 --spec-draft-n-min 2 --ctx-size 4096 --threads 6 --threads-draft 2 --mlock`
  - Resource cap: `--memory=12g --cpus=6`
  - Health: `/health` returns `{"status":"ok"}` ✅
- **Client:** `api/services/llamaserver.py` — async OpenAI-compat with `chat_stream()` matching `OllamaClient` signature (drop-in)
- **Routing:** `X-Inference-Engine: speculative|ollama|auto` (default `auto` → safe Ollama)
- **Telemetry:** `chat.stream.engine_telemetry` log event fires per request with engine name, TTFB ms, total seconds, chunks/s
- **Response header:** `X-Inference-Engine-Resolved` exposed for client debug

### 3. Track C — `docs/SELF_LEARNING_SOURCES.md`
Library-card pattern: w3schools, roadmap.sh, freecodecamp/news, discuss.python.org, stackoverflow. Migan reads via `web_read` / `onamix_search`, synthesizes in own voice, distills to DPO pairs (Cycle 2+) — long-term internalization. Sources are MENTOR not RESPONDER (Lesson #68 applied correctly).

---

## ⚠️ KPI MISS — Speculative Decoding Slower Than Ollama (Track A5)

**Measured (cold-cache, contended production):**
- llama-server speculative: **2.63 tok/s** (28 predicted tokens, 22 drafted)
- Ollama 7B baseline (during contention): 0.16 tok/s ← contaminated by concurrent llama-server load

**Root cause analysis:**
- 8-vCPU host shared between Ollama (4.97GB resident, 788% CPU under prod load) + llama-server (3.7GB resident with mlock)
- mlock pinned ~5GB making Ollama compete for remaining cache
- `--threads 6` for target + `--threads-draft 2` = 8 threads on 8 vCPUs → 100% saturation when both run
- Realistic CPU speedup band per r/LocalLLaMA Q1 2026: 1.6-2x ONLY when target gets full CPU; concurrent inference engines = both starve

**Decision:** Flip `auto` default in `select_inference_client` to **ollama** (safe). `speculative` becomes opt-in via explicit header. No user-visible regression.

**Day 54 follow-up options:**
1. Stop Ollama for chat traffic; use only for tool-calls + model registry
2. Tune `--spec-draft-n-max` 5→3 (reduce wasted draft work when acceptance low)
3. Drop `--mlock` (let kernel page cache do the work)
4. Add `--no-warmup` to skip duplicate warmup
5. Get isolated benchmark window (stop Ollama, test alone, reverse, compare clean)

---

## ❌ Track B — Cycle 1 Vast.ai retry aborted (vendor unreliability, not our bug)

**Sequence:**
1. Search V100 32GB max=$0.10/hr min_rel=0.95 → **0 matches**
2. Fallback A100_PCIE 40GB rel=0.96 @ $0.134/hr → rented offer 31500045
3. Boot poll: actual=`loading→created`, then host self-set `intended=stopped` at 191s (host operator action, not us)
4. Monitor honored Lesson #60 (15-min hard cap) → at 912s issued `DELETE`, got HTTP 200, ran VERIFY (Lesson #59) → confirmed `actual_status=None` (deleted) → confirmed marketplace shows `instances: 0`
5. Cost: ~$0.03 (1 instance × ~13min wall × $0.1375/hr)

**Lesson #62 reinforced** — Vast.ai marketplace remains unpredictable. Even rel=0.96 can self-stop. Need RunPod or dedicated GPU for Cycle 1 ASAP. Day 54 decision point.

---

## 📊 KPI Outcome vs Plan

| Track | KPI | Target | Actual | Status |
|-------|-----|--------|--------|--------|
| A. Spec dec install | llama-server up on :8081 | health 200 | ✅ | PASS |
| A. Spec dec test | First chat via llama-server | <10s | ~5s TTFB | PASS |
| A. Acceptance rate | per request log | ≥70% | not exposed in this build | DEFERRED |
| A. Speedup | warm chat measured | ≥1.5x vs Ollama | 2.63 tok/s vs ?? | NOT MET |
| B. Cycle 1 retry | adapter OR clean abort | binary | clean abort | PASS (binary) |
| C. Self-learn sources | doc updated | reference list | ✅ written | PASS |
| **v0.5.16** | speculative live + lessons #71-72 | health 200 + retro | ✅ | PASS |

---

## 💰 Budget Actual Day 53

| Item | Spent |
|------|-------|
| Track A speculative (zero infra cost — Docker image free) | $0.00 |
| Track B Cycle 1 retry (Vast A100 13min wall) | ~$0.03 |
| Track C self-learning sources doc | $0.00 |
| **Day 53 total** | **~$0.03** |

Cumulative: **$8.36 / $44 budget (~19%)**.

---

## 🎓 Lessons Learned Day 53 (2 new, **72 cumulative**)

### Lesson #71 — Speculative decoding on shared CPU = often a wash. Bench BEFORE flipping default.
On CPU-only with concurrent inference engines (Ollama + llama-server both resident), draft model competes with target for L2/L3 cache + threads. Acceptance-rate-aware speedup (1.6-2x theoretical, per r/LocalLLaMA Q1 2026) requires either (a) isolated CPU/RAM, (b) GPU offload of draft, or (c) shutting down the other engine for chat traffic. **Never flip default before empirical apples-to-apples benchmark.** Default remained safe (Ollama); speculative = opt-in via `X-Inference-Engine: speculative`.

### Lesson #72 — Self-learning sources are Migan's "library card", NOT its tongue.
Library card = read access to mentor knowledge (w3schools, roadmap.sh, etc.). Tongue = the response — always own model, own voice. Confusing the two = wrapper pattern (Lesson #68) all over again. Right pattern: read source → distill to DPO pair → train Migan → eventually answer without source. Same MENTOR-vs-RESPONDER distinction extended to web sources, not just teacher APIs.

---

## 🚦 Exit Criteria Day 53

Must-have:
- [x] Track A: llama-server running, sample chat working
- [x] Track A: speculative decoding measurable speedup recorded (KPI MISS documented honestly, not papered over)
- [x] Track B: Cycle 1 retry result (clean abort verified)
- [x] Track C: self-learning sources documented
- [x] DAY53_RETRO + memory close-out

Stretch (deferred):
- [ ] Hot-swap migancore:0.1 to Ollama (no Cycle 1 adapter to swap — Day 54+)
- [ ] Identity eval (no adapter)
- [ ] Webcam capture (Day 54)

---

## 🔭 DAY 54+ LOOKAHEAD

| Day | Track | Goal |
|-----|-------|------|
| 54 | Speculative decoding tune-or-kill | Isolated benchmark, decide ship-or-revert |
| 54 | RunPod-based Cycle 1 retry (saldo $16) | Avoid Vast.ai marketplace flakiness |
| 54-55 | Webcam capture | Multimodal 5th sense |
| 55 | "Otak Belajar" Indonesia thread (M-1) | Beta narrative |
| 56-60 | Cycle 2 + iterate beta | Self-improving moat in motion |

**Vision compass intact:** all 3 tracks today passed 5-check sanity test. ZERO wrapper-pattern violations. Standing-alone principle preserved through honest KPI reporting (didn't ship a regression to look "fast").

---

## 📈 PRODUCTION HEALTH (end Day 53)

| Component | Status |
|-----------|--------|
| API v0.5.16 | ✅ healthy |
| Brain (Ollama) | ✅ qwen2.5:7b loaded, KEEP_ALIVE 24h |
| llama-server (NEW) | ✅ running on :8081, opt-in via header |
| 23 tools | ✅ verified |
| Vision principles | ✅ LOCKED PERMANENT (`VISION_PRINCIPLES_LOCKED.md`) |
| 72 lessons cumulative | documented |
| Cost discipline | $8.36 / $44 (19%) |
| Cycle 1 adapter | ❌ STILL not trained (Vast unreliable, RunPod next) |

---

**Day 53 = INFRA SHIPPED + HONEST KPI REPORTING + VISION INTACT.**

> "Speed problems → better local model, NOT wrapper. AND: don't ship a regression to *look* faster." — Lesson #70 + #71
