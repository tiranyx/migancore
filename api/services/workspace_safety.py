"""Workspace path safety primitives.

Used by routers/artifacts.py (and any future save layer) to enforce that
a user-supplied save path stays inside settings.WORKSPACE_DIR after
symlink resolution. Kept dependency-light so tests can run without the
full FastAPI/SQLAlchemy stack.

Mirrors the contract of tool_executor._resolve_workspace_path but with
HTTP-style exceptions and additional defenses (tilde prefix, empty path).
"""

from __future__ import annotations

from pathlib import Path


class WorkspaceSafetyError(ValueError):
    """Raised when a path cannot be resolved safely inside the workspace.

    Callers (typically a FastAPI route) translate this to HTTP 400.
    """


def resolve_workspace_target(workspace_dir: str, rel_path: str) -> Path:
    """Resolve `rel_path` against `workspace_dir`. Reject any escape.

    Defenses applied (in order):
      1. Empty/whitespace/root sentinels rejected
      2. Tilde prefix rejected (no home expansion ever)
      3. Backslashes normalized to forward slashes
      4. Leading slashes / dots stripped to force relative
      5. Resolved path must be inside resolved workspace (catches symlinks
         that point outside)

    Raises WorkspaceSafetyError with a human-readable reason on any failure.
    """
    if rel_path is None:
        raise WorkspaceSafetyError("path is required")

    stripped = rel_path.strip()
    if not stripped or stripped in ("/", ".", "./", "//"):
        raise WorkspaceSafetyError("path missing or resolves to workspace root")

    if stripped.startswith("~"):
        raise WorkspaceSafetyError("path must not start with '~'")

    workspace = Path(workspace_dir).resolve()
    clean = stripped.replace("\\", "/").lstrip("/").lstrip(".")
    if not clean:
        raise WorkspaceSafetyError("path resolves to workspace root")

    target = (workspace / clean).resolve()
    try:
        target.relative_to(workspace)
    except ValueError as exc:
        raise WorkspaceSafetyError("path escapes workspace") from exc

    return target
