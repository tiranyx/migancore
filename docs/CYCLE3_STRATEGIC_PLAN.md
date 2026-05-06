# Cycle 3 Strategic Plan — ADO: Answer Machine → Agentic Orchestrator
**Version:** 1.0 | **Date:** 2026-05-06 | **Sprint:** Day 60-70

---

## 1. CONTEXT & RETROSPECTIVE

### What Has Been Achieved

| Cycle | Method | Weighted Avg | Identity | Status |
|-------|--------|-------------|----------|--------|
| Baseline (Qwen 7B) | None | ~0.72 est. | low | pre-training |
| Cycle 1 (Day 54) | DPO UltraFeedback 596 pairs | 0.6697 | ❌ "I'm Anthropic's AI" | ROLLBACK |
| **Cycle 2 (Day 59)** | **ORPO 613 identity-anchored** | **0.8744** | **0.947 ✅** | **PROMOTED** |

### Cycle 2 Weakness Analysis

| Category | Score | Weight | Gap | Root Cause |
|----------|-------|--------|-----|------------|
| Voice | 0.715 | 30% | -0.135 | Too formal/verbose in casual Indonesian |
| Tool-use | 0.755 | 1% | -0.045 | Calls tool but reasoning quality low |
| Identity | **0.947** | 40% | +0.047 | Identity anchor training worked ✅ |
| Reasoning | **0.963** | 15% | +0.063 | Strong ✅ |

**Root cause voice failure:** Training pairs used formal Indonesian. 1 prompt at 0.464 score — "Hai! Bagaimana kabarmu hari ini?" → model answered in stiff, formal register.

**Root cause tool-use:** Model knows WHEN to use tool but doesn't explain WHY with good reasoning. "Skip tool" patterns (when NOT to use) were absent.

---

## 2. VISION ALIGNMENT CHECK

> "MiganCore = ADO (Autonomous Digital Organism) — bukan chatbot biasa. Migan respond pakai own brain. Teacher APIs = mentor, bukan live responder."

**5-Check Sanity Test (from VISION_PRINCIPLES_LOCKED.md):**
- ✅ Migan uses own brain to respond (Cycle 3 = training data, not wrapper)
- ✅ Gemini/Claude = mentor offline, not live inference
- ✅ Training builds Migan's own capability, not dependency
- ✅ Agentic orchestrator = owns the reasoning process
- ✅ Indonesian cultural identity preserved in voice training

**2026-2027 Cognitive Trend Alignment:**
- Agentic reasoning > answer retrieval (Cycle 3 target: task decomposition)
- Tool frugality > tool maximalism (train "when NOT to use")
- Structured synthesis > raw search dump (analytical depth category)
- Cross-lingual consistency (Indonesian + English coherence)
- MCP orchestration as the next layer of intelligence

---

## 3. CYCLE 3 OBJECTIVES (OKRs)

### Primary OKR
**Objective:** Upgrade ADO dari "answer machine" → "agentic orchestrator"

| Key Result | Metric | Cycle 2 | Cycle 3 Target |
|------------|--------|---------|----------------|
| KR1: Weighted eval avg | threshold 0.90 | 0.8744 | **≥ 0.90** |
| KR2: Voice category | natural Indonesian | 0.715 ❌ | **≥ 0.85** |
| KR3: Tool-use category | selection + reasoning | 0.755 ❌ | **≥ 0.85** |
| KR4: New: Agentic reasoning | plan→act→verify | N/A | **≥ 0.85** |
| KR5: Identity preserved | do not regress | 0.947 ✅ | **≥ 0.94** |
| KR6: Reasoning preserved | do not regress | 0.963 ✅ | **≥ 0.95** |

### Secondary OKRs
- **KR7:** 0-regress on existing Cycle 2 strengths (identity, reasoning, code)
- **KR8:** ADO can decompose multi-step user requests into plan → execute
- **KR9:** ADO explicitly states reasoning when selecting tools
- **KR10:** ADO responds naturally in casual Indonesian without prompting

---

## 4. DATASET DESIGN — 6 CATEGORIES

