# RISK REGISTER — ADO Project
**Version:** 1.0 | **Last Updated:** 2026-05-02

| ID | Risk | Likelihood | Impact | Status | Mitigation | Owner |
|---|---|---|---|---|---|---|
| R01 | VPS RAM OOM (all services simultaneous) | HIGH | HIGH | 🟡 MONITORED | Docker mem limits + 8GB swap + disable Langfuse during training | DevOps |
| R02 | RunPod $50 depleted before 4 training cycles | HIGH | HIGH | 🟡 MONITORED | Community Cloud only ($0.34/hr), max 8hr per job, track in budget.md | Training |
| R03 | Fine-tuned model degrades (catastrophic forgetting) | MEDIUM | HIGH | ⬜ PLANNED | Eval gate + identity test + 50 anchor samples in every dataset | Training |
| R04 | Self-rewarding loop compounds hallucinations | MEDIUM | HIGH | ⬜ PLANNED | Constitution check on all pairs + external judge + weekly human audit | Core |
| R05 | Cross-tenant data leak | LOW | CRITICAL | ✅ MITIGATED | RLS policies + tenant_id middleware + integration tests | Backend |
| R06 | Ollama crashes under concurrent load | MEDIUM | MEDIUM | 🟡 MONITORED | Health-check + auto-restart + OLLAMA_NUM_PARALLEL=1 under load | DevOps |
| R07 | Letta service instability (early-stage product) | MEDIUM | MEDIUM | ⬜ PLANNED | Pin Docker image version + fallback to LangMem if Letta fails | Core |
| R08 | Runaway agent spawning (quota exceeded) | LOW | HIGH | ⬜ PLANNED | Hard quotas per tenant + rate limiting + circuit breaker | Backend |
| R09 | Function-calling reliability < 80% | MEDIUM | MEDIUM | ⬜ PLANNED | Constrained decoding + ReAct fallback + Hermes-3-8B as alternative | Core |
| R10 | Synthetic data quality drift after iteration 3+ | HIGH | MEDIUM | ⬜ PLANNED | MTLD diversity metric + diversity-penalized filtering + seed refresh | Training |
| R11 | Legal: using Claude output to train model | HIGH | HIGH | 🔴 ACTIVE | Use Hermes-3-405B/Llama-3.1-405B as teacher only, never Claude/GPT-4o | All |
| R12 | "Anomaly explosion" expectation mismatch | HIGH | LOW | ✅ ACCEPTED | Clear documented expectations: Week 4 = seed alive, not AGI | Human |
| R13 | VPS single point of failure | MEDIUM | HIGH | ⬜ PLANNED | Daily pg_dump to B2, weekly snapshot, deploy-as-code for fast restore | DevOps |
| R14 | Solo developer burnout | HIGH | CRITICAL | ⬜ PLANNED | AI agents do 99% work, human = review only, mandatory weekend rest | Human |
| R15 | SOUL.md drift during fine-tuning | MEDIUM | HIGH | ⬜ PLANNED | Persona consistency test gate + 50 anchor samples always in training | Training |

---

# TRAINING PROTOCOL — Self-Improvement Pipeline
**Version:** 1.0

## Overview
Every Sunday 02:00 WIB, system auto-triggers self-improvement cycle.
Can also be manually triggered via `POST /v1/admin/training/trigger`.

## Pipeline Steps

### Phase 1: Data Collection (Automatic, continuous)
```python
# feedback_collector.py — runs as Celery beat hourly
# Collects from Redis Streams: feedback.events
# Stores to: interactions_feedback table
# Implicit signals computed from: retry_count, turn_length, follow_up_rate
```

### Phase 2: Preference Pair Generation
```python
# preference_generator.py — triggered weekly
# 1. Sample N interactions (N = min(2000, available))
# 2. For each: generate 2 candidate responses from current model
# 3. LLM-as-Judge (local Hermes-3-8B): score each candidate (1-10 each dimension)
#    Dimensions: accuracy, helpfulness, persona_consistency, conciseness
# 4. If score_A - score_B > 1.5: create preference pair
# 5. Constitutional critique: auto-revise pairs that violate principles
# 6. Insert to preference_pairs table
# Target: 500+ new pairs per cycle
```

### Phase 3: Dataset Assembly
```python
# dataset_builder.py
# Combines:
#   - New preference pairs (this cycle)
#   - Anchor samples (50 fixed, never change — preserve identity)
#   - Best historical pairs (top 200 by judge_score)
# Applies curriculum sort: easy → medium → hard
# Outputs: training_dataset_YYYYMMDD.jsonl
```

### Phase 4: Training (RunPod)
```bash
# train_simpo.py — executed on RunPod RTX 4090
# Method: SimPO (no reference model needed)
# Base: current active model or GGUF
# LoRA rank: 16, alpha: 32
# LR: 2e-4, batch: 4, grad_accum: 8
# Epochs: 2 (preference training converges fast)
# Estimated: 4-6 hours
# Output: lora_adapter/ + merged GGUF Q4_K_M
```

