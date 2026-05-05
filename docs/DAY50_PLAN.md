# Day 50 Plan — Verify 6 Objectives + Strategic Cycle 1 Revision
**Date:** 2026-05-06
**Trigger:** User: "lanjut yuk objective sprint ini: Chat jalan, Fetch+MCP+Scrape, baca/generate image, self-learning, bisa ngoding"
**Pre-flight:** AGENT_ONBOARDING.md + ENVIRONMENT_MAP.md compliance

---

## 🧭 1. STATE ASSESSMENT (already done, evidence-based)

### What overnight Cycle 1 attempt revealed:
- Pod `i61w1twqiyndvr` SPOT 4090 CA → **BOOT TIMEOUT 617s** → auto-aborted ✅ (Lesson #60)
- 0 burning, 0 orphan ✅ (Lesson #59 verified DELETE 204 + GET 404)
- Adapter NOT created (training never started)
- Strategy verdict: **3 cloud attempts hari ini all failed at image pull stage** = need different approach

### What backend tests this morning revealed:
- ✅ Chat: 22 tok/s, 3-5s respond (was 120s+ timeout yesterday because tiranyx was building)
- ✅ Tools: onamix_search 1.8s, onamix_get 374ms, web_read 399ms
- ✅ Vision: analyze_image 4.4s with Gemini Vision (Indonesian answer "kucing belang tabby")
- ✅ Image gen: 1s fal.ai
- ✅ Code: 6.6s 132 tokens with type hints + docstring + edge cases

### Diagnosis: 5/6 objectives backend READY. Bottleneck = USER UX path + Cycle 1.

---

## 🎯 2. SIX OBJECTIVES — STATUS + ACTION

### Obj 1: Chat jalan + jawaban relevan + respond cepat
**Status:** ✅ Backend working (22 tok/s, 3-5s typical respond)
**Action:** TEST E2E via `app.migancore.com` UX (login → chat → verify chips render → tools triggered)
**Risk:** brain may not route to tools properly OR chat UI quirks
**KPI:** 1 chat round-trip <10s end-to-end via UI, tool chip renders if tool used

### Obj 2: Fetch + MCP + Scrape jalan
**Status:** ✅ Backend tools all working (onamix family + web_read)
**Action:** Verify brain CALLS these tools when prompted ("baca https://...", "cari di wikipedia X")
**Risk:** agents.json tool routing or tool description ambiguity
**KPI:** Brain emits correct tool_call for prompts with URL OR "cari/baca/scrape"

### Obj 3: Baca image
**Status:** ✅ analyze_image (Gemini Vision) working backend
**Action:** Test via UI (image upload → vision/describe endpoint → brain summarizes)
**Risk:** UI image attach flow regression
**KPI:** Upload sample image → answer in <10s

### Obj 4: Generate image
**Status:** ✅ generate_image (fal.ai) working backend, 1s
**Action:** Test via UI ("gambarkan kucing lucu" → tool called → image rendered as chip)
**Risk:** Brain may interpret as describe instead of generate
**KPI:** Image URL returned + rendered in chat thread

### Obj 5: Makin cognitive + Self-learning
**Status:** ⚠️ Cycle 1 has NEVER run (3 cloud failures hari ini)
**Action:** Strategic revision (3 options below)
**Risk:** continued cloud failures = vision unverified
**KPI:** First MiganCore-branded adapter saved + identity eval pass

**3 strategic options for Cycle 1:**
| Option | Cost | Risk | Effort |
|--------|------|------|--------|
| **A. Different image (axolotl pre-built)** | $0.10 | Med (new image, may also fail) | 10 min adapt |
| **B. Vast.ai with LARGER pool** (filter offers >$0.30/hr = real DC) | $0.30 | Med (cost more, real DC reliable) | 5 min config |
| **C. Defer Cycle 1, ship 5/6 other items** | $0 | LOW | continue Day 50 normally |

**My recommendation: C + parallel A/B research.** Ship the 5 objectives that ARE working today, treat Cycle 1 as parallel research project.

### Obj 6: Bisa ngoding
**Status:** ✅ Qwen 7B base sudah produces decent Python with type hints
**Action:** Verify brain handles longer code prompts + multi-file (kalau ada)
**Risk:** Long code generation may exceed num_predict=500 default
**KPI:** Generate 3 code samples (Python, JS, SQL) all syntactically valid

---

## 📐 3. EXECUTION PLAN — H/R/B per Track

### Track A — E2E UX Verify (HIGH priority, 1 hr)
**Hipotesis:** Backend works tapi UX path mungkin ada friction (login, tool routing, image render).
**Risk:** LOW — read-only testing.
**Benefit:** Confirms 5/6 objectives end-to-end FROM USER PERSPECTIVE.
**KPI:** 5 test scenarios pass via app.migancore.com:
  1. Login OK
  2. Plain chat: "halo" → respond <10s
  3. Wikipedia search: "cari di wikipedia raden saleh" → tool used + Wikipedia answer
  4. URL fetch: "baca https://example.com" → web_read or onamix_get
  5. Image gen: "gambarkan kucing" → image rendered

### Track B — Brain Tool Routing Audit (MED priority, 30 min)
**Hipotesis:** agents.json default_tools sudah benar (Day 46 fix), tapi mungkin description perlu strengthen.
**Risk:** LOW — config-only changes.
**Benefit:** Improve tool selection accuracy.
**KPI:** 5/5 prompt → correct tool routing in chat_with_tools probe.

### Track C — Cycle 1 Strategy Revision (LOW priority, defer-friendly)
**Hipotesis:** 3 different cloud failures = systemic image pull issue (Docker Hub rate limit? Specific image broken?).
**Risk:** MED if pursued today (cost + frustration).
**Benefit:** Validates "self-improving" claim.
**Recommendation:** Background research + try ONCE with Vast.ai >$0.30/hr filter (real DC). If fails, defer to Day 51 with axolotl pre-built image.

---

## 📊 4. KPI Day 50

| Item | Target |
|------|--------|
| Chat E2E | 5/5 scenarios pass via UI |
| Tool routing | brain picks correct tool for each prompt |
| Image read+gen | image render in chat |
| Code | 3 valid samples in 3 languages |
| **Cycle 1** | EITHER successful adapter OR clear "deferred Day 51" decision |
| Documentation | DAY50_PLAN + RETRO + MEMORY update |
| Lessons | +1-2 minimum |

---

## 💰 5. BUDGET PROJECTION

| Item | Estimate |
|------|----------|
| E2E UX testing (zero infra) | $0 |
| Brain config tuning | $0 |
| Cycle 1 retry (Vast.ai real DC) | $0.30 max |
| **Day 50 total** | **~$0.30** |

Saldo: RunPod cap habis ($0.20 left), Vast.ai $6.95 — pakai Vast.ai untuk retry.

---

## 🚦 6. EXIT CRITERIA

Must-have:
- [ ] Track A: 5 E2E scenarios tested + documented
- [ ] Track B: tool routing audit complete
- [ ] DAY50_RETRO + memory entry committed

Stretch:
- [ ] Track C: Cycle 1 attempt (with strategic revision) OR clear deferral plan
- [ ] Identity eval if adapter PROMOTE
- [ ] Hot-swap to migancore:0.1 if PROMOTE

---

## 🛡️ 7. SCOPE BOUNDARIES

❌ **DON'T DO:**
- Add new tools (STOP — 21 sudah cukup, Lesson #57)
- Touch RunPod (cap habis, Lesson #62)
- Patch tiranyx CPU contention (Fahmi's own discipline, Lesson #56)
- Premature Cycle 2 (validate Cycle 1 first)

✅ **DO:**
- VERIFY existing 5/6 objectives end-to-end
- DOCUMENT user-facing performance baselines
- DECIDE Cycle 1 path (retry vs defer)

---

## 🎓 8. LESSONS APPLIED

- #54-64 hari ini all in code/protocol
- New anticipated #65: Cycle 1 image pull failure across 3 clouds = upstream issue OR account-specific = need different image strategy

---

## 🔭 POST-DAY-50 LOOKAHEAD

If Cycle 1 succeeds:
- Day 51: GGUF + Ollama hot-swap + A/B
- Day 52-55: Identity eval + Dream Cycle prep

If deferred:
- Day 51: investigate upstream image issue (try axolotl) OR pivot to local GPU strategy
- Parallel: ship beta soft-launch with current model (Qwen 7B working fine for chat)

---

**THIS IS THE COMPASS for Day 50. Verify the 5 working things FIRST. Cycle 1 is parallel research, not blocker.**
