# Day 52 STRATEGIC PIVOT PLAN — Hybrid Brain (Teacher API + Local Qwen)
**Date:** 2026-05-06
**Trigger:** User feedback Day 51 launch — "lama banget bales halo, bukannya ada 5 teacher API?"
**Critical realization:** Kita PUNYA 4 teacher API yang nganggur. Local Qwen 7B CPU tidak workable untuk chat user real-time.

---

## 🚨 STRATEGIC ADMISSION

### What I missed
Sejak Day 1, blueprint commit ke "Qwen 7B local saja". Reasoning: privacy + biaya $0/req. Realita Day 51-52:
- **CPU 7B = 60-90s per chat** = unusable untuk beta tester
- **Tiranyx contention** = 120s+ saat Fahmi develop tiranyx
- **Context contamination bug** when retries fail
- **4 teacher APIs idle** padahal sudah dibayar/configured

User caught this immediately at moment-of-launch. **Pivot perlu sekarang.**

### Why teacher API hybrid is CORRECT path
- **Cost:** Kimi K2 input $0.10/1M, output $0.30/1M → **~$0.0002/chat avg** (ultra cheap)
- **Speed:** teacher API = <2s respond consistently
- **Quality:** Kimi/Claude/GPT >> base Qwen 7B (no contest)
- **Self-improving still works:** every teacher response → DPO pair → Qwen learns offline
- **Vision compass alignment:** modular brain = swap models per use case (this IS the architecture we promised)

---

## 🧠 HYBRID BRAIN ARCHITECTURE (Day 52 Track A — HIGH priority)

```
┌─────────────────────────────────────────────────────────┐
│ User chat at app.migancore.com                          │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ FastAPI chat router                                     │
│   ↓ classify intent (5ms heuristic)                     │
│   ├─ Long context / complex / tool-heavy                │
│   │     → Kimi K2 (Indonesian primary, $0.0001/chat)    │
│   │                                                     │
│   ├─ Vision required                                    │
│   │     → Gemini 2.5 Flash (multimodal, $0.075/1M)      │
│   │                                                     │
│   ├─ Quick / casual / "halo"                            │
│   │     → Local Qwen 7B (free, fast for short)          │
│   │                                                     │
│   └─ Code generation                                    │
│         → Local Qwen (already good at this)             │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Background: every teacher response → DPO pair generator │
│   chosen = teacher response                             │
│   rejected = Qwen base response (cached or run async)   │
│   → preference_pairs table                              │
│   → Cycle 2 SimPO trains Qwen to catch up               │
└─────────────────────────────────────────────────────────┘
```

**Key insight:** TEACHER LIVE = user UX. QWEN BACKGROUND = self-improving moat. Two layers, both critical.

---

## 📐 EXECUTION TRACKS — Day 52

### Track A — Hybrid Brain Routing (HIGH, ~3 hr)
**Hipotesis:** Modify chat.py untuk route ke teacher API based on intent classifier. Local Qwen jadi fallback OR background.
**Risk:** MED — touching core chat path. Need careful rollout.
**Benefit:** Beta UX 30x faster (60s → 2s). Vision moat preserved.
**KPI:**
- A1 Intent classifier (rule-based 5 categories: long/vision/code/casual/tool-heavy)
- A2 Kimi K2 chat handler (existing client, just add chat-specific call)
- A3 Backend telemetry (which model handled which request)
- A4 Cost tracker (sum teacher API spend per day)

### Track B — Fix Context Contamination Bug (HIGH, ~30 min)
**Hipotesis:** After 2x consecutive errors in same conv, frontend should auto-suggest "+ NEW CHAT" button highlight + clear convId on next send.
**Risk:** LOW — UX polish.
**Benefit:** Prevent "halo" → brain continues old broken context.
**KPI:** After 2 errors, "+ NEW CHAT" button blinks/glows. User sends → fresh convId.

### Track C — Camera/Webcam Capture (MED, ~4 hr — Day 53-54)
**Hipotesis:** `navigator.mediaDevices.getUserMedia()` → canvas snapshot → base64 → send to analyze_image (Gemini Vision).
**Risk:** LOW — frontend additive feature.
**Benefit:** Multimodal "5th sense" — facial expression analysis enables affect-aware AI.
**KPI:** Click "📷 Webcam" button → capture 1 frame → AI describes facial expression in Indonesian.
**Per VISION compass:** modality-as-tool routing — webcam = camera tool calling analyze_image.

