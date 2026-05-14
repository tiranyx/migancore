"""
Admin SSOT Docs Browser — Day 73 Sprint 1.5

Serves /opt/ado/docs/ as the canonical source of truth for vision, backlog,
journal, and lessons. NO duplicate DB; markdown files remain authoritative.

Tabs supported (classification by filename pattern):
  - vision     : SOUL, DIRECTION_LOCK, NORTHSTAR, THEOLOGY, PRD, ARCHITECTURE
  - backlog    : SPRINT_*, DAY*_PROGRESS, M*_PROGRESS, ROADMAP, BACKLOG_*, MODULE_*
  - journal    : *FOUNDER_JOURNAL*, *HANDOFF*, *DAILY*, AGENT_SYNC/*
  - lessons    : LESSONS_*, *MASTER*, *REVIEW*

Endpoints:
  GET  /v1/admin/docs                      — list all docs grouped by tab
  GET  /v1/admin/docs?tab=vision           — filter by tab
  GET  /v1/admin/docs/file?path={rel_path} — return raw markdown content
  GET  /v1/admin/docs/stats                — counts per tab + recent activity

Auth: X-Admin-Key required (matches existing admin router pattern).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    import structlog
except ModuleNotFoundError:  # Local docs tests may run without full API deps.
    import logging

    class _StructlogFallback:
        @staticmethod
        def get_logger(name: str):
            return logging.getLogger(name)

    structlog = _StructlogFallback()
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel

from config import settings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/v1/admin/docs", tags=["admin-docs"])

_DOCS_ROOT_CANDIDATES = (
    Path(os.getenv("ADMIN_DOCS_ROOT", "")).expanduser() if os.getenv("ADMIN_DOCS_ROOT") else None,
    Path("/app/docs"),
    Path("/opt/ado/docs"),
    Path(__file__).resolve().parents[2] / "docs",
)


def _docs_root() -> Path:
    """Return the first available docs root across local and VPS layouts."""
    for candidate in _DOCS_ROOT_CANDIDATES:
        if candidate and candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    configured = os.getenv("ADMIN_DOCS_ROOT", "/app/docs")
    return Path(configured).resolve()

# Tab classification rules — order matters (first match wins)
_TAB_RULES = [
    ("vision", [
        "01_SOUL.md", "02_VISION_NORTHSTAR", "MIGANCORE_DIRECTION_LOCK",
        "SELF_IMPROVEMENT_NORTHSTAR", "INNOVATION_ENGINE_DOCTRINE",
        "COGNITIVE_SYNTHESIS_DOCTRINE", "03_PRD", "ARCHITECTURE",
        "CONSTITUTION", "AGENT_ONBOARDING", "MANIFESTO",
        "BIOMIMETIC_GROWTH", "ADO_ENGINEERING_THEOLOGY",
        "PENCIPTA_BOND", "ADO_LEARNING_FACILITIES",
        "INGEST_PENCERNAAN", "VISION_PRINCIPLES_LOCKED",
        "ORGANISM_ARCHITECTURE", "ORGANISM_IMPLEMENTATION",
        "SIDIX_TO_MIGANCORE_METHOD_MAPPING",
        "ARTIFACT_BUILDER_MVP",
    ]),
    ("backlog", [
        "SPRINT_", "SPRINT2", "SPRINT3", "SPRINT4", "SPRINT5", "SPRINT6", "SPRINT7", "SPRINT8", "SPRINT9", "06_SPRINT_ROADMAP", "DAY",
        "_PROGRESS", "M15", "M16", "M17",
        "ROADMAP", "BACKLOG_ALIGNMENT", "MODULE_", "TOOL_MODULE",
        "GENERATOR", "ARTIFACT_BUILDER", "SPRINT_DAY",
        "STATUS_DAY", "BULAN", "CYCLE",
    ]),
    ("journal", [
        "FOUNDER_JOURNAL", "HANDOFF", "DAILY", "AGENT_SYNC",
        "DIRECTION_HANDOFF", "ALIGNMENT_CHECKPOINT", "SESSION",
    ]),
    ("lessons", [
        "LESSONS_", "MASTER", "REVIEW", "POSTMORTEM",
        "_ANALYSIS", "EVAL", "QA_", "RESEARCH",
    ]),
]


def _classify(name: str) -> str:
    upper = name.upper()
    for tab, patterns in _TAB_RULES:
        for pat in patterns:
            if pat.upper() in upper:
                return tab
    return "other"


def _require_admin(x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")) -> None:
    if not settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin endpoints not configured",
        )
    if not x_admin_key or x_admin_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
        )


class DocEntry(BaseModel):
    path: str           # relative to DOCS_ROOT
    name: str           # filename
    tab: str            # vision|backlog|journal|lessons|other
    size_bytes: int
    modified_at: float  # unix ts


class DocListResponse(BaseModel):
    total: int
    by_tab: dict[str, int]
    docs: list[DocEntry]


class DocContentResponse(BaseModel):
    path: str
    name: str
    tab: str
    size_bytes: int
    modified_at: float
    content: str


def _safe_resolve(rel_path: str) -> Path:
    """Resolve rel_path under DOCS_ROOT, reject traversal."""
    if not rel_path or ".." in rel_path:
        raise HTTPException(status_code=400, detail="Invalid path")
    root = _docs_root()
    full = (root / rel_path).resolve()
    if not str(full).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Path traversal denied")
    if not full.exists():
        raise HTTPException(status_code=404, detail=f"Not found: {rel_path}")
    if not full.is_file():
        raise HTTPException(status_code=400, detail="Not a file")
    return full


@router.get("", response_model=DocListResponse, dependencies=[Depends(_require_admin)])
async def list_docs(
    tab: Optional[str] = Query(None, regex="^(vision|backlog|journal|lessons|other)$"),
    limit: int = Query(500, le=2000),
    search: Optional[str] = Query(None, max_length=100),
):
    """List all .md docs, optionally filtered by tab and search query."""
    root = _docs_root()
    if not root.exists():
        raise HTTPException(status_code=500, detail=f"Docs root not found: {root}")

    by_tab: dict[str, int] = {}
    docs: list[DocEntry] = []
    s = (search or "").lower()

    for path in sorted(root.rglob("*.md")):
        try:
            st = path.stat()
        except OSError:
            continue
        rel = str(path.relative_to(root))
        name = path.name
        t = _classify(name)
        by_tab[t] = by_tab.get(t, 0) + 1
        if tab and t != tab:
            continue
        if s and s not in name.lower() and s not in rel.lower():
            continue
        docs.append(DocEntry(
            path=rel,
            name=name,
            tab=t,
            size_bytes=st.st_size,
            modified_at=st.st_mtime,
        ))
        if len(docs) >= limit:
            break

    # Sort by modified desc within result
    docs.sort(key=lambda d: -d.modified_at)
    return DocListResponse(total=len(docs), by_tab=by_tab, docs=docs)


@router.get("/file", response_model=DocContentResponse, dependencies=[Depends(_require_admin)])
async def get_doc(path: str = Query(..., min_length=1)):
    """Return raw markdown content of a doc."""
    full = _safe_resolve(path)
    try:
        text = full.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Read failed: {exc}")
    st = full.stat()
    return DocContentResponse(
        path=path,
        name=full.name,
        tab=_classify(full.name),
        size_bytes=st.st_size,
        modified_at=st.st_mtime,
        content=text,
    )


@router.get("/stats", dependencies=[Depends(_require_admin)])
async def stats():
    """Quick counts per tab + most-recent in each."""
    root = _docs_root()
    if not root.exists():
        raise HTTPException(status_code=500, detail=f"Docs root not found: {root}")

    by_tab: dict[str, int] = {}
    recent: dict[str, dict] = {}

    for path in root.rglob("*.md"):
        try:
            st = path.stat()
        except OSError:
            continue
        t = _classify(path.name)
        by_tab[t] = by_tab.get(t, 0) + 1
        prev = recent.get(t)
        if prev is None or st.st_mtime > prev["mtime"]:
            recent[t] = {
                "name": path.name,
                "path": str(path.relative_to(root)),
                "mtime": st.st_mtime,
            }
    total = sum(by_tab.values())
    return {
        "total": total,
        "docs_root": str(root),
        "by_tab": by_tab,
        "recent_per_tab": recent,
    }
