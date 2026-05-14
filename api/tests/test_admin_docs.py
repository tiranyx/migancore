from pathlib import Path

try:
    from api.routers import admin_docs
except ModuleNotFoundError:  # Docker image copies api/ contents to /app.
    from routers import admin_docs


def test_docs_root_uses_first_existing_candidate(tmp_path, monkeypatch):
    missing = tmp_path / "missing"
    existing = tmp_path / "docs"
    existing.mkdir()

    monkeypatch.setattr(admin_docs, "_DOCS_ROOT_CANDIDATES", (missing, existing))

    assert admin_docs._docs_root() == existing.resolve()


def test_module_docs_classify_as_backlog():
    assert admin_docs._classify("MODULE_GENERATORS_BACKLOG.md") == "backlog"
    assert admin_docs._classify("TOOL_MODULE_IMAGE_GENERATOR.md") == "backlog"


def test_organism_architecture_classifies_as_vision():
    assert admin_docs._classify("ORGANISM_ARCHITECTURE_BLUEPRINT.md") == "vision"
    assert admin_docs._classify("ORGANISM_IMPLEMENTATION_MAPPING.md") == "vision"
    assert admin_docs._classify("SIDIX_TO_MIGANCORE_METHOD_MAPPING.md") == "vision"
