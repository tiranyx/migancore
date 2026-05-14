"""
Artifact Submission — turn an Artifact Builder preview into a proposal-ready
payload so it can land in the sandbox queue for Fahmi review.

The artifact content lives inside the proposal's metadata JSONB. No file is
written here; finalize() in routers/artifacts.py does the actual workspace
write only after creator approval.

Aligned with:
  - artifact_builder.py preview gates (path_boundary, prompt_bounds, …)
  - inspiration_intake.py payload shape (so panel renders both consistently)
  - biomimetic doctrine: preview → propose → gate → review → save
"""

from __future__ import annotations

from typing import Any

from services.artifact_builder import ArtifactPreview, preview_to_dict


# Tests we suggest the operator run before promoting an artifact save. Kept
# simple — the path/content checks already happened at preview time.
_DEFAULT_TESTS: list[str] = [
    "python -m pytest tests/test_artifact_builder.py -q",
]


def synthesize_artifact_submission(preview: ArtifactPreview) -> dict[str, Any]:
    """Build a sandbox-proposal payload from a passing preview.

    Caller is expected to check `preview.safe_to_save` first — this function
    will still synthesize a payload either way (so audit trails for rejected
    previews are possible), but the metadata records the gate state honestly.
    """
    preview_dict = preview_to_dict(preview)
    fmt = preview.format
    title = preview.title or "Untitled artifact"
    type_label = preview.artifact_type
    target_path = preview.recommended_path

    problem = (
        f"Fahmi asked Migan to create a {type_label} artifact titled "
        f'"{title}". Preview-only build is ready; the file should not be '
        "saved to workspace until the creator approves it here."
    )
    hypothesis = (
        f"If approved, save the {type_label} preview to "
        f"`workspace/{target_path}` ({fmt}, "
        f"{len(preview.content)} chars). Rollback = delete that file; the "
        "preview lineage stays in this proposal log for audit."
    )

    # gate_results are recorded both at proposal level (DB column) and inside
    # metadata, so frontend can render them without joining tables.
    gate_dicts = [
        {"name": g.name, "passed": g.passed, "detail": g.detail}
        for g in preview.gates
    ]

    metadata = {
        "component": "artifact_builder",
        "intake_type": "artifact_save",
        "artifact_id": preview.artifact_id,
        "artifact_type": preview.artifact_type,
        "format": preview.format,
        "title": preview.title,
        "recommended_path": preview.recommended_path,
        "safe_to_save": preview.safe_to_save,
        "content": preview.content,
        "content_preview": preview.content_preview,
        "gates": gate_dicts,
        "lineage": preview.lineage,
        "preview_snapshot": preview_dict,
    }

    return {
        "title": f"Artifact save: {title}",
        "problem": problem,
        "hypothesis": hypothesis,
        "touched_paths": [f"workspace/{target_path}"],
        "tests": _DEFAULT_TESTS,
        "rollback_plan": (
            f"Delete workspace/{target_path}. The proposal metadata retains "
            "the preview content for re-creation if needed."
        ),
        # Must satisfy ProposalCreate regex: source ∈ {auto, owner_command, …}.
        # We use "manual" + metadata.component to stay schema-compatible with
        # auto_train_watchdog's discrimination pattern.
        "source": "manual",
        "created_by": "artifact_builder",
        "metadata": metadata,
    }