### Track D — Cost Telemetry + Cap (HIGH for Track A safety, ~30 min)
**Hipotesis:** Each teacher API call logged cost. Daily cap $1.00 (auto-fallback to Qwen if exceeded).
**Risk:** LOW — additive logging.
**Benefit:** Prevent runaway billing if beta scales.
**KPI:** Per-tenant + global daily spend tracker, hard cap enforced.

---

## 💰 COST PROJECTION — Hybrid Brain

### Per-chat cost estimates (avg 500 input + 500 output tokens):
| Model | Cost/chat | Best for |
|-------|-----------|----------|
| **Kimi K2** | $0.0002 | Indonesian primary chat |
| **Gemini 2.5 Flash** | $0.0001 | Vision + cheap fallback |
| **Claude Sonnet 4.6** | $0.0045 | Complex reasoning (rare) |
| **GPT-5** | $0.0030 | English-heavy edge cases |
| **Local Qwen** | $0 | Casual/short + background training |

### Beta scale projections:
- 5 testers × 20 chats/day = 100 chats/day
- 80% routed to Kimi = $0.016/day = **$0.50/month**
- Plus existing Bulan 2 ops $1.44 = **~$2/month operational**
- Vast.ai Cycle 1+2 training periodic ~$1/month

**Total: <$5/month for full beta with hybrid brain. Sustainable.**

---

## 🎯 KPI Day 52

| Track | KPI |
|-------|-----|
| A1 Intent classifier | 5/5 test prompts categorized correctly |
| A2 Kimi chat | "halo" → respond <3s with Indonesian |
| A3 Telemetry | Each chat logs `model_used` + `cost_usd` |
| A4 Cost cap | Daily spend visible in admin |
| B Context fix | Error 2x → "+ NEW CHAT" suggested |
| C Webcam (Day 53) | getUserMedia + capture POC |
| D Daily cap | $1/day soft, $5/day hard auto-shutoff |
| **v0.6.0** | Hybrid brain LIVE, Lesson #68 documented |

---

## 🛡️ RISK MITIGATION

### What if teacher API down?
→ Auto-fallback to local Qwen (existing path, still works for casual)

### What if cost runs away?
→ Track D daily cap + per-tenant rate limit (2 chats/min/user)

### What if user thinks "MiganCore = ChatGPT wrapper"?
→ NO. Teacher used for SPEED, Qwen learns offline. After Cycle 2-3, Qwen catches up. **The moat is the closed loop, not which model serves immediate**. Document clearly in beta guide.

### What if context contamination still happens after fix B?
→ Add "Reset conversation" button always visible (one-tap nuke)

---

## 🔭 POST-DAY-52 LOOKAHEAD (refined roadmap)

### Day 53 — Camera + multimodal expansion
- Webcam capture button + frame analysis
- Maybe screen-sharing capture (for "lihat layar saya")
- Lesson #68 anticipated: modality-as-tool fully proven (image upload + webcam + voice + text)

### Day 54-55 — Beta iteration
- Iterate top 3 issues from Day 51 launch
- Public X thread "Otak MiganCore Belajar Apa Minggu Ini" (M-1 with Day 28 distillation data narrative)

### Day 56-60 — Cycle 2 SimPO with hybrid data
- Use teacher-vs-Qwen DPO pairs from Day 52+
- Train Qwen to catch up
- Hot-swap migancore:0.2

### Day 61-65 — Open beta
- Public invite Twitter/X
- "Otak Belajar" weekly threads = content marketing
- Per VISION compass: Dream Cycle prototype (Innovation #4)

---

## 🎓 LESSONS APPLIED + ANTICIPATED

Applied:
- All Day 49+ lessons in code
- Lesson #65: verify end-to-end (today's miss = teacher API not in chat path)
- Lesson #66 launch (Day 51 successful)

Anticipated #68:
**Hybrid brain (teacher API live + local Qwen background) IS the modular brain vision.**
- Pure local = unworkable on shared CPU
- Pure cloud = no moat
- HYBRID = both UX speed + self-improving moat
- This was always the right architecture, we shipped wrong default Day 1

---

## 🚀 EXECUTION ORDER

1. **NOW:** Track B (context fix) — 30 min, prevent immediate user pain
2. **TODAY:** Track A1+A2+A3 (Kimi chat routing) — 3 hr, core hybrid brain
3. **TONIGHT:** Track D (cost telemetry) — 30 min, safety
4. **DAY 53:** Track C (webcam) + Track A4 polish
5. **DAY 54+:** Beta iteration + Cycle 2 prep

**Total Day 52 effort:** ~4 hr work, $0 infra cost, +$2/month operational ongoing.

---

**THIS IS THE RIGHT PIVOT. Teacher API + local hybrid = vision actually delivered.**
