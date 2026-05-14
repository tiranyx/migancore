# Artifact Builder MVP

Date: 2026-05-15
Status: Live MVP, preview-only
Owner: Fahmi + MiganCore

## Purpose

Artifact Builder is the first real **Organ** in the MiganCore organism map. It
turns an intent into a structured artifact preview with gates and lineage.

This MVP is deliberately conservative:

```text
Prompt -> structured preview -> gates -> recommended path
```

It does **not** write files, export PDFs, run code, deploy apps, or spend GPU.

## Endpoint

```text
POST /v1/artifacts/preview
Auth: X-Admin-Key
```

Request:

```json
{
  "prompt": "Buat report QA live server",
  "artifact_type": "report",
  "title": "QA Report",
  "constraints": ["Bahasa Indonesia", "preview-only"],
  "target_path": "artifacts/qa-report.md"
}
```

Supported types:
- `markdown`
- `html`
- `json`
- `report`
- `code`

Response includes:
- `artifact_id`
- `artifact_type`
- `content`
- `content_preview`
- `gates`
- `lineage`
- `rollback_plan`
- `safe_to_save`
- `recommended_path`

## Gates

The MVP runs these preview gates:

| Gate | Purpose |
|---|---|
| `schema_check` | Request parsed and normalized |
| `prompt_bounds` | Prompt is not empty or too large |
| `preview_render` | Preview can be rendered within safe size |
| `path_boundary` | Future save path stays workspace-relative |
| `rollback_ready` | No production write happened |

## SIDIX Method Adopted

This implements the safe beginning of **Kitabah Auto-Iterate**:

```text
write/draft -> preview -> review -> iterate -> only then save/export
```

MiganCore adaptation:
- Preview first.
- Gates are explicit.
- Lineage is recorded.
- Save/export is a later step, not automatic.

## What This Unlocks Next

1. Chat can ask for artifact previews instead of only text answers.
2. Approved previews can later become workspace files.
3. HTML/report/code artifacts can get render/eval tests.
4. Strong artifacts can become training/eval examples.

## Not Yet Implemented

- Artifact DB table.
- Inline artifact renderer in chat.
- Save/export endpoint.
- PDF/slide export integration.
- LLM-backed content generation.
- Conversation-linked artifact recall.

Those belong to the next sprint after the preview contract is stable.
