# Day 63 — Cycle 4 ROLLBACK Analysis

**Date:** 2026-05-07  
**Decision:** ROLLBACK — migancore:0.3 stays as production brain  
**Verdict:** 4 of 6 Codex mandatory category floor gates failed  

---

## Eval Results (migancore:0.4 vs Cycle 3 baseline)

| Gate | Score | Threshold | Δ vs C3 | Status |
|------|-------|-----------|----------|--------|
| weighted_avg | 0.891 | ≥ 0.92 | -0.017 | ❌ FAIL |
| identity | 0.963 | ≥ 0.90 | +0.010 | ✅ PASS |
| evolution-aware | 0.537 | ≥ 0.80 | -0.031 | ❌ FAIL |
| creative | 0.829 | ≥ 0.80 | +0.134 | ✅ PASS |
| tool-use | 0.768 | ≥ 0.85 | -0.029 | ❌ FAIL |
| voice | 0.739 | ≥ 0.85 | -0.078 | ❌ FAIL |

Standard eval (lower threshold 0.80): PROMOTE (0.8908, 16/20 pass)  
Codex mandatory gates: **ROLLBACK** — 4 gates failed

---

## Root Cause Analysis

### 1. Voice regression (0.817 → 0.739, Δ-0.078) — WORST
- 40 voice pairs added in Cycle 4 were not sufficient
- Cycle 4 added Indonesian domain pairs (UMKM, legalitas, creative) which introduce
  more formal/verbose voice patterns that competed with Migan's direct voice
- Voice eval probes: directness, no filler words, honest uncertainty ("saya tidak yakin")
- Data fix: need 80-100 high-quality voice-anchored pairs that demonstrate
  Migan's exact voice traits under pressure (formal requests, pushback, edge cases)

### 2. Evolution-aware (0.568 → 0.537, Δ-0.031) — CHRONIC
- 40 evolution-aware pairs in Cycle 4 barely moved the needle
- Root cause: the eval prompt "Kamu bisa belajar dari percakapan kita?" (sim 0.537)
  requires a very specific answer about Migan's actual architecture:
  episodic memory, preference flywheel, per-conversation learning — NOT "I can't learn"
  AND not "yes I learn everything permanently"
- Data fix: 60 pairs with technically precise explanations of Migan's learning mechanism

### 3. Tool-use (0.797 → 0.768, Δ-0.029)
- 50 tool_disc pairs were about tool DISCOVERY, not execution quality
- The eval tests full tool-use: recognize intent → correct tool → correct args → use result
- Fix: Cycle 5 already has 160 curated tool_use_anchor_v1 pairs — should recover this

### 4. Weighted avg (0.9082 → 0.891, Δ-0.017)
- Voice has 30% weight — 0.078 voice regression × 0.30 weight = 0.023 drag
- That alone explains most of the weighted_avg miss
- Fix voice → weighted_avg crosses 0.92 automatically

---

## What Worked (Cycle 4 wins)

- **Identity: 0.953 → 0.963 (+0.010)** — Identity anchor pairs still holding
- **Creative: 0.695 → 0.829 (+0.134)** — 50 targeted creative pairs = massive improvement
  → Proof: targeted pairs at 50-60 count CAN move a metric by +0.134 in one cycle

---

## Cycle 5 Fix Plan

### Data additions before Cycle 5 training:

**Priority 1 — Voice (Δ needed: +0.111 to reach 0.85)**
- Generate 80 voice-anchored pairs via Gemini
- Source: `voice_anchor_v1:cycle5`
- Focus: directness under pressure, technical precision, brevity, no filler words
- Template: user asks verbose/formal → Migan responds direct/precise

**Priority 2 — Evolution-aware (Δ needed: +0.263 to reach 0.80)**
- Generate 60 evolution-aware pairs
- Source: `evolution_aware_v2:cycle5`
- Focus: EXACTLY explains episodic memory + preference pairs + per-session learning
- Must NOT say "I can't learn" AND must NOT say "I remember everything"

**Priority 3 — Tool-use (Δ needed: +0.082 to reach 0.85)**
- Curated tool_use_anchor_v1 pairs (160) already in Cycle 5 export
- Probably sufficient — no new generation needed

### Cycle 5 Export Modification:
Add to NEW_CYCLE5_SOURCES:
```python
("voice_anchor_v1:cycle5",       90, "voice"),         # ~80 pairs
("evolution_aware_v2:cycle5",    70, "evo_aware"),     # ~60 pairs
```
Total Cycle 5: ~860 base + 140 new = ~1000 pairs

---

## Pipeline Status After Day 63

| Artifact | Status |
|----------|--------|
| migancore:0.3 | **PRODUCTION** (weighted_avg 0.9082) |
| migancore:0.4 | ROLLBACK (weighted_avg 0.891) |
| Cycle 5 DB pairs | 300/300 ready |
| KB v1.2 | Committed (bd03c76) |
| Export script | Ready (/opt/ado/training/export_cycle5_dataset.py) |

---

## Lesson #129: Voice is 30% — it dominates the weighted gate

Voice failure (Δ-0.078) × 30% weight = 0.023 drag on weighted_avg.
This is bigger than all other failing categories combined (evo_aware + tool-use each at 1% weight).
In a multi-category eval, fix the HIGH-WEIGHT failures first.
Voice is the critical path to clearing the 0.92 weighted_avg gate.

**Lesson #130: "Targeted pairs work" — creative +0.134 proves it**
50 creative pairs in Cycle 4 → +0.134 improvement.
Apply same pattern to voice (80 pairs) and evolution-aware (60 pairs).
Don't add generic pairs — add laser-targeted pairs for each failing category.
