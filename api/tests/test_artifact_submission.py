"""Pure-function tests for artifact submission payload synthesis.

The router-side tests (submit/finalize over DB) live separately; this file
covers the synthesizer in isolation so it can run without a DB or workspace.
"""

try:
    from api.services.artifact_builder import ArtifactRequest, build_artifact_preview
    from api.services.artifact_submission import synthesize_artifact_submission
except ModuleNotFoundError:  # Docker image copies api/ contents to /app.
    from services.artifact_builder import ArtifactRequest, build_artifact_preview
    from services.artifact_submission import synthesize_artifact_submission


def _ok_preview():
    return build_artifact_preview(
        ArtifactRequest(
            prompt="Buat ringkasan tata bahasa Indonesia singkat",
            artifact_type="markdown",
            title="Ringkasan Tata Bahasa",
            constraints=["preview-only"],
        )
    )


def test_synthesize_carries_artifact_id_and_safe_to_save_into_metadata():
    preview = _ok_preview()
    payload = synthesize_artifact_submission(preview)

    meta = payload["metadata"]
    assert meta["component"] == "artifact_builder"
    assert meta["artifact_id"] == preview.artifact_id
    assert meta["safe_to_save"] is True
    assert meta["recommended_path"].endswith(".md")
    assert meta["content"] == preview.content
    # Gates are also flattened into metadata so frontend can render them
    # without a join.
    assert any(g["name"] == "path_boundary" for g in meta["gates"])


def test_payload_touched_paths_use_workspace_prefix():
    preview = _ok_preview()
    payload = synthesize_artifact_submission(preview)
    assert payload["touched_paths"], "touched_paths must list the future save target"
    assert all(p.startswith("workspace/") for p in payload["touched_paths"])


def test_payload_source_is_manual_with_component_discriminator():
    """source must satisfy the existing ProposalCreate regex; component goes
    into metadata so we don't have to alter the SQL CHECK constraint."""
    payload = synthesize_artifact_submission(_ok_preview())
    assert payload["source"] in {
        "auto", "owner_command", "tool_failure", "eval_failure", "manual",
    }
    assert payload["metadata"]["component"] == "artifact_builder"


def test_synthesize_records_failed_gates_honestly():
    """If preview gates fail (e.g., traversal), metadata.safe_to_save must
    reflect that so finalize() can reject before writing."""
    bad_preview = build_artifact_preview(
        ArtifactRequest(
            prompt="probe traversal",
            artifact_type="markdown",
            target_path="../escape.md",
        )
    )
    payload = synthesize_artifact_submission(bad_preview)
    assert payload["metadata"]["safe_to_save"] is False
    bad_gates = [g for g in payload["metadata"]["gates"] if not g["passed"]]
    assert any(g["name"] == "path_boundary" for g in bad_gates)
