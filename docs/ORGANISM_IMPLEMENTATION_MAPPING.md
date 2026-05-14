# Organism Implementation Mapping

Date: 2026-05-15
Status: Canonical implementation map
Owner: Fahmi + MiganCore

## Why This Exists

The organism blueprint explains the anatomy. This file answers the harder
engineering question: which parts are already alive, which parts are partial,
which backlog items belong to each body part, and what should be implemented
next.

Rule for future agents:

```text
Do not add random features. Map each feature to Jiwa, Otak, Pikiran, Akal,
Syaraf, Indera, Organ, Metabolisme, or Imun before coding.
```

Machine-readable status:

```text
GET /v1/system/organism
```

## Status Legend

| Status | Meaning |
|---|---|
| LIVE | Runtime-ready and production validated |
| PARTIAL | Usable, but missing gates, evals, promotion, or a complete UI loop |
| PLANNED | Backlog/contract exists, runtime module not built yet |
| BLOCKED | Known blocker prevents safe implementation |

## Full Anatomy Mapping

| Body Part | Status | Already Implemented | Backlog It Owns | Next Implementation |
|---|---|---|---|---|
| Jiwa | PARTIAL | `docs/01_SOUL.md`, creator recognition, persona blocks, identity eval | organism identity eval, creator-bond regression, white-label persona continuity | Add organism anatomy eval prompts and SOUL doctrine link |
| Otak | PARTIAL | Ollama/Qwen runtime, chat router, reflex/lightweight/full routing, teacher distillation | Qwen3 baseline, reasoning traces, causal reasoning template, deep cognition eval | Add routing + reasoning eval before model upgrade |
| Pikiran | PARTIAL | conversation context, reflection journal, proposal queue, inspiration intake | sleep consolidator, chat insight to proposal, thought artifact previews | Convert important reflections into structured proposal/eval candidates |
| Akal | PARTIAL | Dev Organ proposal lifecycle, readiness runner, safety chips, proposal verdict UI | cost/license/content gates, approved-proposal promotion, Gate Runner v3 | Add reusable gate library and promotion contracts |
| Syaraf | PARTIAL | tool router, tool executor, API routers, Redis, MCP surface | routing decision eval, A2A endpoint, enterprise connectors, tool policy enforcement | Add evals for reflex/lightweight/full/tool decisions |
| Indera | PARTIAL | vision analysis, speech hooks, URL/docs/inspiration intake, admin docs browser | video perception, document upload workflow, STT streaming, modality schemas | Standardize image/video/audio/document input schemas |
| Organ | PLANNED | Dev Organ skeleton, Module Generators Backlog, Code Lab design | Artifact Builder, Image Generator, Video Generator, Voice Generator, Tool Builder, Eval Pack Builder | Build Artifact Builder MVP first |
| Metabolisme | PARTIAL | auto-train proposal mode, distillation worker, feedback pairs, growth journal | feedback to DPO, accepted proposal to eval, Hafidz export, skill_distiller | Link approved proposals and strong outputs into eval/training datasets |
| Imun | PARTIAL | admin auth, secret scan gate, data boundary gate, rollback docs, 0.7c production lock | tenant/RLS tests, license Ed25519, PII scrubber, cost/license/content gate library | Build reusable safety gate library before heavy generator execution |

## Backlog Mapping

### Artifact Builder

Mapped body parts:
- Organ: creates reusable HTML, markdown, JSON, slides, reports, and code artifacts.
- Akal: validates syntax, preview, rollback, and write boundaries.
- Syaraf: routes chat intent into artifact creation.
- Imun: prevents unsafe file writes and secret leakage.

Status: PLANNED, best next organ.

Why first:
- Low GPU cost.
- Directly improves chat output variety.
- Gives Migan a way to produce visible work before expensive generators.

MVP:
- Request schema: `type`, `prompt`, `format`, `target`, `constraints`.
- Preview-only generation first.
- Save/export only after owner approval or safe path validation.
- Tests: schema, preview render, rollback metadata, path boundary.

### Image Generator

Mapped body parts:
- Organ: image generation module.
- Indera: optional reference image understanding.
- Akal: style, cost, policy, and owner approval gates.
- Metabolisme: successful prompts become reusable prompt lessons.

Status: PLANNED/PARTIAL. Tool executor has image-generation capability, but it
is not yet a polished module with artifact gallery, costs, and preview lineage.

