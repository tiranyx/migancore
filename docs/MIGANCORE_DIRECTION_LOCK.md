# MiganCore Direction Lock

**Date:** 2026-05-07  
**Owner:** Fahmi Ghani / PT Tiranyx Digitalis Nusantara  
**Status:** Direction locked. Do not pivot without owner approval.

This document distills the founder brief into a short canonical reference for all
agents working on MiganCore. Read this before implementation, review, research,
training, deployment, or roadmap changes.

## 1. What MiganCore Is

MiganCore is a platform for building, cloning, distributing, and deploying ADOs
(Autonomous Digital Organisms). An ADO is the core AI organism for an
organization: brain, nervous system, and identity layer.

MiganCore is not a chatbot wrapper, generic SaaS assistant, prompt-only persona,
or plugin on top of another vendor. MiganCore is a self-hosted AI organism
platform designed for confidential organizations that need their own AI brain.

One sentence:

> MiganCore is a self-hosted, clonable, white-label AI organism that can be
> retrained with an organization's own business data and workflow while keeping
> data inside the client's infrastructure.

## 2. ADO Concept

Every ADO has three core layers:

| Layer | Name | Responsibility |
|---|---|---|
| Otak | Cognitive Core | Reasoning, analysis, synthesis, self-learning loop |
| Syaraf | Integration Layer | MCP tools, APIs, workflow, memory, external systems |
| Jiwa | Identity Layer | Persona, mission, values, organization-specific behavior |

The ADO should feel like an AI brain that can be connected to different organs
and senses. The product is closer to a "Brain OS" than a chatbot UI.

## 3. Non-Negotiables

1. Zero data leak by architecture.
2. Self-hosted on client VPS or on-premise infrastructure.
3. Modular clone per organization.
4. Retrain by owner using internal business data and business flow.
5. Base skills preloaded: self-learn, analyze, synthesize, respond, use tools.
6. White-label naming: clients can rename the visible ADO.
7. License remains MiganCore x Tiranyx, even when white-labeled.
8. Anti vendor lock-in: open, migratable, self-hostable.
9. Trilingual by design: Indonesian first, English second, Mandarin third.

## 4. Product Boundary

MiganCore should always optimize for confidential organizations:

- Law firms and notaries.
- Finance, accounting, audit.
- Government and state-owned organizations.
- Clinics and private hospitals.
- Manufacturing and factories.
- Agencies and consultants that want white-label ADOs.

The first ICP is 10-500 employee organizations with sensitive data, existing IT
capacity, and willingness to pay for self-hosted AI.

## 5. White-Label And License Model

Clients may change:

- ADO display name.
- Logo and colors.
- Default language.
- Persona and tone.
- End-user visible brand.

Fixed:

- MiganCore ADO Engine.
- License file.
- License validator.
- Technical "Powered by MiganCore x Tiranyx" in admin/config.

License must support offline validation because client deployments must not
phone home by default.

Minimum license fields:

- license_id
- client_name
- ado_display_name
- issued_by
- product
- issued_date
- expiry_date
- tier
- max_instances
- language_pack
- signature

## 6. Relationship With SIDIX

SIDIX is Tiranyx internal AI lab and R&D engine. MiganCore is the external
product that can be sold, cloned, and deployed to clients.

Do not confuse paths, repos, or runtime:

- SIDIX is not the MiganCore product.
- Lessons from SIDIX may be reused.
- MiganCore must keep its own product direction, deployment model, and docs.

## 7. Current Product Interpretation

The Day 60 result confirms that the correct product thesis is:

> MiganCore is becoming a Brain OS for organization-specific ADO instances.

The validated loop is:

```text
conversation/data -> preference pairs -> ORPO training -> eval gate -> promote or rollback -> hot-swap production brain
```

This is the foundation for "AI that learns from its own experience", but the
claim must stay grounded: each promotion must pass explicit eval gates.

## 8. Self-Improvement Dev Organ

MiganCore's self-improvement loop must evolve from model-only training into a
full Dev Organ:

```text
observe -> diagnose -> propose -> sandbox patch -> test -> iterate -> validate -> promote -> monitor -> learn
```

The Dev Organ may create tools, patch workflows, update prompts, prepare code
changes, and write tests. It must never edit live production directly. A change
can move toward production only when it has a problem statement, hypothesis,
test evidence, risk classification, validation gates, and rollback plan.

Autonomy unlocks by tier:

| Tier | Scope |
|---|---|
| 0 | Observe and summarize. |
| 1 | Propose changes and classify risk. |
| 2 | Patch in sandbox/branch and run QA. |
| 3 | Promote low-risk changes only after every gate passes. Disabled by default. |
| 4 | Promote high-risk changes only after owner approval. |

Canonical reference: `docs/SELF_IMPROVEMENT_NORTHSTAR.md`.

## 9. Cognitive Synthesis

MiganCore must understand creator vision even when the input is non-technical,
intuitive, visual, or incomplete. Do not require Fahmi to write engineering
specs before helping. First translate intent, synthesize the hidden concept,
then map it to architecture, roadmap, gates, and an executable next step.

Canonical loop:

```text
raw intent -> hidden concept -> synthesis -> options -> roadmap -> executable next step -> memory
```

Canonical reference: `docs/COGNITIVE_SYNTHESIS_DOCTRINE.md`.

## 10. Agent Rules

When an agent works on MiganCore:

1. Find the correct repo and path first.
2. Do not confuse MiganCore with SIDIX.
3. Read this document and the current Day retro before editing.
4. Do not pivot the product into a generic chatbot, SaaS wrapper, or API-only app.
5. Keep self-hosting and zero data leak as architecture constraints.
6. Record findings, lessons, tests, eval results, and rollback plans.
7. Before deployment, report git status, diff stat, tests, deploy command, and rollback plan.
8. If multiple agents are active, use one main implementor and keep others as QA/review.
