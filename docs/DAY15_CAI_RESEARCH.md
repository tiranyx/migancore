# DAY 15 — Constitutional AI Research, Synthesis & Architecture
**Date:** 2026-05-03  
**Author:** Claude Sonnet 4.6  
**Methodology:** Research-first → Synthesis → Benchmark → Execute → Analyze

---

## 1. Research Phase (2025-2026 Sources)

### 1.1 Self-Evolving Agents — State of Science

**Source:** arxiv.org/abs/2508.07407 — "A Comprehensive Survey of Self-Evolving AI Agents" (August 2025)

Key framework — 4-component feedback loop underlying all self-evolving systems:
```
System Inputs → Agent System → Environment → Optimizers → (back to Agent System)
```

**MiganCore ADO state after Day 14:**
| Component | Status |
|-----------|--------|
| System Inputs | ✅ SOUL.md, Constitution, user context |
| Agent System | ✅ 7B model + 3-tier memory (Redis+Qdrant+Letta) |
| Environment | ✅ User conversations, tool execution results |
| **Optimizers** | ❌ MISSING — this is Day 15 |

Optimizer techniques survey (ranked by adoption 2025):
1. **DPO** (Direct Preference Optimization) — most production-ready
2. **Self-Rewarding** / LLM-as-Judge — generates its own preference labels
3. **SPIN** (Self-Play Fine-Tuning) — between SFT and RL, no human labels
4. **Constitutional AI** — principle-based critique-revise, generates (chosen, rejected) pairs

**Lesson:** We don't need external human annotations. The model can critique itself.

### 1.2 Constitutional AI Implementation

**Source:** Anthropic (2022, arxiv 2212.08073) + C3AI at ACM Web Conf 2025 (arxiv 2502.15861)

**Classic CAI pipeline:**
```
[Human] → SL-CAI (supervised via self-critique) → RL-CAI (via RLAIF)

Self-critique loop:
1. Sample response from model
2. Ask model to critique response vs constitution principles
3. Ask model to revise based on critique
4. Store (original, revised) as preference pair
5. Train DPO on accumulated pairs
```

**C3AI 2025 insight:** Not all principles are equal. Some principles drive 5x more preference pair quality than others. The key differentiators are:
- **Principles that are specific** (not vague like "be helpful")
- **Principles with measurable proxies** (length, citations, format)
- **Principles that are in tension** (forces non-trivial choices)

**Adaptation for MiganCore:** Design CONSTITUTION.md with measurable, specific principles.

### 1.3 DPO Preference Data — Production Best Practices

**Source:** philschmid.de — "How to align open LLMs in 2025 with DPO" + Anyscale DPO guide

**Key findings:**
- On-policy data (from your model) > off-policy (from GPT-4)
- ~1.9k preference pairs × 3 epochs = 5% improvement on 7B models
- Format: `{prompt: str, chosen: str, rejected: str}`
- Scoring: rule-based > LLM-judge for verifiable domains; LLM-judge for general chat
- DPO beta = 0.1 (conservative alignment)
- Learning rate: 5e-6 (much lower than SFT)

**DPO training stack (for Week 4):**
- TRL (Hugging Face) + vLLM for generation
- RunPod RTX 4090 at $0.34/hr — 1.9k pairs × 3 epochs ≈ 2-4 hours

**Data quality insight:** "Without a Reward Model as intermediary, errors in preference pairs directly impact model behavior." → Quality filter matters more for DPO than RLHF.

### 1.4 LLM-as-Judge — What Works at 7B Scale

**Source:** arxiv 2509.13332 — "Thinking Small Models are Efficient LLM Judges"

Critical finding — model capacity requirements:
| Task Type | 0.6B Judge | 7B Judge |
|-----------|-----------|---------|
| Chat Easy | ~70% | ~90% |
| Chat Hard | < 50% ❌ | ~75% ✅ |
| Safety eval | < 50% ❌ | ~72% ✅ |

**Decision:** Use `qwen2.5:7b-instruct-q4_K_M` as judge (same model critiquing itself). Research shows same-model self-critique still significantly improves alignment via Constitutional AI.

**Meta-Rewarding** (arxiv 2407.19594): Model judges its own judgments. Self-referential but works at 7B. Day 16+ opportunity.

### 1.5 Memory Architecture 2026

**Source:** mem0.ai/blog/state-of-ai-agent-memory-2026