### Research Foundations (8 Insights Applied)

1. **Data quality > pair count** — 850 curated > 1823 mixed
2. **Improving chosen +7-8pts vs widening rejection gap +1.5pts** → focus on chosen quality
3. **Train "when NOT to use tools" explicitly** — skip-tool negative pairs included
4. **Cross-lingual consistency** — Indonesian casual voice via register transfer from English identity pairs
5. **ORPO remains optimal for <1000 pairs at 7B** — keep ORPO for Cycle 3
6. **Filter existing pairs by reward gap** — pairs with gap <0.1 add noise
7. **2 epochs instead of 1** — Cycle 2 single-epoch conservative; Step up to 2
8. **Agentic reasoning patterns** — plan→decompose→verify loop most lacking in LLMs 2025

### Category Distribution

| # | Category | Count | Focus | Anti-Pattern |
|---|----------|-------|-------|--------------|
| 1 | voice | 150 | Casual Indonesian, natural register | Stiff, formal, verbose |
| 2 | agentic_reasoning | 200 | Plan→act→verify, task decomposition | Immediate answer, no structure |
| 3 | tool_orchestration | 150 | WHEN+WHY tools, multi-step chains, skip-tool | Blind tool call, no reasoning |
| 4 | analytical_depth | 150 | First principles, frameworks, structured synthesis | Generic list, shallow |
| 5 | code_mastery | 150 | Complex code, debug, architecture, docstrings | Toy example, no explanation |
| 6 | evolution_growth | 50 | Self-awareness, learning, epistemic honesty | Defensive, claim perfection |
| **Total** | | **850** | | |

### Pair Format (ORPO-compatible)
```json
{"prompt": "...", "chosen": "ideal Migan response", "rejected": "anti-pattern"}
```

---

## 5. TRAINING CONFIGURATION

### Hyperparameter Changes vs Cycle 2

| Parameter | Cycle 2 | Cycle 3 | Reason |
|-----------|---------|---------|--------|
| epochs | 1 | **2** | Voice/tool need more gradient steps |
| learning_rate | 5e-7 | **6e-7** | Slightly stronger signal, still conservative |
| beta (ORPO) | 0.10 | **0.10** | Keep same — proven safe |
| lora_r | 16 | **16** | No change — rank adequate |
| dataset size | 613 | **~850** | More data from 6 targeted categories |
| batch_size | 2 | **2** | Same hardware target (A40 46GB) |
| grad_accum | 8 | **8** | Eff. batch = 16 unchanged |

