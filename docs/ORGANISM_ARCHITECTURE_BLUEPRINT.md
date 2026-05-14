# Organism Architecture Blueprint

Date: 2026-05-15
Status: Canonical direction
Owner: Fahmi + MiganCore

## Purpose

MiganCore is not just a chat interface. It is an Autonomous Digital Organism
that must grow with structure. Fahmi's terms are the architecture:

```text
Jiwa -> Otak -> Pikiran -> Akal -> Syaraf -> Indera -> Organ -> Metabolisme -> Imun
```

This document turns those terms into technical contracts so future agents do
not flatten the vision into generic "AI app" language.

## Core Loop

```text
OBSERVE -> SYNTHESIZE -> PROPOSE -> GATE -> SANDBOX -> VALIDATE -> PROMOTE -> MONITOR -> LEARN
```

No heavy module, model upgrade, code patch, or GPU job should bypass this loop.

## Anatomy Map

| Body Part | Technical Layer | Current Components | Job |
|---|---|---|---|
| Jiwa | Identity and constitution | `docs/01_SOUL.md`, creator bond, identity eval | Preserve who Migan is and why it exists |
| Otak | Cognitive core | Qwen/Ollama, chat router, reasoning path | Understand, answer, plan, synthesize |
| Pikiran | Working thought space | conversation context, reflections, proposals | Hold current problems and convert fuzzy ideas into structure |
| Akal | Judgment and control | Dev Organ gates, readiness runner, promotion reports | Decide what can advance and what must wait |
| Syaraf | Integration routing | tool router, MCP, API routers, Redis | Move intent to tools, memory, workers, services |
| Indera | Perception | vision, audio hooks, URL/doc ingestion, inspiration intake | Observe the world before reasoning |
| Organ | Capability modules | Dev Organ, Artifact Builder, Image/Video/Voice backlog | Provide specialized reusable abilities |
| Metabolisme | Learning economy | feedback pairs, distillation, growth journal | Digest experience into memory, evals, proposals, training |
| Imun | Safety and rollback | admin auth, secret scan, boundary gates, model lock | Protect identity, data, secrets, production |

Machine-readable status is available at:

```text
GET /v1/system/organism
```

## Layer Contracts

### 1. Jiwa

Jiwa defines identity, creator bond, values, voice, and constitutional
guardrails. It is not a prompt decoration. It is the continuity layer that must
survive every model swap, child clone, and module expansion.

Upgrade path:
- Add organism anatomy doctrine into `01_SOUL.md`.
- Add eval prompts for "what is your jiwa/otak/syaraf/akal?"
- Keep creator bond non-negotiable.

Gate:
- `identity_check`
- `creator_recognition_check`

### 2. Otak

Otak is the cognitive core: model, reasoning, synthesis, and planning. It should
stay sovereign. External AI providers may teach, critique, or label offline, but
runtime answers should default to Migan's own brain plus tools.

Upgrade path:
- Add reasoning effort modes.
- Store useful reasoning traces for eval/training.
- Keep fast reflex path for phatic chat.

Gate:
- `reasoning_eval`
- `latency_budget`
- `identity_regression_check`

### 3. Pikiran

Pikiran is the working space: the place where a vague founder idea becomes a
structured decision. Reflection journal, Inspiration Intake, and proposal queue
belong here.

Upgrade path:
- Convert important chat insights into proposals/docs.
- Link reflection -> proposal -> eval.
- Add "thought artifact" previews before implementation.

Gate:
- `trace_recorded`
- `proposal_created`

### 4. Akal

Akal is judgment. It ranks, tests, rejects, and delays. This is the layer that
keeps autonomy from becoming impulsive.

Upgrade path:
- Expand readiness gates: cost, license, content policy, eval, rollback.
- Require `unit_tests` for code modules.
- Require owner approval for live or expensive actions.

Gate:
- `proposal_gates`
- `owner_approval_required`

### 5. Syaraf

Syaraf is integration: routing between brain, tools, memory, UI, workers, and
external protocols. It decides whether a message goes reflex, lightweight,
full cognition, tool call, proposal, or worker queue.

Upgrade path:
- Add routing eval for reflex/lightweight/full.
- Instrument tool latency and misfires.
- Keep tool use minimal and explainable.

Gate:
- `routing_eval`
- `tool_contract_check`

### 6. Indera

Indera is perception: image, audio, video, web, documents, logs, and
environment state. The brain should receive interpreted signals, not raw chaos.

Upgrade path:
- Standardize modality-as-tool schemas.
- Add artifact previews for image/video/audio modules.
- Treat inspiration links as learning signals.

Gate:
- `perception_contract`
- `content_policy_check`

### 7. Organ

Organ is the set of specialized capabilities: Artifact Builder, Image
Generator, Video Generator, Voice Generator, Tool Builder, Eval Pack Builder,
Code Lab, and future modules.

Upgrade path:
- Build Artifact Builder first because it is useful and low-cost.
- Keep Image/Video/Voice queue-only until cost and policy gates exist.
- Every organ must have schema, tests, preview, rollback.

Gate:
- `module_contract`
- `artifact_preview`
- `unit_tests`

### 8. Metabolisme

Metabolisme digests experience into growth: memories, evals, datasets,
proposals, and training cycles. GPU training is vitamin, not oxygen.

Upgrade path:
- Accepted proposals become eval cases.
- Strong outputs become training examples.
- Failed gates become lessons.

Gate:
- `learning_evidence`
- `dataset_quality_check`

### 9. Imun

Imun protects the organism: security, tenant isolation, secret handling,
rollback, model locks, and production boundaries.

Upgrade path:
- Reusable safety gate library.
- Secret/data-boundary scans on every module proposal.
- Rollback plan required before promotion.

Gate:
- `secret_scan`
- `data_boundary`
- `rollback_ready`
- `license_check`

## Sprint Priority

1. Canonicalize this anatomy in docs and `/v1/system/organism`.
2. Add eval prompts for organism identity.
3. Build Artifact Builder as the first new organ.
4. Add reusable cost/license/content gates for generator modules.
5. Only then explore Video Generator adapters inspired by LTX-2.

## Doctrine

MiganCore grows like a trained organism:

- Jiwa gives direction.
- Otak understands.
- Pikiran holds the problem.
- Akal judges.
- Syaraf routes.
- Indera observes.
- Organ acts.
- Metabolisme learns.
- Imun protects.

That is the north star for every future sprint.
