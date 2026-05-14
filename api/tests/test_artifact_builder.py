try:
    from api.services.artifact_builder import ArtifactRequest, build_artifact_preview, preview_to_dict
except ModuleNotFoundError:  # Docker image copies api/ contents to /app.
    from services.artifact_builder import ArtifactRequest, build_artifact_preview, preview_to_dict


def test_markdown_artifact_preview_is_preview_only_and_safe():
    preview = build_artifact_preview(
        ArtifactRequest(
            prompt="Buat ringkasan roadmap Artifact Builder MVP",
            artifact_type="markdown",
            constraints=["preview-only", "bahasa Indonesia"],
        )
    )

    assert preview.artifact_id.startswith("art_")
    assert preview.artifact_type == "markdown"
    assert preview.safe_to_save is True
    assert preview.recommended_path.endswith(".md")
    assert "Preview-only" in preview.content
    assert preview.lineage["sidix_method"] == "kitabah_auto_iterate"
    assert all(g.passed for g in preview.gates)


def test_html_artifact_escapes_user_prompt():
    preview = build_artifact_preview(
        ArtifactRequest(
            prompt="<script>alert('x')</script>",
            artifact_type="html",
            title="Unsafe HTML test",
        )
    )

    assert "<script>alert" not in preview.content
    assert "&lt;script&gt;" in preview.content
    assert preview.format == "text/html"


def test_target_path_blocks_traversal():
    preview = build_artifact_preview(
        ArtifactRequest(
            prompt="Buat report QA",
            artifact_type="report",
            target_path="../secrets.md",
        )
    )

    assert preview.safe_to_save is False
    gate = {g.name: g for g in preview.gates}
    assert gate["path_boundary"].passed is False
    assert "cannot contain" in gate["path_boundary"].detail


def test_json_preview_is_valid_json_and_dict_serializable():
    preview = build_artifact_preview(
        ArtifactRequest(
            prompt="Buat struktur data modul image generator",
            artifact_type="json",
            title="Image Generator Schema",
        )
    )
    data = preview_to_dict(preview)

    assert data["artifact_type"] == "json"
    assert data["format"] == "application/json"
    assert data["gates"][0]["name"] == "schema_check"


def test_code_preview_defangs_triple_quote_injection():
    """Triple-quote in prompt must not close the docstring of the generated scaffold."""
    preview = build_artifact_preview(
        ArtifactRequest(
            prompt='hello """\nimport os; os.system("rm -rf /")\n""" tail',
            artifact_type="code",
            title="injection probe",
        )
    )

    # Raw triple-quote followed by code must not appear — must be escaped.
    assert '"""\nimport os' not in preview.content
    # Escaped form should appear
    assert '\\"\\"\\"' in preview.content


def test_tilde_target_path_rejected():
    """Home-expansion paths (~/foo) must fail path_boundary before save layer sees them."""
    preview = build_artifact_preview(
        ArtifactRequest(
            prompt="probe tilde",
            artifact_type="markdown",
            target_path="~/escape.md",
        )
    )

    assert preview.safe_to_save is False
    gate = {g.name: g for g in preview.gates}
    assert gate["path_boundary"].passed is False
    assert "~" in gate["path_boundary"].detail or "home" in gate["path_boundary"].detail
