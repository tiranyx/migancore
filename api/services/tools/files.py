"""File organ — read/write sandboxed workspace."""

import json
from pathlib import Path
from typing import Any

import structlog

from .base import ToolContext, ToolExecutionError

logger = structlog.get_logger()

WORKSPACE_DIR = Path("/app/workspace")


def _resolve_workspace_path(user_path: str) -> Path:
    """Resolve a user-provided path inside the workspace sandbox.

    Blocks path traversal attacks by ensuring the resolved path
    is still inside WORKSPACE_DIR.
    """
    # Strip leading slashes and '..' sequences as a first defence
    cleaned = user_path.lstrip("/").lstrip("\\")
    if ".." in cleaned:
        raise ToolExecutionError("Path traversal ('..') is not allowed")

    target = (WORKSPACE_DIR / cleaned).resolve()
    # Double-check it's still inside the sandbox
    try:
        target.relative_to(WORKSPACE_DIR.resolve())
    except ValueError:
        raise ToolExecutionError("Path escapes the workspace sandbox")
    return target


async def _read_file(args: dict, ctx: ToolContext) -> dict:
    """Read a file from /app/workspace/ sandbox."""
    path = args.get("path", "").strip()
    if not path:
        raise ToolExecutionError("'path' is required")

    target = _resolve_workspace_path(path)
    if not target.exists():
        raise ToolExecutionError(f"File not found: {path}")
    if not target.is_file():
        raise ToolExecutionError(f"Not a file: {path}")

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Try binary read and return base64 for non-text files
        import base64
        raw = target.read_bytes()
        content = base64.b64encode(raw).decode("ascii")
        return {"path": path, "content": content, "encoding": "base64", "size_bytes": len(raw)}

    logger.info("tool.read_file", path=path, chars=len(content))
    return {"path": path, "content": content, "encoding": "utf-8", "size_bytes": len(content.encode("utf-8"))}


async def _write_file(args: dict, ctx: ToolContext) -> dict:
    """Write a file to /app/workspace/ sandbox."""
    path = args.get("path", "").strip()
    content = args.get("content", "")
    append = bool(args.get("append", False))

    if not path:
        raise ToolExecutionError("'path' is required")

    target = _resolve_workspace_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    mode = "a" if append else "w"
    try:
        with target.open(mode, encoding="utf-8") as fh:
            fh.write(content)
        logger.info("tool.write_file", path=path, chars=len(content), append=append)
        return {"path": path, "status": "written", "size_bytes": len(content.encode("utf-8"))}
    except Exception as exc:
        raise ToolExecutionError(f"Write failed: {exc}") from exc


HANDLERS: dict[str, Any] = {
    "read_file": _read_file,
    "write_file": _write_file,
}
