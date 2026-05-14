from services.inspiration_intake import synthesize_inspiration


def test_synthesize_ltx_video_inspiration():
    payload = synthesize_inspiration(
        url="https://github.com/Lightricks/LTX-2",
        notes="audio-video generative model with multiple video pipelines",
    )

    assert payload["title"] == "Inspiration: Video Generator module from LTX-2"
    assert payload["source"] == "owner_command"
    assert payload["created_by"] == "inspiration_intake"
    assert payload["metadata"]["module_type"] == "video_generator"
    assert "gpu_budget_check" in payload["metadata"]["suggested_gates"]
    assert "docs/MODULE_GENERATORS_BACKLOG.md" in payload["touched_paths"]


def test_synthesize_artifact_builder_inspiration():
    payload = synthesize_inspiration(
        url="",
        notes="Migan should build reusable artifacts like HTML, docs, JSON configs, and eval packs.",
    )

    assert payload["metadata"]["module_type"] == "artifact_builder"
    assert "preview_render" in payload["metadata"]["suggested_gates"]
    assert "Artifact Builder" in payload["hypothesis"]


def test_synthesize_generic_tool_builder_inspiration():
    payload = synthesize_inspiration(
        url="https://example.com/tool-pattern",
        notes="A reusable tool with schema and sandbox execution.",
    )

    assert payload["metadata"]["module_type"] == "tool_builder"
    assert "contract_check" in payload["metadata"]["suggested_gates"]
