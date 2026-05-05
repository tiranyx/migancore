# Day 53 Plan — Speculative Decoding + Cycle 1 Retry + Vision Aligned
**Date:** 2026-05-06 (Day 53)
**Trigger:** User: "lanjut 53 dan cycle 1 retry"
**Vision check:** ALL 5 principles pass (`docs/VISION_PRINCIPLES_LOCKED.md`)

---

## 🧭 1. CONTEXT (Day 53 morning)

| Item | State |
|------|-------|
| API | v0.5.16 healthy ✅ |
| Brain | Qwen 7B loaded, 24h KEEP_ALIVE ✅ |
| Tiranyx | idle (no contention) ✅ |
| Disk | 273GB free (plenty for llama.cpp) ✅ |
| Model blobs | accessible at `/opt/ado/data/ollama/models/blobs/` ✅ |
| GPU pods | 0 active (clean) ✅ |
| Lessons | 70 cumulative |
| Vision principles | LOCKED PERMANENT (Day 52) |

---

## 🎯 2. THREE TRACKS PARALLEL

### Track A — Speculative Decoding via llama-server (HIGH, ~3-4 hr)

**Hipotesis:** Use llama.cpp `llama-server` (C++ binary, in Docker) for speculative decoding. Qwen 7B target + Qwen 0.5B draft. **All local, vision-aligned (Principle 1, 2, 3, 5 ✅).**