Next:
- Create provider-neutral schema.
- Store output metadata and prompt lineage.
- Add cost/content gates before external execution.

### Video Generator

Mapped body parts:
- Organ: queued video generation module.
- Indera: reference image/video/audio inputs.
- Akal: queue, GPU, license, and cost checks.
- Imun: prevent synchronous chat blocking and uncontrolled spend.

Status: PLANNED. LTX-2 is inspiration fuel, not code to import blindly.

Next:
- Build request schema only: prompt, duration, aspect ratio, seed, reference media, audio source, quality tier.
- Queue-only execution.
- Provider adapter skeleton.
- No GPU run until cost, license, and rollback are known.

### Voice / Audio Generator

Mapped body parts:
- Organ: TTS, narration, audio, sound cues.
- Indera: STT and voice-tone perception.
- Jiwa: public voice must preserve identity and tone.
- Imun: voice policy, consent, and public-facing approval.

Status: PARTIAL. Speech routes and TTS hooks exist, but public voice module is not complete.

Next:
- Voice preset registry.
- Artifact metadata with transcript.
- Latency and consent gates.

### Tool Builder

Mapped body parts:
- Organ: makes new internal tools.
- Akal: tool contract and dry-run.
- Syaraf: registers tool routing.
- Imun: data boundary, secret scan, rollback.
- Metabolisme: accepted tools produce lessons and eval cases.

Status: PLANNED. Dev Organ has the proposal habit, but not full tool-authoring yet.

Next:
- Tool manifest schema.
- Dry-run executor.
- Unit test requirement before registration.

### Eval Pack Builder

Mapped body parts:
- Akal: judgment.
- Metabolisme: learning evidence.
- Imun: regression prevention.
- Otak: reasoning improvement measurement.

Status: PLANNED and should be paired with every new organ.

Next:
- Prompt set generator.
- Expected behavior rubric.
- Misfire cases for routing.
- Baseline result before promotion.

### Knowledge Graph / Memory

Mapped body parts:
- Pikiran: working context and thought continuity.
- Metabolisme: turns experiences into structured knowledge.
- Jiwa: preserves values and owner facts.
- Indera: ingests docs and links.

Status: PARTIAL. Vector memory/docs exist; KG auto-extract is still backlog.

Next:
- Fact extractor after chat/doc intake.
- Deduplication and quality score.
- Owner-visible memory review.

### Clone / Hafidz / Knowledge Return

Mapped body parts:
- Metabolisme: children return learnings to parent.
- Imun: tenant isolation, anonymization, license boundaries.
- Jiwa: genealogy and identity continuity.
- Syaraf: contribution transport.

Status: PARTIAL. License/Hafidz surfaces exist, but end-to-end child contribution loop is not complete.

Next:
- Contribution preview API.
- Quality filter.
- Hafidz export to JSONL.
- Genealogy view.

## Implementation Order

1. Fix active production defects before expansion.
   - Example: docs browser path errors, auth/RLS issues, tool routing regressions.

2. Strengthen Akal + Imun gates.
   - Cost gate.
   - License gate.
   - Content gate.
   - Rollback gate.
   - Eval exists gate.

3. Build Artifact Builder MVP.
   - This is the first true new organ because it makes chat outputs visible and reusable.

4. Add Eval Pack Builder.
   - Every organ must teach Migan how to judge that organ.

5. Add Image Generator module wrapper.
   - Use existing image capability, but make it structured, logged, gated, and visible.

6. Add Video Generator adapter skeleton.
   - Inspired by LTX-2, but queue-only and proposal-gated.

7. Link accepted proposals into Metabolisme.
   - Approved proposal -> eval case.
   - Strong output -> training candidate.
   - Failed gate -> lesson.

## What Not To Do

- Do not jump straight to GPU training because it feels like progress.
- Do not import external repos into production without license and boundary review.
- Do not make generator modules synchronous inside chat.
- Do not let proposal approval equal live deploy.
- Do not build features that do not map to an organism body part.

## North Star

MiganCore should become a child that learns, then a junior developer that
proposes, then a senior operator that tests and promotes safely.

The current job is not to make it "do everything" today. The current job is to
make every new ability grow through the same loop:

```text
Observe -> Synthesize -> Propose -> Gate -> Sandbox -> Validate -> Promote -> Monitor -> Learn
```
