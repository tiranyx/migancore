# Day 51 Plan — Beta Soft-Launch Enablement (research-driven)
**Date:** 2026-05-06
**Trigger:** User: "lanjut" — execute Day 50 retro recommendation: beta soft-launch HIGH priority
**Research:** parallel agent (7-section synthesis on indie AI chat betas 2025-2026)

---

## 🧭 1. CONTEXT (Day 51 morning)

| Item | State |
|------|-------|
| Production | v0.5.16 healthy ✅ |
| Brain | 1.6s/21.7tps (tiranyx idle, baseline) ✅ |
| 5/6 objectives | verified working backend (Day 50) |
| Brain routing | 100% accurate (5/5 prompts → correct tools) |
| Tiranyx | idle (no CPU competition) |
| Active GPU pods | 0 (RunPod + Vast.ai both clean) |
| DPO pool | 801 (synth stopped per status) |
| Lessons | 65 cumulative |
| Bulan 2 spend | $1.44 / $30 (4.8%) |

---

## 🔬 2. RESEARCH INSIGHTS (synthesized this morning)

**Indie AI chat beta best practices 2025-2026:**

1. **Synchronous first-touch** = 80% week-2 retention vs 15% cold link (Cline beta data Feb 2025)
2. **Indonesian DM**: casual "gw bikin sendiri" + scarcity (3-4 orang) + time-bound (15 min weekend) + 15-sec video (NOT GIF)
3. **First-5-min onboarding**: ONE specific auto-greeting question + 3 chips (NOT 6+, Vercel A/B 40% better)
4. **Expectation framing**: Pi.ai pattern — "lebih lambat tapi inget + lihat gambar + cari web + makin pinter"
5. **Feedback at N=5**: shared WhatsApp group >> Notion forms (Reflect.app retro Mar 2025)
6. **3 failure modes**: account friction (magic link), empty-state paralysis (auto-greeting), first-bug churn (auto-DM Fahmi)
7. **Indonesia tactic**: weekly public X thread "Otak MiganCore Belajar Apa Minggu Ini" — narrate self-improving moat

**My synthesis for Day 51 execution:**
Focus on what AI agent (me) can deliver: enabling Fahmi to launch successfully. NOT actually sending DMs.

---

## 📐 3. EXECUTION TRACKS — H/R/B

### Track A — Beta Launch Enablement (HIGH, ~2 hr)
**Hipotesis:** Polish BETA_LAUNCH_GUIDE.md with research insights + add chat UI suggested-prompts + write video script. Fahmi only needs to copy-paste DM + record 15-sec video + create WhatsApp group.
**Risk:** LOW — config + doc + minor frontend change.
**Benefit:** Beta-ready in 1 sprint.
**KPI:**
- A1 BETA_LAUNCH_GUIDE.md polished with 7 research-validated sections
- A2 DM template Indonesian (3 versions: brief, standard, with-video)
- A3 chat.html suggested-prompt chips (3 chips showcase moats: wikipedia/image-gen/web-read)
- A4 15-sec demo video script + storyboard
- A5 In-app feedback button → WhatsApp deeplink (pre-filled conversation context)

### Track B — Cycle 1 Retry (MED, parallel ~1 hr)
**Hipotesis:** Vast.ai with `vastai/base-image:cuda-12.1.1-auto` (cloud's native, fastest boot — solves 3-cloud image pull issue).
**Risk:** MED — could fail again, but $0.30 capped budget.
**Benefit:** Validate self-improving moat for the "Otak Belajar Apa Minggu Ini" narrative.
**KPI:** Adapter saved OR clear "deferred Day 52 with new strategy" decision.

### Track C — Synth Gen Rate-Limit (LOW, defer if time)
**Hipotesis:** Add `last_chat_at` timestamp in Redis, synth pipeline checks before each round. If chat <60s ago → sleep 5 min.
**Risk:** LOW — additive only, no breaking change.
**Benefit:** Prevents Lesson #56 contention reflex when Fahmi works on tiranyx.
**KPI:** 1 simple check added to synth pipeline + integration test.

---

## 📊 4. KPI Day 51

| Item | Target |
|------|--------|
| BETA_LAUNCH_GUIDE.md polish | All 7 research insights integrated |
| DM templates | 3 versions ready copy-paste |
| Chat UI suggested chips | 3 chips visible empty-state |
| Feedback shortcut | WhatsApp deeplink button working |
| Cycle 1 attempt | success OR clean deferred |
| Documentation | DAY51_RETRO + memory + +1-2 lessons |
| Beta-ready signal | Fahmi can launch tonight if siap |

---

## 💰 5. BUDGET PROJECTION

| Item | Estimate |
|------|----------|
| Track A docs/UI (zero infra) | $0 |
| Track B Cycle 1 retry | $0.30 max |
| Track C synth fix | $0 |
| **Day 51 total** | **~$0.30** |

Cumulative: $8.33 + $0.30 = **$8.63 of $30+$7+$7 budget (~16%)**.

---

## 🚦 6. EXIT CRITERIA

Must-have:
- [ ] BETA_LAUNCH_GUIDE.md polished with research
- [ ] DM templates ready (3 versions)
- [ ] DAY51_RETRO + memory committed

Stretch:
- [ ] Chat UI 3 suggested chips deployed
- [ ] Feedback WhatsApp deeplink button
- [ ] Cycle 1 retry attempt
- [ ] Synth rate-limit fix

---

## 🛡️ 7. SCOPE BOUNDARIES

❌ DON'T:
- Add new tools (STOP per Lesson #57)
- Touch RunPod (cap habis)
- Build new feature beyond research-validated beta needs
- Send actual DMs to friends (Fahmi's scope, not AI agent)

✅ DO:
- Enable Fahmi to launch (templates, scripts, UI polish)
- Verify 5/6 objectives still working (regression check)
- Document everything per protocol mandatory

---

## 🎓 8. LESSONS APPLIED + ANTICIPATED

Applied:
- All Day 49+ lessons in code/protocol
- Research-first per mandatory protocol

Anticipated #66:
**Indie indie AI launch: build-in-public + casual Indonesian DM beats formal pitch.**
- "gw bikin sendiri" disarms comparison vs ChatGPT
- 15-sec video > GIF (Indonesian WhatsApp culture)
- Synchronous 15-min demo = 80% retention

---

## 🔭 POST-DAY-51 LOOKAHEAD

If beta launches successfully tonight:
- Day 52: First feedback collection round
- Day 53-55: Iterate on top 3 issues from beta + parallel Cycle 1 retry
- Day 56-65: Public X thread "Otak Belajar Apa Minggu Ini" if Cycle 1 done

If beta delays:
- Day 52: continue Track A polish + Cycle 1 retry
- Beta target shift to Day 53-55

---

**THIS IS THE COMPASS for Day 51. Research-driven. Fahmi-enabled. Ready-to-ship beta launch package.**