### Phase 5: Evaluation
```python
# evaluator.py
# 1. Identity test: 5 fingerprint prompts → cosine sim > 0.85
# 2. Tool use accuracy: 20 tool-use prompts → >80% correct
# 3. General quality: 20 held-out prompts → judge_score improvement
# 4. Regression test: 10 known-good scenarios → must not degrade
# PASS: all 4 criteria met → candidate model
# FAIL: any criterion fails → rollback, log, investigate
```

### Phase 6: A/B Deployment
```
1. Hot-swap in Ollama: ollama create mighan-vX.Y -f Modelfile
2. Route 10% traffic to new model (Caddy header-based routing)
3. Monitor 24 hours: quality metrics in Langfuse
4. If new > baseline + 0.02: promote to 100%
5. If new < baseline: rollback immediately
6. Register result in model_versions table
```

## Budget Tracking
```
Training run budget: $50 total for Sprint 1
Per run estimate: $3-8 (RTX 4090, 4-8 hours @ $0.34-0.69/hr)
Max 6 runs in Sprint 1: $18-48
Conservative budget: 4 runs × $8 = $32 planned
Buffer: $18 remaining
```

---

# CONTEXT.md — Live Project State
**Last Updated:** 2026-05-02 (Initial)
**Updated By:** Project Inception

## CURRENT STATUS
Sprint: Week 1, Day 1
Active Milestone: Infrastructure Setup
Phase: THE SEED

## WHAT'S WORKING ✅
- Project documented
- Architecture decided
- Schema designed
- Protocol established

## WHAT'S IN PROGRESS 🔵
- VPS provisioning (Day 1)

## WHAT'S BLOCKED 🔴
- Nothing blocked yet

## RECENT DECISIONS
- 2026-05-02: Seed model = Qwen2.5-7B-Instruct Q4_K_M — Reason: best function-calling + Apache-2.0 + fits 32GB RAM
- 2026-05-02: Orchestration = LangGraph — Reason: deterministic, stateful, production-grade
- 2026-05-02: Memory = Letta + Qdrant — Reason: native sub-agent spawning + semantic search
- 2026-05-02: Training = Unsloth + SimPO — Reason: fastest, no reference model needed
- 2026-05-02: Teacher for distillation = Hermes-3-405B (NOT Claude/GPT-4o) — Reason: legal compliance

## KNOWN ISSUES
- None yet

## NEXT PRIORITY
1. VPS provisioning + Docker install (Day 1)
2. Ollama + Qwen2.5-7B running (Day 3)
3. FastAPI hello-world chat (Day 4)

## ENVIRONMENT STATE
- Ollama: NOT STARTED
- Postgres: NOT STARTED
- Redis: NOT STARTED
- Qdrant: NOT STARTED
- Letta: NOT STARTED
- Core Brain agent_id: NOT CREATED
- Current active model_version: NOT TRAINED
- RunPod balance: $50.00

---

# BUDGET LOG (/docs/logs/budget.md)

## RunPod Budget Tracker

**Total Allocated:** $50.00
**Total Spent:** $0.00
**Remaining:** $50.00

### Transactions
| Date | Type | Description | Duration | $/hr | Cost | Balance |
|---|---|---|---|---|---|---|
| 2026-05-02 | DEPOSIT | Initial budget | — | — | +$50.00 | $50.00 |

### Planned Spending
| Run | Purpose | Est. Duration | Est. Cost | Status |
|---|---|---|---|---|
| Run 1 | Magpie generation (Qwen-7B, 20K samples) | 8 hrs | $3 | PLANNED |
| Run 2 | SFT Run 1 (Unsloth QLoRA, 10K samples) | 8 hrs | $5 | PLANNED |
| Run 3 | SimPO Run 1 (preference pairs, 500 pairs) | 5 hrs | $3 | PLANNED |
| Run 4 | SFT Run 2 (iteration 2 with feedback data) | 8 hrs | $5 | PLANNED |
| Buffer | Emergency / extra iterations | — | $15 | RESERVED |
| **Total Planned** | | | **$31** | |

**Budget Rule:** Alert human at $15 remaining. Pause non-critical runs at $10 remaining.

---

# CHANGELOG.md

## [Unreleased] — v0.1.0-seed

### Added
- Complete project documentation (PRD, Architecture, ERD, Sprint Plan)
- SOUL.md — Core Brain identity definition
- Agent Protocol — anti-duplication and context preservation
- Database schema with full RLS multi-tenancy
- Docker Compose stack specification
- 30-day sprint plan with daily task breakdown
- Risk register with 15 identified risks
- Training protocol with automated self-improvement pipeline
- Budget tracking system

### Architecture Decisions
- **Model:** Qwen2.5-7B-Instruct Q4_K_M via Ollama
- **Orchestration:** LangGraph StateGraph
- **Memory:** Letta + Qdrant + PostgreSQL
- **Training:** Unsloth + QLoRA + SimPO
- **Multi-tenancy:** Postgres RLS + tenant_id isolation

### Not Yet Implemented
- All application code (starts Day 1 of Sprint)
