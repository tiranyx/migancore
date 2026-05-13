# MiganCore — VISION PRINCIPLES LOCKED (anti-strategi-drift)
**Date:** 2026-05-06 (Day 52)
**Trigger:** Saya hampir salah usul "Hybrid Brain wrapper pattern" Day 52 — user tarik saya kembali ke visi.
**Status:** PERMANENT — wajib baca sebelum propose strategy apapun.

---

## ⚠️ KESALAHAN SAYA YANG HARUS TIDAK DIULANG

**Day 52 saya usulkan:** "Pakai Kimi K2 sebagai LIVE chat responder" untuk fix chat slow.

**User koreksi:** *"Guru API itu gunanya untuk membantu migancore BELAJAR, bukan untuk jadi PENJAWAB, tapi buat synthetic conversation MENGAJARKAN migancore."*

**Yang saya salah:** Saya gampang lompat ke "wrapper pattern" untuk solve UX problem. Itu **defeats the entire purpose**.

---

## 🎯 VISION PRINCIPLES (lock these forever)

### Principle 1: Migan = STANDING ALONE BRAIN
- Migan **JAWAB SENDIRI** dengan model + tool sendiri
- Long-term: tidak butuh dependence pada API third-party untuk RESPOND ke user
- Vision quote: "Otak inti AI Model, yang nantinya bisa di adopsi diturunkan, dikembangkan modular oleh AI model lain"

### Principle 2: Teacher API = MENTOR (NOT responder)
**OK uses untuk teacher API** (Anthropic, OpenAI, Kimi, Gemini):
- ✅ Synthetic conversation generator (Day 28 distillation pipeline)
- ✅ CAI critique judge (Day 15 quorum)
- ✅ Generate DPO pairs: `chosen=teacher, rejected=migan_baseline` → SimPO trains migan
- ✅ Vision data labeling untuk train Qwen-VL local later
- ✅ Code review for migan-generated code (catch errors)
- ✅ Identity baseline calibration

**NOT OK uses:**
- ❌ Live chat responder (=wrapper, kills moat)
- ❌ Default vision processor (long-term: own model)
- ❌ Default tool execution (we have ONAMIX, web_read, etc.)
- ❌ Anything user-facing where MIGAN should respond

### Principle 3: OWN TOOLS, NOT third-party SDKs
- ✅ ONAMIX = our browser/search tool (built from HYPERX user-owned)
- ✅ web_read = Jina Reader (third-party API but minimal, replaceable)
- ✅ tool_executor = our own dispatch system
- 🟡 Gemini Vision = third-party. **Acceptable as TEACHER for vision data**. Long-term distill to local Qwen-VL.
- 🟡 fal.ai image gen = third-party. **Acceptable** karena image generation memerlukan large diffusion model that's impractical local. May replace dengan SDXL local Day 100+.
- ❌ Don't add new third-party SDKs as DEFAULT path. Only as fallback or teacher.

### Principle 4: Self-Improving via Closed Loop
**The flywheel that matters:**
```
User chat with Migan (standing alone)
  ↓
Conversation logged
  ↓
Teacher API generates "what better answer would have been" (offline, async)
  ↓
DPO pair stored: chosen=teacher, rejected=migan
  ↓
Cycle N SimPO trains Migan
  ↓
Migan v0.N gets smarter
  ↓
Eventually: Migan responses near-equivalent to teachers
  ↓
THE MOAT: closed identity-evolution loop, no vendor can replicate
```

**Self-cognitive + self-learning** = end-state. Teacher = scaffolding to get there, NOT the destination.

**M1.6 Dev Organ extension:** The closed loop now also covers code, tools, and
workflow improvement. The correct shape is observe -> diagnose -> propose ->
sandbox patch -> test -> iterate -> validate -> promote -> monitor -> learn.
Use `docs/SELF_IMPROVEMENT_NORTHSTAR.md` and `api/services/dev_organ.py` as the
gate reference. This is still standing-alone learning, not wrapper behavior.

### Principle 5: Speed problems ≠ permission to wrapper
**When chat is slow, AVAILABLE solutions (vision-aligned):**

| Approach | Vision-fit | Notes |
|----------|------------|-------|
| **Speculative decoding** (Qwen 0.5B draft + 7B target) | ⭐⭐⭐ | 2-3x speedup, 100% local, in original kickoff |
| **Distill smaller model** (7B → 3B/1.5B trained on CAI/teacher data) | ⭐⭐⭐ | Standing alone, smaller faster |
| **Dedicated GPU VPS** | ⭐⭐ | Infra investment, no architecture change |
| **Better quantization** (Q4 → Q5_K_M or AWQ) | ⭐⭐ | Quality + slight speed |
| **Cycle 1+ better Qwen** | ⭐⭐⭐ | Smarter = fewer tokens = effectively faster |
| **Wrapper to teacher API** | ❌ | DEFEATS VISION |
| **Switch to GPT-only API backend** | ❌ | DEFEATS VISION |

**When in doubt:** ask "does this make Migan stronger and more independent OR weaker and more dependent?" If weaker → reject.

---

