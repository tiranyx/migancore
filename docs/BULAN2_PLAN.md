# Bulan 2 Plan — "From The Seed to Living System" (Day 36-65)
**Drafted:** 2026-05-04 (Day 35) by Claude Opus 4.7
**Per kickoff doc timeline:** "Bulan 2 — Internal Dogfooding + 5 Beta Users"

---

## 🎯 Bulan 2 NORTH STAR

> **Migancore Core berjalan stabil di production dengan 5 beta users active. Cycle 1+2 self-improvement DONE. Migancore-7B-soul-v0.2 deployed. Memori 30 hari kuat — agent ingat user antar session.**

Per kickoff doc original:
> **Bulan 2 — Internal Dogfooding + 5 Beta Users**
> Gunakan migancore untuk semua proyek Tiranyx. Undang 5 orang terpilih. Kumpulkan feedback nyata. Identifikasi semua rough edges.

---

## 📊 STATE AT BULAN 2 START (Day 36)

| Component | Status |
|-----------|--------|
| API v0.5.0 | ✅ live |
| 3 domains | ✅ migancore.com (landing), api., app. (chat + admin) |
| Spawn UI + genealogy | ✅ Level 5 visible |
| 3 mode templates | ✅ |
| Training pipeline | ✅ ready (waiting 500+ pairs) |
| MCP server | ✅ 8 tools + 4 resources |
| DPO pool | 277 pairs (target 1000+ for Cycle 2) |

---

## 🎯 BULAN 2 OBJECTIVES (4 weeks)

### Week 5 (Day 36-42) — "Cycle 1 Self-Improvement Live"
1. **DPO pool reaches 500-700** (synthetic + distillation continued)
2. **First SimPO training run** on RunPod ($5.50)
3. **Identity eval gate** check (≥0.85 cosine sim)
4. **Hot-swap migancore-7b-soul-v0.1** to production via Ollama
5. **A/B test 24h** (10% traffic v0.1 vs 90% baseline)
6. **Promote or rollback** based on metrics
7. **Day 42 demo** — record 5-min video showing cycle complete

