# Module Generators Backlog

Date: 2026-05-15
Owner: Fahmi + MiganCore
Status: Planned, proposal-gated

## Why This Exists

MiganCore should treat inspiring external projects as learning fuel. When Fahmi
sends a repo, paper, demo, or product link, Migan should synthesize:

1. What capability exists.
2. Why it matters for ADO.
3. What minimal module could be built.
4. What tests and gates are required.
5. What should stay proposal-only until Fahmi approves.

This document is the backlog for basic capability modules that can grow when
triggered, reviewed, tested, and promoted.

## Trigger Doctrine

User sends an inspiration link or instruction:

```text
Observe -> synthesize -> create proposal -> run gates -> build sandbox module -> QA -> owner approve -> live
```

No module should bypass proposal review. Heavy GPU modules are especially
proposal-only until cost, hardware, model license, and rollback are clear.

## Day 74 Sprint: Inspiration Intake

Shipped direction:

- Add an intake surface in the Proposal tab.
- Fahmi can paste a repo, paper, product, or raw idea.
- MiganCore synthesizes it into a normal Dev Organ proposal.
- The proposal includes module type, suggested gates, target files, tests,
  rollback plan, source URL, and creator notes.
- No external code is executed. No browsing is required. No GPU job starts.

This is the learning habit we want: inspiration becomes structured curriculum,
not random tool-chasing.

## Module 1: Image Generator

Goal:
Generate images from chat prompts and optionally refine with style, aspect
ratio, seed, and reference image.

MVP:
- Prompt-to-image request schema.
- Provider abstraction: local model, external API, or queued GPU worker.
- Output gallery artifact saved to memory.
- Safety and cost gate before execution.

Backlog gates:
- `schema_check`
- `cost_estimate`
- `content_policy_check`
- `artifact_preview`
- `owner_approval_required` for expensive runs

## Module 2: Artifact Builder

Goal:
Build reusable HTML, markdown, JSON, slide, spreadsheet, or code artifacts from
chat.

Status:
- MVP live as preview-only endpoint: `POST /v1/artifacts/preview`
- Contract documented in `docs/ARTIFACT_BUILDER_MVP.md`
- No file write, export, or deployment yet.

MVP:
- Artifact type router.
- Draft artifact preview.
- Edit history and rollback.
- Export/save path proposal before writing production files.

Backlog gates:
- `syntax`
- `schema_check`
- `preview_render`
- `rollback_ready`
- `unit_tests` when code is generated

## Module 3: Video Generator

Goal:
Learn from modern video generation systems and expose a proposal-gated video
creation module.

Inspiration:
- Lightricks LTX-2 is an audio-video generative model family with synchronized
  audio/video, multiple inference pipelines, LoRA/control variants, and
  optimization paths such as distilled inference and FP8 quantization.
- Repo: https://github.com/Lightricks/LTX-2

MVP:
- Video generation request schema: prompt, duration, aspect ratio, seed,
  reference image/video, audio source, quality tier.
- Queue-only execution; no synchronous chat blocking.
- Provider adapter skeleton for future LTX-style or hosted video backends.
- Result artifact with thumbnail, metadata, cost, and prompt lineage.

Learning questions:
- What pipeline mode is appropriate for a VPS without GPU?
- When should Migan choose image-to-video vs text-to-video vs audio-to-video?
- How should prompt, storyboard, camera motion, and audio be represented?
- What is the minimum preview that is useful before spending GPU time?

Backlog gates:
- `cost_estimate`
- `gpu_budget_check`
- `license_check`
- `queue_check`
- `artifact_preview`
- `rollback_ready`

## Module 4: Audio and Voice Generator

Goal:
Generate voice, narration, sound cues, or audio drafts for content.

MVP:
- Text-to-speech schema.
- Voice preset registry.
- Output artifact with transcript.
- Owner approval for public-facing voice.

Backlog gates:
- `voice_policy_check`
- `artifact_preview`
- `cost_estimate`
- `rollback_ready`

## Module 5: Tool Builder

Goal:
Let Migan propose small tools for itself, then sandbox and promote them.

MVP:
- Tool manifest schema.
- Tool input/output contract.
- Dry-run executor.
- Proposal queue integration.

Backlog gates:
- `contract_check`
- `data_boundary`
- `secret_scan`
- `unit_tests`
- `rollback_ready`

## Module 6: Eval and Judge Pack Builder

Goal:
Every new module should generate its own eval probes.

MVP:
- Prompt set generator.
- Expected behavior rubric.
- Regression fixtures.
- Misfire examples for routing.

Backlog gates:
- `eval_exists`
- `baseline_recorded`
- `regression_check`

## First Sprint Recommendation

Build in this order:

1. Artifact Builder MVP because it is low-cost and immediately useful.
2. Image Generator schema and artifact preview without heavy GPU execution.
3. Video Generator proposal adapter inspired by LTX-2, queue-only.
4. Eval Pack Builder so each module teaches Migan how to judge itself.

The strategic point: Migan does not need to master every generator today. It
needs the habit of turning inspiration into a small module proposal with clear
cost, tests, and rollback.
