"""
Artifact Builder router.

MVP is preview-only: create structured artifact drafts with gates and lineage,
but do not write files or export to production.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from config import settings
from services.artifact_builder import ArtifactRequest, build_artifact_preview, preview_to_dict

router = APIRouter(prefix="/v1/artifacts", tags=["artifacts"])


def _require_admin(x_admin_key: str = Header(default="", alias="X-Admin-Key")) -> None:
    if not settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Admin not configured")
    if not secrets.compare_digest(x_admin_key or "", settings.ADMIN_SECRET_KEY):
        raise HTTPException(status_code=401, detail="Invalid admin key")


class ArtifactPreviewRequest(BaseModel):
    prompt: str = Field(..., min_length=4, max_length=5000)
    artifact_type: str = Field(default="markdown", max_length=32)
    title: str = Field(default="", max_length=120)
    constraints: list[str] = Field(default_factory=list, max_length=12)
    target_path: str = Field(default="", max_length=180)


@router.post("/preview")
async def preview_artifact(
    body: ArtifactPreviewRequest,
    _: None = Depends(_require_admin),
):
    """Build a preview-only artifact with gates, lineage, and safe save hint."""
    try:
        preview = build_artifact_preview(
            ArtifactRequest(
                prompt=body.prompt,
                artifact_type=body.artifact_type,  # type: ignore[arg-type]
                title=body.title,
                constraints=body.constraints,
                target_path=body.target_path,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return preview_to_dict(preview)