### Week 6 (Day 43-49) — "Beta Onboarding"
1. **Invite 5 beta users** (Fahmi's network — design/AI Indonesian community)
2. **Onboarding flow polish** (chat.html UX improvements based on Fahmi dogfooding)
3. **Multimodal chat input** (image attach via fal.ai analyze + file MD/PDF)
4. **Voice input STT** (ElevenLabs Scribe v2)
5. **Conversation export** (MD/JSON download)
6. **First 5 beta feedback session** (1-on-1, 30min each)

### Week 7 (Day 50-56) — "Distillation Pipeline Stable"
1. **GPU sourcing** — RunPod inference pod for distillation student step (eliminates Ollama CPU bottleneck)
2. **Distillation pool 200+ pairs** with reliable Kimi/Claude judge
3. **Cycle 2 training** with combined dataset (synthetic + distill + CAI)
4. **migancore-7b-soul-v0.2** released
5. **Public learn dashboard polish** — show v0.1 → v0.2 win-rate publicly

### Week 8 (Day 57-65) — "Open Source Prep + 10 Active Users"
1. **README + LICENSE polish** (Apache 2.0 ready per kickoff)
2. **`docs/` cleanup for public consumption**
3. **GitHub repo public** (per kickoff: "Bulan 3" but we're ahead)
4. **Tweet thread launch** — 5-tweet narrative
5. **10 beta users** (5 → 10 via referrals)
6. **Bulan 3 plan** drafted (mighan.com agent marketplace foundation)

---

## ⚠️ EXPLICIT BOUNDARIES (DO NOT VIOLATE per Decisions Log)

- ❌ NO mighan.com, sidixlab.com, mighantect3d.com — Bulan 3+ minimum
- ❌ NO 10-domain ADO (Creative/Programming/Marketing specialists) — Bulan 4+
- ❌ NO billing/payment system — Bulan 3+
- ❌ NO multi-org / enterprise features — Bulan 4+
- ❌ NO mobile app — defer indefinitely
- ✅ FOCUS: Migancore Core stability + dogfooding + Cycle 1+2 training cycles

---

## 🗓️ WEEKLY SPRINT CADENCE

Each week:
- **Monday AM**: Read CONTEXT.md + WEEK4_DECISIONS_LOG.md, plan week's items
- **Mon-Wed**: Execute (1 PRIMARY item per day)
- **Thu**: Buffer + review distillation/synthetic pipeline status
- **Fri AM**: Test + verify
- **Fri PM**: Daily logs cleaned, weekly retro committed
- **Sat-Sun**: Hard cutoff rest (per blueprint Risk #14 — burnout prevention)

---

## 📐 KPIs Bulan 2 EXIT (Day 65)

| KPI | Day 36 baseline | Day 65 target |
|-----|----------------|---------------|
| Active users | 1 (Fahmi) | **10 beta** |
| DPO pairs | 277 | **2000+** (Cycle 2 trained) |
| Model versions deployed | 1 (base) | **3** (base + v0.1 + v0.2) |
| Conversations / day | <5 | **50+** |
| Distillation pairs (real teacher) | 0 | **200+** |
| Memory recall quality (LoCoMo-style) | not measured | **70%+** |
| Average chat response time | 30-90s (CPU) | **<10s** (RunPod GPU inference Day 50+) |
| Public stats page views | <10/day | **500+/week** (post tweet) |
| GitHub repo stars (when public) | 0 | **20+** week 1 of public |
| Cost / month | <$5 | **<$30** (within $50 budget) |

---

## 🔁 ADAPTATION PROTOCOL (Bulan 2)

If Cycle 1 training fails identity eval (≥0.85 cosine sim):
- Add more identity-anchor samples (50 → 100)
- Reduce learning rate
- Run with smaller dataset subset first
- DOCUMENT failure in WEEK5_RETRO

If <5 beta sign-ups Week 6:
- Drop sign-up bar (lower complexity ask)
- Personal DM outreach to Fahmi's network
- Iterate landing page CTA

If RunPod GPU not feasible for inference:
- Stay CPU 7B + accept slow distillation
- OR shrink to 0.5B for student step (degenerate, but unblocks data flow)
- OR pause distillation, lean 100% synthetic

If beta user feedback says "too slow":
- Prioritize GPU inference deployment Week 6 (move from Week 7)
- Consider serverless inference (RunPod Serverless, ~$0.001 per call)

---

## 💰 BUDGET BULAN 2

| Item | Estimate |
|------|----------|
| RunPod RTX 4090 training (4 cycles) | $25 |
| RunPod GPU inference (~10hr) | $7 |
| Distillation API (4 teachers) | $10 |
| ElevenLabs TTS+STT | $5 |
| fal.ai images | $5 |
| Anthropic Claude (judge + distill) | $5 |
| OpenAI / Kimi / Gemini | $3 |
| Misc / experiments | $5 |
| **Total Bulan 2** | **~$65** |

Per kickoff allocation: $50 RunPod + $20/mo VPS = $70 budget. **Within budget.**

---

## 🚦 GO / NO-GO Checkpoints

**End Week 5:** Cycle 1 trained + eval pass + hot-swap done?
- YES → continue Week 6 onboarding
- NO → fix root cause, repeat Week 5 (don't proceed to beta with broken model)

**End Week 6:** 5 beta users active + dogfooding feedback collected?
- YES → continue Week 7 distillation push
- NO → onboarding flow problem — debug + iterate, delay distillation 1 week

**End Week 7:** Cycle 2 trained, v0.2 deployed?
- YES → continue Week 8 public launch
- NO → assess: dataset quality issue or training instability? Document, retry with adjustments.

**End Week 8:** 10 beta + repo public + Bulan 3 plan drafted?
- YES → enter Bulan 3 (mighan.com marketplace)
- PARTIAL → carry incomplete to Bulan 3 first week

---

## 🎁 BULAN 2 BONUS TARGETS (if velocity allows)

1. Browser-use tool (`browser_navigate`) — table stakes for 2026
2. Vision tool (`analyze_image` via Gemini API or Qwen2.5-VL on RunPod)
3. PDF parser (Docling) + chat file attachment
4. Letta sleep-time compute (consolidation when API idle)
5. Magpie pipeline upgrade (synthetic generator v2)

---

## 📚 REQUIRED READING for Next Agent

Before starting Bulan 2:
1. `docs/CONTEXT.md` — current state (will update Day 36)
2. `docs/WEEK4_DECISIONS_LOG.md` — boundaries + rules
3. `docs/WEEK4_RETRO.md` — what worked / didn't
4. This file (`BULAN2_PLAN.md`)
5. `docs/HANDOFF.md` — operational reference
6. Original blueprint: `Autonomous Digital Organism_ 30-Day Blueprint`

**Anti-patterns to avoid (from Week 4 lessons):**
- Scope creep into 10-domain ADO
- Touching consumer domains (mighan.com, sidixlab.com)
- Triggering training before identity eval
- Ignoring `WEEK4_DECISIONS_LOG.md` boundaries
- Not running container `--build` after code changes

---

**End of Bulan 2 = Migancore Core production-grade with real users + 2 self-improvement cycles done.**
**Bulan 3 = mighan.com agent marketplace foundation (consumer domain unlock).**
