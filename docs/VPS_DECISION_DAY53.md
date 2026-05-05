# VPS Decision Memo — Day 53 evening (2026-05-06)
**Trigger:** Fahmi screenshot Hostinger KVM pricing + "local desktop saya nggak cukup, penuh" → asking which dedicated VPS plan is enough.
**Status:** Recommendation = **DON'T BUY YET.** GPU cloud ($5 RunPod) solves the actual blocker (Cycle 1).

---

## ⚠️ Misconception clarification

**Hostinger KVM 1/2/4/8 = CPU-only (AMD EPYC). NO GPU.**

Cycle 1 training (the actual blocker for ADO moat) needs GPU. Buying Hostinger KVM does **0%** for Cycle 1. This is the most important point of this memo.

---

## 📊 Current VPS state

- IP: `72.62.125.6` (Hostinger)
- Spec: **32GB RAM, 8 vCPU, 400GB NVMe** (= equivalent KVM 8 spec)
- Co-tenants on same VPS: SIDIX, Tiranyx, Ixonomic, MiganCore
- Cost to Fahmi: $0 attributable to MiganCore (already paid for sidix/tiranyx use)
- Known contention pattern: Lesson #56 — `next build` in tiranyx project saturates CPU during chat hours

So current VPS = already KVM 8 spec, just shared.

---

## 🛒 Hostinger KVM plan analysis (for MiganCore-only dedicated VPS)

| Plan | Price/mo | vCPU | RAM | Disk | Verdict for MiganCore stand-alone |
|------|----------|------|-----|------|-----------------------------------|
| KVM 1 | $9.99 | 1 | 4GB | 50GB | ❌ Won't fit Qwen 7B (needs 5GB resident). OOM guaranteed. |
| KVM 2 | $13.99 | 2 | 8GB | 100GB | ❌ Too tight. 7B+API+DB ~6GB peak, leaves 2GB → swap thrash on multi-tool calls. |
| KVM 4 | $25.99 | 4 | 16GB | 200GB | 🟡 Workable but **chat ~50% slower** (4 vCPU vs current 8). Estimate 3-7 tok/s vs current 7-15 tok/s. UX regression. |
| **KVM 8** | $50.99 | 8 | 32GB | 400GB | ✅ Identical to current spec. Zero regression. ONLY worth buying if tiranyx contention is unsolvable + beta scales >10 users. |

---

## 🤔 Real problem decomposition

The user wants "no contention." But contention has TWO sources:

1. **Tiranyx CPU saturation during builds** (Lesson #56) — this is the documented case
2. **Migancore vs llama-server vs Ollama** (Lesson #71, Day 53 evening) — self-inflicted

Buying KVM 8 solves #1. Doesn't solve #2 (still 8 vCPU, llama-server still competes with Ollama on the new box).

**Cheaper #1 fix:** Fahmi schedules `next build` outside chat hours (19:00-23:00 WIB beta-user time). $0/month.

---

## 💰 Cost reality check

- Project total budget: **$44**
- KVM 8: $50.99/month = **$612/year** = **14× total project budget annually**
- One Cycle 1 training run on RunPod: **~$2-5 one-shot**
- Today's Cycle 1 abort cost: **$0.03**

Even if Fahmi had unlimited budget, the principle is: **spend on the bottleneck, not on the comfortable upgrade.** Cycle 1 = bottleneck. VPS = comfortable upgrade.

---

## ✅ Decision tree (use this when Fahmi asks again)

```
Apa goal-nya?
│
├─ Train Cycle 1 (Day 54 priority)
│  └─ JANGAN Hostinger. Top-up RunPod $5 atau pakai Vast credit $7 sisa.
│
├─ Chat lebih cepat
│  ├─ Sumber lambat = tiranyx?  → Disiplin schedule, $0
│  └─ Sumber lambat = 7B CPU?    → Distill 7B→3B (Day 60+), bukan beli VPS
│
├─ Eliminate co-tenant noise (psikologis "punya server sendiri")
│  └─ TUNGGU sampai Cycle 1 sukses + beta scale 10+ users. Lalu KVM 8.
│
└─ "Supaya keren"
   └─ Ego, bukan engineering need. JANGAN.
```

---

## 🎯 Concrete recommendation Day 54

### Don't buy Hostinger today. Instead:

1. **Top-up RunPod $5** (or use existing Vast.ai $7 credit)
2. **Run Cycle 1 training** (single track Day 54 per `DAY53_REVIEW_SYNTHESIS.md`)
3. **Verify adapter lands + identity eval ≥0.85**
4. **THEN** evaluate VPS need based on:
   - Beta user count (if <10, stay on shared VPS)
   - Frequency of tiranyx contention (if >2× per week, buy KVM 8)
   - Cycle 2 success (if cycles working, may need dedicated for 24/7 synthetic generation)

### If Fahmi insists on buying TODAY (against recommendation):

**KVM 8 ($50.99/mo).** Not KVM 4 (regression), not KVM 2 (OOM risk), not KVM 1 (won't fit 7B).

---

## 📝 Lesson candidate (#74 if accepted)

**Spend on the bottleneck, not on the comfortable upgrade.**
Day 53 evening: Fahmi asked "which Hostinger VPS plan?" but the actual blocker is Cycle 1 = needs GPU = Hostinger gives nothing. Resisting the comfortable purchase that doesn't solve the real problem is part of the discipline. $5 RunPod > $51/mo Hostinger when the blocker is GPU.

This pairs with Lesson #57 ("STOP — don't add tools/cloud when 21 tools already enough — DOUBLE DOWN to identity eval / hot-swap demo / Dream Cycle, NOT feature collection") and Lesson #70 ("speed problem → better local model NOT wrapper, NOT vendor swap by default").

---

## 🔁 If circumstances change

Re-evaluate VPS purchase if ANY of these triggers fire:
- Beta MAU > 10
- Tiranyx contention causes >2 chat outages/week
- Cycle 1 succeeds + Cycle 2 needs 24/7 synthetic generation that CAN'T share with chat
- Fahmi's revenue from any project source covers $51/mo recurring without dipping into project budget

**None of these are true today (Day 53).**
