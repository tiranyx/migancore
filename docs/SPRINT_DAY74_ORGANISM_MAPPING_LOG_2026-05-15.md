# Sprint Day 74 - Organism Mapping Log

Date: 2026-05-15
Owner: Codex + Fahmi
Status: Deployed to production
Commit: `cb78e88`

## Why This Sprint Happened

Fahmi clarified that many MiganCore ideas came from SIDIX-style metaphorical
methods. The problem was not lack of backlog; the problem was that backlog
items were not mapped clearly to the digital-organism anatomy. That created a
risk of overlap, random feature work, or treating metaphor as decoration rather
than engineering structure.

## What Changed

1. Added `docs/ORGANISM_IMPLEMENTATION_MAPPING.md`.
   - Maps Jiwa, Otak, Pikiran, Akal, Syaraf, Indera, Organ, Metabolisme, and
     Imun to live code, backlog ownership, missing gaps, and next steps.
   - Separates implemented/partial/planned work.
   - Makes Artifact Builder the recommended first new Organ.

2. Expanded `/v1/system/organism`.
   - Each layer now exposes `implementation_status`.
   - Each layer now exposes `backlog_refs`.
   - Response includes a status legend: live, partial, planned, blocked.

3. Updated docs classification.
   - `ORGANISM_IMPLEMENTATION_MAPPING.md` is classified as `vision`.
   - It appears in SSOT Backlog docs browser.

4. Updated tests.
   - Added assertions that every organism layer has a valid implementation
     status and backlog refs.
   - Tests support both local `api.*` layout and production container layout.

## Live QA

Production VPS:
- Path: `/opt/ado`
- Commit: `cb78e88`
- API container: healthy
- Model lock: `migancore:0.7c`

Verified:
- `GET /health` returns healthy.
- `GET /v1/system/organism` returns 9 layers with `implementation_status`.
- `GET /v1/admin/docs?tab=vision` returns 200 and includes
  `ORGANISM_IMPLEMENTATION_MAPPING.md`.
- Container tests pass:

```text
tests/test_organism_architecture.py
tests/test_admin_docs.py
6 passed
```

## Current Mapping Summary

| Body Part | Status | Meaning |
|---|---|---|
| Jiwa | partial | Identity/creator bond live, organism identity eval still needed |
| Otak | partial | Brain/routing live, reasoning traces and Qwen3 eval still pending |
| Pikiran | partial | Reflection/proposals live, chat insight to proposal still pending |
| Akal | partial | Dev Organ gates live, cost/license/content gates pending |
| Syaraf | partial | Tool routing live, routing eval and A2A pending |
| Indera | partial | Vision/docs/inspiration live, video/audio perception incomplete |
| Organ | planned | Backlog exists, real Artifact/Image/Video/Tool modules not complete |
| Metabolisme | partial | Proposal training mode live, approved proposal to eval/training pending |
| Imun | partial | Safety gates exist, reusable gate library and RLS/PII hardening pending |

## Next Recommended Sprint

Build **Artifact Builder MVP** as the first real Organ.

Why:
- Low cost, no GPU.
- Directly improves chat output variety.
- Creates visible artifacts: HTML, markdown, JSON, report, slide, code preview.
- Forces Akal + Imun gates to become reusable before heavier Image/Video modules.

Minimum scope:
- `api/services/artifact_builder.py`
- Request schema for artifact type, prompt, format, constraints.
- Preview-only first.
- Save/export only after safe path + rollback metadata.
- Tests for schema, preview, rollback, and path boundary.

## SIDIX Mapping Follow-Up

Fahmi said SIDIX contains many metaphorical methods that may overlap with or
complement MiganCore. Next safe research task:

```text
Read SIDIX synthesis docs one by one -> create SIDIX_TO_MIGANCORE_METHOD_MAPPING.md
```

Goal:
- Identify which SIDIX methods are already represented in MiganCore.
- Identify which should become Jiwa/Otak/Pikiran/Akal/Syaraf/Indera/Organ/
  Metabolisme/Imun contracts.
- Avoid duplicate naming and make the two systems complement each other.
