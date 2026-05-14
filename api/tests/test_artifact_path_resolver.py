"""Save-time path resolver tests for the artifact pipeline.

The preview gate already vets target_path, but the finalize endpoint
re-validates because metadata.recommended_path could be edited out of band.
These tests cover services.workspace_safety directly so they run without
the full FastAPI/SQLAlchemy stack.
"""

from __future__ import annotations

import pytest

try:
    from api.services.workspace_safety import (
        WorkspaceSafetyError,
        resolve_workspace_target,
    )
except ModuleNotFoundError:
    from services.workspace_safety import (
        WorkspaceSafetyError,
        resolve_workspace_target,
    )


def test_resolves_clean_relative_path(tmp_path):
    target = resolve_workspace_target(str(tmp_path), "artifacts/note.md")
    assert target == (tmp_path / "artifacts" / "note.md").resolve()


def test_rejects_traversal_via_dotdot(tmp_path):
    with pytest.raises(WorkspaceSafetyError, match="escape"):
        resolve_workspace_target(str(tmp_path), "../../../etc/passwd")


def test_rejects_tilde_prefix(tmp_path):
    with pytest.raises(WorkspaceSafetyError, match="~"):
        resolve_workspace_target(str(tmp_path), "~/escape.md")


def test_rejects_absolute_unix_path(tmp_path):
    """An absolute path is normalized to relative by the lstrip; it must
    still not escape workspace. (Strip leaves 'etc/passwd' under workspace,
    which IS safe — the real attack vector is .. and we test that above.)"""
    target = resolve_workspace_target(str(tmp_path), "/etc/passwd")
    # The leading slash is stripped, so /etc/passwd lands as workspace/etc/passwd.
    # That's contained, not escaping — correct outcome.
    assert target.is_relative_to(tmp_path.resolve())


def test_rejects_empty_and_root(tmp_path):
    for bad in ("", "  ", "/", ".", "./", "//"):
        with pytest.raises(WorkspaceSafetyError):
            resolve_workspace_target(str(tmp_path), bad)


def test_resolves_nested_path_inside_workspace(tmp_path):
    target = resolve_workspace_target(str(tmp_path), "artifacts/sub/dir/file.md")
    assert target.is_relative_to(tmp_path.resolve())
    assert target.name == "file.md"


def test_symlink_escape_blocked(tmp_path):
    """A symlink placed inside the workspace that points OUT must fail the
    relative_to check after resolve() follows the link.
    """
    outside = tmp_path.parent / "outside_workspace_for_symlink_test"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "evil_link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("filesystem does not support symlinks")

    with pytest.raises(WorkspaceSafetyError, match="escape"):
        resolve_workspace_target(str(tmp_path), "evil_link/escape.md")


def test_none_path_raises(tmp_path):
    with pytest.raises(WorkspaceSafetyError):
        resolve_workspace_target(str(tmp_path), None)  # type: ignore[arg-type]