## 🛡️ STRATEGY SANITY CHECKLIST (before any new feature proposal)

Before suggesting ANY architectural change, run these 5 checks:

1. **Vision check:** Apakah ini buat Migan **standing alone** atau **wrapper third-party**?
2. **Mentor check:** Kalau pakai teacher API, apakah role-nya **MENTOR** (offline, training) atau **RESPONDER** (live, user-facing)?
3. **Standing alone check:** Long-term, apakah feature ini butuh third-party selamanya, atau bisa di-replace own model?
4. **Closed loop check:** Apakah feature ini feed data ke flywheel (DPO pairs) atau cuma ngabisin tokens API?
5. **Modular check:** Apakah feature ini bisa di-adopt by other AI agents yang fork MiganCore brain?

**Kalau check 1, 3, 4 = NO → STOP, jangan propose. Pikir lagi.**

---

## 📋 EXAMPLES — Right vs Wrong Strategic Calls

### ✅ RIGHT — Day 28 Distillation Pipeline
- 4 teacher APIs generate synthetic chats
- Stored as preference pairs
- Used untuk Cycle N SimPO training
- Migan slowly gets smarter standing alone
- **Vision-aligned: teacher = mentor, migan = student → independent expert**

### ✅ RIGHT — Day 38 analyze_image (Gemini Vision)
- Used as TEACHER for vision data baseline
- Captions/descriptions feed back as training data
- Long-term plan: distill to local Qwen-VL
- **Acceptable trade-off:** vision is HARD to do local at quality, mentor pattern OK

### ❌ WRONG — Day 52 Hybrid Brain proposal (saya hampir salah)
- Routing user chat to Kimi K2 / Gemini Flash
- Reason: speed
- **VIOLATES Principle 1, 2, 4** — wrapper pattern, no closed loop
- USER REJECTED, correctly

### ✅ RIGHT — Day 52 revised: Speculative Decoding
- Qwen 0.5B draft + Qwen 7B target
- 100% local (in Ollama already)
- 2-3x speedup
- Migan still answers, just faster
- **Vision-aligned: standing alone, own model, faster**

### ✅ RIGHT — Day 56+ Cycle 2 SimPO
- Use teacher-vs-Qwen DPO pairs from Day 52+ chats
- Teacher generated OFFLINE async, NOT live response
- Migan learns from comparisons
- **Vision-aligned: closed loop, mentor pattern**

### 🟡 EDGE CASE — fal.ai image generation
- Third-party for image gen
- TRADE-OFF: image diffusion models too large for local CPU
- Acceptable for now, plan replace SDXL local Day 100+
- **NOTE:** image generation isn't core "brain" function — it's a tool migan calls. Different from "who responds to user".

---

## 🎓 NEW PERMANENT LESSONS

### Lesson #68: Teacher API = MENTOR, NEVER live RESPONDER
**Core principle:** External APIs (Anthropic, OpenAI, Kimi, Gemini) generate training data, generate critiques, label vision — semua OFFLINE/ASYNC. **Migan respond ke user pakai own brain (Qwen + tools)**. Wrapper pattern = defeats moat.

### Lesson #69: Standing alone principle (own tools default)
**ONAMIX is the right model.** We took HYPERX (user-owned tool), made it ours, integrated as MCP. This is the pattern: own infrastructure, own tools, third-party only as teacher OR last-resort fallback. Vision doc compliance check before any new dependency.

### Lesson #70: Speed problems → better local model, not wrapper
**When CPU 7B too slow:** options ranked vision-fit:
1. Speculative decoding (Qwen 0.5B + 7B) — 100% local, 2-3x faster
2. Distill smaller (7B → 3B trained) — own model
3. Better quantization (Q5_K_M or AWQ) — quality preserved
4. Dedicated GPU — infra investment
5. Cycle N+ better-trained Qwen — smarter = fewer tokens
**NEVER:** route to live teacher API (defeats vision).

---

## 📝 DECISION LOG (for future reference)

When this file is updated, log decision below:

| Date | Decision | Why | Vision check |
|------|----------|-----|---------------|
| 2026-05-06 (Day 52) | REJECT Hybrid Brain wrapper proposal | Violated Principle 1+2+4 | User caught immediately |
| 2026-05-06 (Day 52) | ACCEPT Speculative Decoding (Qwen 0.5B + 7B) | All local, 2-3x speedup, in original kickoff | All 5 checks pass |
| 2026-05-06 (Day 52) | CONTINUE Cycle 1 retry strategy | Validates self-improving moat | Core vision |
| 2026-05-06 (Day 52) | CONTINUE webcam capture Day 53-54 | Multimodal sense, modality-as-tool, all local snapshot | Vision-aligned |

---

## 🔁 HOW TO USE THIS DOC

**Every new agent session WAJIB read this BEFORE proposing strategy.** Bookmark in onboarding flow.

**Every new feature WAJIB pass 5-check sanity test.** Document in DAY{N}_PLAN.md the vision check result.

**If unsure** between two options — ask: which makes Migan more independent? That's the answer.

---

**This doc supersedes any earlier strategic proposal that conflicts with these principles.**
**Update only with explicit user approval.**
