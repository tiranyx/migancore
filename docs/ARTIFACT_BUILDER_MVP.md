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

## Save Path — Proposal-Gated (added 2026-05-15)

Two new endpoints close the preview → review → save loop without ever
auto-writing to workspace:

### `POST /v1/artifacts/submit`

Same request body as `/preview`. Builds the preview internally; if every
gate passes (`safe_to_save: true`), inserts a row in `dev_organ_proposals`
with:

- `source = "manual"`, `metadata.component = "artifact_builder"`
- `metadata.artifact_id`, `metadata.content`, `metadata.recommended_path`
- `gate_results` mirrored at proposal level for panel rendering

Idempotent on `artifact_id`: a re-submit of the same inputs returns the
existing pending proposal instead of duplicating.

Returns 400 if `safe_to_save` is false, with the failing gate list in
`detail.failed_gates`.

### `POST /v1/artifacts/finalize/{proposal_id}`

Body: `{ "verdict": "approved" | "rejected", "notes": "", "overwrite": false }`

- **approved** → re-validate `metadata.recommended_path` against workspace
  (defense in depth via `services.workspace_safety.resolve_workspace_target`),
  write `metadata.content` to that file, transition `stage = "deployed"`,
  record `metadata.saved_at` and `metadata.saved_path`.
- **rejected** → `stage = "blocked"`.
- Already-decided proposals (`stage in {"deployed", "blocked"}`) are
  idempotent — endpoint returns current state.
- Existing file at target rejects with 409 unless `overwrite: true`.
- Symlinks pointing outside workspace fail the resolver and return 400.

### Frontend (`backlog.html` → 📥 PROPOSAL tab)

If `metadata.component === "artifact_builder"`, the proposal card renders:

- Artifact-type pill + recommended-path code + SAFE/UNSAFE badge
- Collapsible content preview
- Three buttons: `APPROVE & SAVE`, `APPROVE (overwrite)`, `REJECT`
  — all call `/v1/artifacts/finalize/{id}` (not the generic verdict
  endpoint), so save happens atomically with verdict.

### Not Yet Implemented

- Artifact DB table (separate from proposals — currently content lives in
  `metadata` JSONB; fine up to ~50 KB which is also the preview cap).
- Inline artifact renderer in chat (open saved artifact from `saved_path`).
- PDF/slide export integration.
- LLM-backed content generation (preview is still a templated scaffold).
- Conversation-linked artifact recall.

Those belong to the next sprint after the save contract is stable.
