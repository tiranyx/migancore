# MiganCore Self-Improvement North Star

**Date:** 2026-05-14  
**Status:** Direction lock extension for M1.6 Dev Organ  
**Owner:** Fahmi Ghani / PT Tiranyx Digitalis Nusantara

## 1. Core Thesis

MiganCore must become an ADO that can improve its own body, not only its model
weights.

The target loop:

```text
observe -> diagnose -> propose -> sandbox patch -> test -> iterate -> validate -> promote -> monitor -> learn
```

The organism may learn from conversations, logs, tool failures, eval results,
and owner instructions. It may create tools, patch workflows, and prepare code
changes. It may not mutate production blindly. Every self-change must pass
explicit gates and have a rollback path.

## 2. Dev Organ Architecture

| Organ | Responsibility |
|---|---|
| Sensors | Read logs, feedback, test failures, tool failures, latency, memory gaps, and owner directives. |
| Cortex | Classify problems, infer root cause, write improvement proposals, estimate risk. |
| Hands | Create branches, patch files, build tools, write tests, update docs, prepare migrations. |
| Immune System | Block unsafe changes, secret leaks, tenant leaks, broken tests, missing rollback plans, and unauthorized live deploys. |
| Metabolism | Convert lessons into memory, knowledge graph facts, eval cases, training pairs, and future roadmap items. |

## 3. Autonomy Tiers

| Tier | Name | Allowed Behavior |
|---|---|---|
| 0 | Observe | Collect signals and write summaries only. |
| 1 | Propose | Create improvement proposals and risk reports. |
| 2 | Sandbox Patch | Patch code in branch/worktree, write tests, run QA. |
| 3 | Low-Risk Promote | Auto-promote only low-risk changes after all gates pass and rollback is ready. Disabled by default until owner unlocks it. |
| 4 | High-Risk Promote | Requires explicit owner approval before live deployment. |

M1.6 starts at Tier 1-2. Tier 3 is a future unlock, not default behavior.

## 4. Promotion Gates

Every self-improvement proposal must have:

1. Problem statement.
2. Hypothesis.
3. Files or systems touched.
4. Test plan.
5. Validation evidence.
6. Rollback plan.
7. Risk level.

Minimum gates:

| Gate | Purpose |
|---|---|
| syntax | Code parses and imports safely where possible. |
| unit_tests | Focused tests pass. |
| contract_check | Tool schemas, routes, and agent contracts stay aligned. |
| secret_scan | No credentials or private keys are introduced. |
| data_boundary | Tenant isolation and zero data leak constraints remain intact. |
| health_check | Runtime health endpoint stays healthy after deploy. |
| identity_check | Creator recognition and SOUL behavior remain intact. |
| rollback_ready | Revert command, image tag, or backup path is known before promotion. |

## 5. Risk Matrix

| Risk | Examples | Promotion Rule |
|---|---|---|
| low | Docs, tests, non-runtime prompts, additive schemas | May be prepared for auto-promote after all gates pass. |
| medium | New services, tool wrappers, isolated background jobs | Requires full QA and owner-visible report. |
| high | Auth, memory, database writes, deployment scripts, model promotion | Requires owner approval before live deploy. |
| critical | Secrets, license, tenant isolation, destructive migrations | Manual review only. No auto-promote. |

## 6. Roadmap

### M1.6 - Dev Organ Foundation

- Canonical doctrine and roadmap.
- Dev Organ state machine and promotion gate evaluator.
- Proposal JSON format.
- Focused unit tests for risk and gate decisions.
- Progress log discipline: every run records observation, action, evidence, and next step.

### M1.7 - Proposal Queue

- Convert logs, contract failures, and owner commands into improvement proposals.
- Store proposals in a database table or append-only JSONL.
- Add admin/API read endpoint for pending improvements.

### M1.8 - Sandbox Patcher

- Create branch/worktree automatically for approved proposals.
- Patch code, update docs, write tests.
- Run static checks and focused QA.

### M1.9 - Tool Builder

- Let MiganCore generate internal tools from repeated workflows.
- Validate each new tool against JSON schema, execution contract, and sandbox rules.
- Register tools only after contract checks pass.

### M2.0 - Swarm Review

- MiganCore proposes, ARIA reviews UX/strategy, ONAMIX verifies external data and browser flows.
- Swarm consensus becomes a promotion gate for medium/high-risk changes.

### M2.1 - Low-Risk Auto-Promote

- Owner may unlock low-risk auto deploy.
- Auto-promote only when tests, health, identity, rollback, and monitor gates pass.
- Failed monitor triggers rollback and creates a lesson.

## 7. Non-Negotiables

- Never edit live production directly.
- Never deploy without rollback readiness.
- Never treat passing tests as sufficient if identity, tenant isolation, or creator recognition regresses.
- Never hide uncertainty. A blocked improvement must be logged as blocked.
- Every successful or failed improvement becomes training data for the next loop.