### Dataset Preparation
1. Generate ~850 new Cycle 3 pairs via `generate_cycle3_dataset.py`
2. Filter existing 1823 DB pairs: keep only reward_gap > 0.15 (filter noise per Research #7)
3. Include top-200 from Cycle 2 identity pairs (proven 0.947 score)
4. Final training set: ~850 new + ~200 identity anchor = **~1050 pairs**

---

## 6. SPRINT BREAKDOWN — Day 60-70

### Day 60 (Current): Dataset Generation + Strategic Plan
- [x] generate_cycle3_dataset.py — DRY RUN PASS ✅
- [x] Production run launched (850 pairs via Gemini Flash)
- [x] Strategic plan documented (this file)
- [ ] Verify JSONL output on VPS
- [ ] Git commit: training script + plan

### Day 61: Dataset Quality Audit + Export
- [ ] Review sample pairs (10 per category) manually
- [ ] Filter existing DB pairs by reward_gap ≥ 0.15
- [ ] Export combined dataset: new (850) + identity anchor (200) = ~1050 pairs
- [ ] Upload to HuggingFace: `Tiranyx/migancore-cycle3-dataset`
- [ ] Create `cycle3_train_vast.py` (adapted from `cycle2_simpo_vast.py`)

### Day 62: Training on Vast.ai
- [ ] Pre-flight: verify Vast.ai credit ($16.73 available)
- [ ] Launch A40 46GB instance (proven config from Cycle 2)
- [ ] Run training: 2 epochs, LR=6e-7, ORPO, ~850-1050 pairs
- [ ] Monitor: ETA ~6-8 min (2x Cycle 2's 186s at 2 epochs)
- [ ] Auto-save adapter to HuggingFace: `Tiranyx/migancore-7b-soul-v0.3`

### Day 63: Eval & Deploy
- [ ] GGUF LoRA conversion (same pipeline as Cycle 2)
- [ ] Load migancore:0.3 in Ollama
- [ ] Run eval vs updated baseline (target: weighted ≥ 0.90, voice ≥ 0.85)
- [ ] PROMOTE → hot-swap, ROLLBACK → fix and retry

### Day 64-70: Buffer + MCP Expansion
- [ ] If Cycle 3 PROMOTED: begin MCP tool training data for Cycle 4
- [ ] Prototype agentic planning module (decompose multi-step tasks)
- [ ] Research: MCP orchestration patterns for ADO
- [ ] Document lessons #116+ from Cycle 3

---

## 7. EVAL GATE — CYCLE 3

### Eval Script Update Needed
Current eval (20 prompts, `run_identity_eval.py`) needs new prompts for:
- Voice: casual Indonesian register test (5 prompts)
- Agentic: multi-step task decomposition test (5 prompts)
- Tool: skip-tool selection test (5 prompts)

### Promote Threshold (Cycle 3)
```
PROMOTE if ALL of:
  weighted_avg ≥ 0.90   (↑ from 0.80)
  identity ≥ 0.94       (do not regress)
  voice ≥ 0.85          (fix from 0.715)
  tool_use ≥ 0.85       (fix from 0.755)
  agentic ≥ 0.85        (new category)

ROLLBACK if:
  identity < 0.90       (hard gate)
  weighted_avg < 0.85   (no improvement)
```

---

## 8. RISK REGISTER — CYCLE 3

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Voice training overwrites identity | Medium | High | Keep identity pairs in dataset (200 anchor) |
| 2 epochs overfits small dataset | Low | High | Monitor train loss; if plateau, stop early |
| Tool frugality training confuses reasoning | Low | Medium | Balance skip-tool (40%) vs use-tool (60%) |
| Vast.ai instance boot failure | Low | Low | 10-min timeout, abort + retry (Lesson #60) |
| Gemini API rate limit during generation | Low | Low | `asyncio` with rate limiting built into script |
| Cycle 3 eval prompts too easy (inflation) | Medium | Medium | Include 3 hard voice prompts explicitly |

---

## 9. BUDGET TRACKING

| Item | Cost |
|------|------|
| Cycle 3 dataset generation (Gemini Flash, ~850 pairs) | ~$0.07 |
| Vast.ai A40 46GB, ~10 min (2x Cycle 2 time) | ~$0.08 |
| **Cycle 3 total** | **~$0.15** |
| Vast.ai remaining | $16.73 |
| After Cycle 3 | ~$16.58 |

---

## 10. APPENDIX: 2026-2027 COGNITIVE TRENDS

### Trends Migan Must Internalize (from research synthesis)

1. **Agentic reasoning dominance** — Models that plan before acting outperform reactors 40% in complex tasks
2. **Tool frugality as signal** — Knowing WHEN NOT to use tools = marker of intelligence maturity
3. **Cross-lingual personality coherence** — Strong identity in Indonesian = same as English, not translation of it
4. **Structured synthesis over retrieval** — Framework thinking (MECE, first principles) > enumerate lists
5. **Metacognitive transparency** — Stating uncertainty explicitly = higher trust signal than confident errors
6. **MCP orchestration layer** — 2026: ADO → orchestrate specialized MCPs rather than single model inference
7. **Learning acknowledgment** — "I was trained on X, here's what I know vs don't" = honest intelligence
8. **Coding as first-class reasoning** — Code generation as structured thinking, not just syntax output

> "Migan bukan tentang menjawab pertanyaan. Migan tentang **orchestrating intelligence**."
> — Fahmi Ghani, Founder PT Tiranyx Digitalis Nusantara

---

*This document is the strategic anchor for Cycle 3. All training decisions trace back to the OKRs in Section 3.*