Critical insight: "As foundation models converge in capability, the differentiator for enterprise agents will increasingly be **what memory they have accumulated** rather than which model they call."

**MiganCore memory stack vs. state of art:**
| Dimension | Industry 2026 | MiganCore Day 14 |
|-----------|--------------|-----------------|
| Short-term | In-memory / Redis | ✅ Redis K-V Tier 1 |
| Episodic | Vector store | ✅ Qdrant Tier 2 |
| Semantic | Entity graph (Mem0g/Zep) | ✅ Letta blocks Tier 3 |
| Knowledge auto-grow | Async extraction | ✅ fact_extractor Day 14 |
| **Training signal** | Preference data flywheel | ❌ MISSING — Day 15 |

**Conclusion:** We're ahead on memory. Now we need the training data flywheel.

### 1.6 MCP — Strategic but Not Urgent

**Source:** blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/

MCP 2026 roadmap priorities:
1. Streamable HTTP scalability → horizontal scaling improvements
2. Tasks primitive → retry semantics, expiry policies
3. Governance → contributor ladder
4. Enterprise readiness → audit trails, SSO

Production-ready: Streamable HTTP transport (already in our architecture).

**Strategic decision:** MCP = high visibility/demo value but NOT on the critical path for self-evolving ADO. DPO flywheel is more foundational. MCP = Day 17-18.

---

## 2. Synthesis & Insights

### What We Learned

**L1: Optimizer is the missing piece.** MiganCore has excellent memory (Tier 1-3) but no mechanism to improve the model from interaction data. Day 15 closes this gap.

**L2: Self-critique works at 7B.** Despite the limitation of same-model judging, Constitutional AI with Qwen2.5-7B critiquing itself generates quality preference pairs. The research validates this across multiple papers.

**L3: Quality filter matters more than quantity.** 1.9k HIGH-quality pairs > 10k noisy pairs for DPO. Our `judge_score` column + score threshold is the right approach.

**L4: Fire-and-forget is correct architecture.** Mem0, Letta — all production memory systems moved to async writes in 2025. We're aligned with industry.

**L5: Principles must be specific and measurable.** Vague principles generate noisy critique. Constitution must be specific.

### What NOT To Do

- ❌ Don't use 0.5B as judge — fails on quality dimensions
- ❌ Don't block HTTP response for critique/revision — adds 30-60s latency
- ❌ Don't store ALL pairs without quality filter — DPO degrades with noisy data
- ❌ Don't over-engineer: skip self-play (Day 16+), skip meta-judge (Day 17+)
- ❌ Don't critique every single turn — sampling at 50% is correct

---

## 3. Benchmarks & Success Criteria

### Objectives (Day 15)
**Primary:** Establish automated preference data pipeline from real conversations.  
**Secondary:** Validate that 7B self-critique generates meaningful quality discrimination.  
**Long-term:** Accumulate 500+ preference pairs by Week 4 for DPO training.

### KPIs & Indicators

| KPI | Target | Measurement Method |
|-----|--------|--------------------|
| Pipeline deployment | ✅ Running in production | `docker ps`, `/health` endpoint |
| Preference pairs generated | ≥ 1 after E2E test | `SELECT count(*) FROM preference_pairs` |
| Judge score distribution | Scores 1-4 (not always 5) | `SELECT avg(judge_score), min, max FROM preference_pairs` |
| Chat latency unchanged | p50 < 5s, p95 < 10s | Compare before/after |
| CAI sample rate | 50% of turns (adjustable) | Log: cai.critique_done count vs chat count |
| Constitution coverage | ≥ 10 principles | Manual review |

### Parameters
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Judge model | qwen2.5:7b-instruct-q4_K_M | Research: 0.5B fails quality dims |
| Sample rate | 0.5 (E2E: 1.0) | CPU resource management |
| Critique threshold | score ≤ 3 | Only revise clearly suboptimal responses |
| Max prompt tokens | 400 (critique) + 800 (revision) | Balance quality vs. speed |
| Temperature critique | 0 | Deterministic quality assessment |
| Temperature revision | 0.3 | Slight creativity for improvement |

---

## 4. Adaptation Plan

### Original Plan (Sprint Day 15 from SPRINT_ROADMAP.md)
```
□ Write Constitution.md (12 principles)
□ Implement critique-revise tool
□ Auto-critique vs principles
□ Store (original, revised) as preference pair
□ Preference pair table being populated
```