**Why bypass Ollama:**
- Ollama 0.22.1 + 0.23.1 NO native speculative decoding (PR #8134 closed unmerged)
- llama-server has it since 2024 (`--model-draft` + `--draft-max`)

**Risk:** MED — new infrastructure component on shared VPS. Need careful resource budget.
- KV cache cost ~5.5-6GB (target + draft). Fits in 32GB but adds to budget.
- May not actually achieve 1.5x if acceptance <60% (creative prompts tank acceptance).

**Benefit:** Chat 7-22 → 12-35 tok/s (1.6-2x), 100% local, vision-aligned.

**Approach:**
1. Pull `ghcr.io/ggerganov/llama.cpp:server` Docker image
2. Create symlinks for Ollama blobs as `.gguf` files in `/opt/ado/llama-models/`
3. Run llama-server container on port 8081, bind-mount models read-only
4. Test API endpoint (OpenAI-compatible)
5. Add `services/llamaserver.py` client in API container
6. Add header `X-Inference-Engine: speculative|ollama|auto` (default `auto`)
7. Auto-route: tool-calls/structured → speculative; creative → ollama
8. Telemetry: log acceptance rate per request

**KPI:**
- ≥70% acceptance rate on real chat workload
- ≥1.5x sustained speedup vs Ollama baseline
- ZERO quality regression (sample 5 prompts, eyeball check)
- 0 ollama unloads triggered (kalau RAM tight)

### Track B — Cycle 1 Retry V100 32GB (MED parallel, autonomous)

**Hipotesis:** Vast.ai V100 32GB rel=1.00 @ $0.040/hr more reliable than 4090 today (4090 unavailable in supply).

**Status:** ALREADY SPAWNED (Day 53 morning). Monitor PID 2850578 autonomous.

**KPI:** Adapter saved `/opt/ado/cycle1_output/migancore-7b-soul-v0.1/` OR clean abort.

**Cost cap:** $0.10 max (5 min smoke + 30 min train + buffer = ~2.5 hr × $0.040 = $0.10).

### Track C — Self-Learning Sources Documentation (LOW, ~30 min)

User mentioned: ajarkan basic juga via:
- https://www.w3schools.com/
- https://roadmap.sh/
- https://www.freecodecamp.org/news/
- https://discuss.python.org/
- https://stackoverflow.com/questions

**Two interpretations:**
1. Migan must be ABLE to scrape these (already can via web_read + onamix_get)
2. These should be in Migan's training/knowledge base

**Action Day 53:** Document these as approved learning sources for Migan (in BETA_LAUNCH_GUIDE + AGENT_ONBOARDING). Migan brain ALREADY has tools to read them (web_read Jina, onamix_get, onamix_search). User can paste URL → Migan reads → answers from real source.

For TRAINING data: add to seed_bank.py — generate synthetic "explain X like w3schools tutorial" prompts that distill teacher knowledge from these sources.

---

## 📊 3. KPI Day 53

| Track | KPI | Target |
|-------|-----|--------|
| A. Spec dec install | llama-server up on :8081 | health endpoint 200 |
| A. Spec dec test | First chat via llama-server | <10s respond |
| A. Acceptance rate | log per request | ≥70% target |
| A. Speedup | warm chat measured | ≥1.5x vs Ollama baseline |
| B. Cycle 1 retry | adapter downloaded OR clean abort | binary outcome |
| C. Self-learn sources | doc updated | reference list ready |
| **v0.6.0** | speculative live + lessons #71-73 | health 200 + retro |

---

## 💰 4. BUDGET PROJECTION

| Item | Estimate |
|------|----------|
| Track A spec dec (zero infra, just Docker pull) | $0 |
| Track B Cycle 1 retry V100 | $0.10 max |
| Track C docs | $0 |
| **Day 53 total** | **~$0.10** |

Cumulative: $8.33 + $0.10 = **$8.43 / $44 budget (~19%)**.

---

## 🚦 5. EXIT CRITERIA — Day 53

Must-have:
- [ ] Track A: llama-server running, sample chat working
- [ ] Track A: speculative decoding measurable speedup recorded
- [ ] Track B: Cycle 1 retry result (adapter OR clean abort)
- [ ] Track C: self-learning sources documented
- [ ] DAY53_RETRO + memory close-out

Stretch:
- [ ] Hot-swap migancore:0.1 to Ollama if Cycle 1 PROMOTE
- [ ] Identity eval if adapter exists
- [ ] Webcam capture (Day 54 alt)

---

## 🛡️ 6. SCOPE BOUNDARIES (per VISION_PRINCIPLES_LOCKED)

**Vision check on each track (5-question test):**

### Track A (Speculative Decoding)
1. Standing alone? ✅ 100% local, no third-party API in response path
2. Mentor not responder? ✅ N/A (Migan responds via own model)
3. Long-term own model? ✅ Qwen we own, llama.cpp open-source
4. Closed loop? ✅ Doesn't break DPO flywheel
5. Modular? ✅ llama-server is open standard

### Track B (Cycle 1 Retry)
1. Standing alone? ✅ Trains own Qwen with our DPO data
2. Mentor not responder? ✅ Teacher data already collected, training is internal
3. Long-term own model? ✅ Output = own MiganCore-branded adapter
4. Closed loop? ✅ THE moat
5. Modular? ✅ Adapter portable

### Track C (Self-learning sources)
1. Standing alone? ✅ Migan reads sources via own tools
2. Mentor not responder? ✅ Sources are knowledge, not RESPONDER
3. Long-term own model? ✅ Knowledge synthesized into Migan brain over time
4. Closed loop? ✅ Source content → DPO pairs possible
5. Modular? ✅ Universal pattern

**ALL 3 TRACKS PASS — proceed.**

❌ DON'T DO Day 53:
- Wrapper any teacher API as live responder (Lesson #68)
- Add new third-party SDK as default (Lesson #69)
- Speed-fix via vendor switch (Lesson #70)

---

## 🎓 7. LESSONS APPLIED + ANTICIPATED

Applied:
- All 70 lessons in code/docs
- 5-check sanity test passed for all 3 tracks
- VISION_PRINCIPLES_LOCKED followed

Anticipated #71:
**Speculative decoding != Ollama. Use llama-server for inference engine, Ollama for model lifecycle.**
- Two-tier: Ollama = registry/manage, llama-server = inference
- Vision-aligned because both are local/open

Anticipated #72:
**Self-learning sources are Migan's "library card" — must be IN tool routing, not in training only.**
- Migan should know to call web_read on roadmap.sh when user asks "ajarkan SQL basics"
- Update skill descriptions to mention these as preferred sources for educational queries

---

## 🔭 POST-DAY-53 LOOKAHEAD

If spec dec sukses + Cycle 1 sukses:
- Day 54: Hot-swap migancore:0.1 + A/B test new adapter via spec dec
- Day 55: "Otak Belajar" thread M-1 (real cycle 1 trained model)
- Day 56-60: Cycle 2 + webcam capture + iterate beta

If spec dec gagal:
- Day 54: Distill 7B → 3B own model strategy
- Cycle 1 continues parallel

If Cycle 1 gagal lagi:
- Day 54: dedicated GPU VPS evaluation OR local desktop (kalau Fahmi punya)

---

**THIS IS THE COMPASS for Day 53. Vision-aligned. Cycle 1 parallel autonomous. Spec dec serial implementation.**
