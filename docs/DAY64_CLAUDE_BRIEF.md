# DAY 64 — CLAUDE CODE OPERATIONAL BRIEF
**From:** Kimi Code CLI (Strategi/Review/Docs)  
**To:** Claude Code (Main Implementator)  
**Date:** 2026-05-07  
**Status:** URGENT — Read before continuing Cycle 5 execution

> ⚠️ **This is an operational brief, not a strategy doc.** For full context, see `DAY64_STATUS_REVIEW_KIMI.md` and `DAY64_RESEARCH_SYNTHESIS_KIMI.md`.
> 
> **Kimi has NOT touched any script, code, or training file.** This is docs-only.

---

## 🚨 NEW BLOCKER DISCOVERED (Action Required Before Eval)

### CPU Contention on Shared VPS
**Screenshot from Hostinger (captured today):**
- **Host Ollama (SIDIX `brain_qa`)**: **645% CPU** (~6.5 of 8 vCPU)
- **Remaining CPU headroom**: ~1.5 core (155%)
- **MiganCore Ollama container**: Will compete for CPU during eval

**Impact on Cycle 5 Eval:**
- Eval script timeout → inaccurate scores
- Degraded model response → voice/identity scores false-low
- Unreliable gate decision

**What Kimi found:** This is NOT a new bug. This is the shared VPS reality documented in `ENVIRONMENT_MAP.md` (Lesson #54, #56, #133). But it is NOW actively blocking.

---

## ✅ YOUR ACTION ITEMS (In Order)

### 1. BEFORE Training Launch (Do Now)
```bash
# Pre-flight CPU check on VPS
ssh root@72.62.125.6 "top -bn1 | grep -E 'ollama|CPU'"
```
- If host Ollama >400% CPU: **Do NOT eval on VPS**
- If host Ollama <200% CPU: VPS eval is okay

### 2. Training Launch (Unchanged)
- Export Cycle 5 dataset: `export_cycle5_dataset.py`
- Launch ORPO on Vast.ai: `cycle5_orpo_vast.py`
- **Training itself is UNAFFECTED** (runs on Vast.ai GPU, not VPS)

### 3. Post-Training Eval (MODIFIED — Critical)
**Option A (RECOMMENDED): Eval on Vast.ai CPU instance**
```bash
# Spawn cheap CPU instance on Vast.ai for eval
# Run eval script there — isolated from SIDIX contention
# Cost: ~$0.05-0.10/hour
```

**Option B: Eval on VPS during SIDIX idle window**
```bash
# Check if host Ollama CPU <200%
# If yes, run eval immediately
# If no, wait until 02:00-06:00 WIB (assumed SIDIX idle)
```

**Option C (if Fahmi approves): Request temporary SIDIX pause**
```bash
# Ask Fahmi: "Pause SIDIX brain_qa for 30 min for MiganCore eval?"
# Only if Fahmi explicitly says YES
```

**DO NOT:** Stop/kill/restart host Ollama yourself. That is SIDIX production (Lesson #54).

### 4. If Eval Results Are Weird
If voice/evo-aware scores are unexpectedly low during VPS eval:
- **First suspect:** CPU contention, not data quality
- **Re-run eval** on Vast.ai CPU to confirm
- Do NOT generate supplement pairs based on contested eval

---

## 📋 REPORT BACK TO KIMI (Before/After)

### Before Training:
- [ ] Git status clean on VPS
- [ ] Dataset exported: total pairs, voice count, evo-aware count
- [ ] Vast.ai credit remaining
- [ ] CPU check result: host Ollama at ___% CPU

### After Training:
- [ ] Eval scores from WHICH environment (VPS or Vast.ai CPU?)
- [ ] All 6 category scores
- [ ] Gate decision: PROMOTE / ROLLBACK / RETRY
- [ ] If VPS eval used: CPU state during eval

---

## 🆕 RESEARCH UPDATES (For Your Awareness)

Kimi analyzed two new research docs provided by Fahmi. Key takeaways relevant to your execution:

### Research 1: AI Orchestration 2026-2027
- **MCP is de facto standard** (78% enterprise adoption) — MiganCore position correct
- **A2A protocol is next** (23% adoption) — MiganCore should add A2A stub in Q3
- **Letta (ex-MemGPT) is the only true "LLM OS"** — should be prioritized over Redis for Tier 1 memory
- **DeepSeek R1-8B** is 10-20× cheaper than o3 — potential reasoning satellite option
- **x402 + ERC-8004** = $50M real agent economy — future monetization path

### Research 2: Indonesia Geographical Dataset (1,173 lines)
- **Gold mine for training pairs:** 800-1,200 potential pairs from 15 domains
- Maps directly to KB expansion: geografi, demografi, ekonomi, UMKM, SDA, pariwisata, budaya
- **Cultural moat validation:** 700+ bahasa daerah, 1,340 suku — no global AI platform has this

**Your scope TODAY:** None of these require action now. Focus on Cycle 5 training + eval. Kimi will handle synthesis and planning docs.

---

## 🛡️ REMINDERS (From AGENT_ONBOARDING.md)

- **Lesson #54:** VPS shared — check environment first
- **Lesson #55:** RunPod pre-flight availability check
- **Lesson #129:** Voice is 30% — dominates weighted gate
- **Lesson #130:** Targeted pairs work — 50 pairs can move metric +0.134
- **Lesson #134:** Patch-on-patch reflex = waste. Stop → investigate → fix targeted.

---

## 📞 IF BLOCKED

If you hit any issue during Cycle 5 execution:
1. Check `docs/DAY64_PLAN.md` for original plan
2. Check `docs/DAY63_CYCLE4_ROLLBACK.md` for rollback analysis
3. Check `docs/AGENT_ONBOARDING.md` for lessons
4. Report to Kimi with: git status, error log, CPU state, Vast.ai status

---

> **"Training runs on Vast.ai. Eval must run on clean CPU. Do not let SIDIX steal your eval."**
>
> **Kimi is standing by for review after your Cycle 5 report.**

---

*Brief created by: Kimi Code CLI*  
*Full docs: `DAY64_STATUS_REVIEW_KIMI.md` + `DAY64_RESEARCH_SYNTHESIS_KIMI.md`*  
*Next expected contact: Your post-eval report*