### Adapted Plan (After Research)
**Additions vs. original:**
1. Research-grounded constitution (not just principles, but C3AI-informed specificity)
2. Structured JSON critique output (not free text) → more reliable parsing
3. Quality filter (`judge_score > CRITIQUE_THRESHOLD`) → better DPO data
4. Sampling rate (50%) → CPU resource management
5. Source tracking (`source_method`, `source_message_id`) → training data lineage

**Removed from original:**
- Sleep-time compute (too expensive for now)
- Langfuse integration (deferred Week 3)

**Rationale for changes:** Research shows quality > quantity for DPO. Structured output from judge is more reliable than free-text critique at 7B scale.

---

## 5. Evaluation Framework

### Impact Evaluation
- **Short-term (Day 15):** Pipeline live, first pairs generated → DATA FLYWHEEL STARTS
- **Medium-term (Week 4):** 500+ pairs accumulated → DPO training ready
- **Long-term:** Model quality improves per user interaction → True self-evolving ADO

### Benefit Evaluation
- Every conversation contributes to model improvement (alignment with ADO vision)
- No human labeling required (Constitutional AI is self-supervised)
- Training data lineage preserved (source_message_id FK)
- Quality filter ensures DPO training data is high-signal

### Risk Evaluation
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Judge bias (same model) | HIGH | LOW | Accept limitation; spot-check 20 pairs/week |
| CPU overload | MEDIUM | MEDIUM | CAI_SAMPLE_RATE=0.5; monitor via docker stats |
| Poor quality pairs | MEDIUM | HIGH | score <= 3 filter; used_in_training_run_id allows re-filtering |
| Revision worse than original | LOW | MEDIUM | Future: use LLM to rank (chosen, rejected) before storing |

---

## 6. Files Affected

### New Files
- `docs/CONSTITUTION.md` — 10 core principles for Mighan-Core ADO
- `api/services/cai_pipeline.py` — critique, revise, store functions
  - `run_cai_pipeline()` — fire-and-forget entry point
  - `_critique()` — structured JSON critique via 7B
  - `_revise()` — improved response generation
  - `_store_preference_pair()` — AsyncSessionLocal INSERT

### Modified Files
- `api/routers/chat.py` — 3rd `asyncio.create_task` after index_turn_pair + knowledge extraction
- `api/main.py` — version 0.3.4 → 0.3.5

### No Migration Required
- `preference_pairs` table already exists with correct schema (from Day 0)
- No RLS on preference_pairs (correct — global training table, not tenant-scoped)

---

## 7. Self-Evolution Architecture (Post Day 15)

```
User Conversation Turn
        ↓
[API: chat.py]
        ↓
  HTTP Response (< 2s)
        ↓ [fire-and-forget — 3 parallel asyncio.create_tasks]
  ┌─────┴──────────────────────────────────┐
  │             │                          │
[Qdrant     [Letta                  [CAI Pipeline
 index      knowledge               Day 15]
 Day 12]    extraction
            Day 14]
  │             │                          │
  ↓             ↓                          ↓
Episodic    User profile           Preference pair
  memory     updates               (prompt, chosen, rejected)
                                          ↓
                               preference_pairs table
                                          ↓
                               [Week 4: DPO Training]
                                          ↓
                               Improved Qwen2.5-7B-v2
```

This is the self-evolving loop. Every conversation both uses AND improves the system.

---

## 8. Next After Day 15

| Day | Feature | Why |
|-----|---------|-----|
| 16 | LLM-as-Judge batch scoring on historical messages | Backfill data from Day 0+ conversations |
| 17 | MCP Server (Streamable HTTP) | External integrations, Claude Desktop |
| 18 | Langfuse observability | Monitor CAI quality, pair distribution |
| Week 4 | DPO Training on RunPod | First training run with accumulated pairs |

**Sources consulted:**
- [Self-Evolving Agents Survey](https://arxiv.org/abs/2508.07407)
- [Constitutional AI Original Paper](https://arxiv.org/abs/2212.08073)
- [C3AI at ACM Web 2025](https://arxiv.org/html/2502.15861v1)
- [DPO with Synthetic Data 2025](https://www.philschmid.de/rl-with-llms-in-2025-dpo)
- [Small Models as Judges](https://arxiv.org/html/2509.13332v1)
- [State of AI Agent Memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
- [MCP 2026 Roadmap](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
