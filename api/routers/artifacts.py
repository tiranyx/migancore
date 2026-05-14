"""
Artifact Builder router.

Three endpoints:
  POST /v1/artifacts/preview          — preview-only, no DB write, no file
  POST /v1/artifacts/submit           — preview + write proposal row (pending)
  POST /v1/artifacts/finalize/{id}    — creator approve/reject; on approve,
                                        write file to workspace and flip stage
                                        to deployed. Reject → stage=blocked.

The save layer never bypasses the proposal queue. Aligned with Codex Day 73
audit + biomimetic growth doctrine: chat → preview → gate → review → save.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from deps.db import get_db
from models.proposal import DevOrganProposal
from services.artifact_builder import (
    ArtifactRequest,
    build_artifact_preview,
    preview_to_dict,
)
from services.artifact_submission import synthesize_artifact_submission
from services.dev_organ import classify_risk
from services.workspace_safety import WorkspaceSafetyError, resolve_workspace_target

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/artifacts", tags=["artifacts"])


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _require_admin(x_admin_key: str = Header(default="", alias="X-Admin-Key")) -> None:
    if not settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Admin not configured")
    if not secrets.compare_digest(x_admin_key or "", settings.ADMIN_SECRET_KEY):
        raise HTTPException(status_code=401, detail="Invalid admin key")


# ---------------------------------------------------------------------------
# Path safety (mirrors tool_executor._resolve_workspace_path; kept local so
# routers/artifacts.py has zero coupling to the chat tool surface)
# ---------------------------------------------------------------------------

def _resolve_workspace_target(rel_path: str) -> Path:
    """HTTP-facing wrapper around services.workspace_safety.

    Save-time defense in depth: the preview gate already vetted the path,
    but metadata could in principle be edited out of band, so we re-validate.
    """
    try:
        return resolve_workspace_target(settings.WORKSPACE_DIR, rel_path)
    except WorkspaceSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ArtifactPreviewRequest(BaseModel):
    prompt: str = Field(..., min_length=4, max_length=5000)
    artifact_type: str = Field(default="markdown", max_length=32)
    title: str = Field(default="", max_length=120)
    constraints: list[str] = Field(default_factory=list, max_length=12)
    target_path: str = Field(default="", max_length=180)


class ArtifactFinalizeRequest(BaseModel):
    verdict: str = Field(..., pattern="^(approved|rejected)$")
    notes: str = Field(default="", max_length=2000)
    overwrite: bool = Field(default=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_request(body: ArtifactPreviewRequest) -> ArtifactRequest:
    return ArtifactRequest(
        prompt=body.prompt,
        artifact_type=body.artifact_type,  # type: ignore[arg-type]
        title=body.title,
        constraints=body.constraints,
        target_path=body.target_path,
    )


def _failed_gates(preview) -> list[dict[str, Any]]:
    return [
        {"name": g.name, "detail": g.detail}
        for g in preview.gates
        if not g.passed
    ]


# ---------------------------------------------------------------------------
# 1. Preview — no DB write, no file write
# ---------------------------------------------------------------------------

@router.post("/preview")
async def preview_artifact(
    body: ArtifactPreviewRequest,
    _: None = Depends(_require_admin),
):
    """Build a preview-only artifact with gates, lineage, and safe save hint."""
    try:
        preview = build_artifact_preview(_build_request(body))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return preview_to_dict(preview)


# ---------------------------------------------------------------------------
# 2. Submit — preview + insert proposal (pending creator review)
# ---------------------------------------------------------------------------

@router.post("/submit")
async def submit_artifact(
    body: ArtifactPreviewRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    """Build preview, then queue a proposal for creator review.

    Idempotent on artifact_id: if a pending proposal already exists for the
    same artifact (same hash of inputs), returns it instead of duplicating.
    Returns 400 if preview gates fail (e.g. path traversal).
    """
    try:
        preview = build_artifact_preview(_build_request(body))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not preview.safe_to_save:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "preview is not safe to save; fix the gate failures",
                "failed_gates": _failed_gates(preview),
                "artifact_id": preview.artifact_id,
            },
        )

    # Dedupe — pending proposal with same artifact_id
    existing = (await db.execute(
        select(DevOrganProposal)
        .where(DevOrganProposal.creator_verdict.is_(None))
        .where(DevOrganProposal.stage == "proposed")
        .order_by(DevOrganProposal.created_at.desc())
        .limit(50)
    )).scalars().all()
    for p in existing:
        meta = p.metadata_ or {}
        if (meta.get("component") == "artifact_builder"
                and meta.get("artifact_id") == preview.artifact_id):
            logger.info(
                "artifact.submit.dedupe",
                proposal_id=str(p.id),
                artifact_id=preview.artifact_id,
            )
            return {
                "status": "dedup_existing",
                "proposal": p.to_dict(),
                "artifact_id": preview.artifact_id,
            }

    payload = synthesize_artifact_submission(preview)
    risk = classify_risk(payload["touched_paths"]).value
    row = DevOrganProposal(
        title=payload["title"],
        problem=payload["problem"],
        hypothesis=payload["hypothesis"],
        touched_paths=payload["touched_paths"],
        tests=payload["tests"],
        rollback_plan=payload["rollback_plan"],
        source=payload["source"],
        risk_level=risk,
        stage="proposed",
        gate_results=payload["metadata"]["gates"],
        metadata_=payload["metadata"],
        created_by=payload["created_by"],
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    logger.info(
        "artifact.submit.created",
        proposal_id=str(row.id),
        artifact_id=preview.artifact_id,
        artifact_type=preview.artifact_type,
        path=preview.recommended_path,
    )
    return {
        "status": "submitted",
        "proposal": row.to_dict(),
        "artifact_id": preview.artifact_id,
    }


# ---------------------------------------------------------------------------
# 3. Finalize — creator approve/reject; on approve, write file
# ---------------------------------------------------------------------------

@router.post("/finalize/{proposal_id}")
async def finalize_artifact(
    proposal_id: uuid.UUID,
    body: ArtifactFinalizeRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    """Approve or reject an artifact proposal.

    Approve → re-validate gates, write content to workspace, transition
    stage='deployed'. Reject → stage='blocked'. Idempotent on already-decided
    proposals (returns current state). Rejects overwrite-existing-file
    unless body.overwrite is true.
    """
    proposal = await db.get(DevOrganProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="proposal not found")

    meta = proposal.metadata_ or {}
    if meta.get("component") != "artifact_builder":
        raise HTTPException(
            status_code=400,
            detail="proposal is not an artifact_builder submission",
        )

    # Idempotent terminal states
    if proposal.stage in ("deployed", "blocked"):
        return {
            "status": "idempotent",
            "stage": proposal.stage,
            "proposal": proposal.to_dict(),
        }

    now = datetime.now(timezone.utc)

    if body.verdict == "rejected":
        proposal.creator_verdict = "rejected"
        proposal.creator_notes = body.notes or None
        proposal.decided_at = now
        proposal.stage = "blocked"
        await db.commit()
        await db.refresh(proposal)
        logger.info("artifact.finalize.rejected", proposal_id=str(proposal_id))
        return {"status": "rejected", "proposal": proposal.to_dict()}

    # Approved: re-validate + write
    rel_path = meta.get("recommended_path") or ""
    content = meta.get("content") or ""
    if not isinstance(content, str):
        raise HTTPException(status_code=400, detail="metadata.content invalid")
    if not meta.get("safe_to_save", False):
        raise HTTPException(
            status_code=400,
            detail="metadata.safe_to_save is false; resubmit a fresh preview",
        )

    target = _resolve_workspace_target(rel_path)

    if target.exists() and not body.overwrite:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "file already exists; resend with overwrite=true to replace",
                "path": str(target),
            },
        )

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        logger.warning("artifact.finalize.write_failed", error=str(exc)[:200])
        raise HTTPException(
            status_code=500,
            detail=f"workspace write failed: {exc}",
        ) from exc

    # Mutate proposal — verdict + stage + metadata save record
    proposal.creator_verdict = "approved"
    proposal.creator_notes = body.notes or None
    proposal.decided_at = now
    proposal.stage = "deployed"
    updated_meta = dict(meta)
    updated_meta["saved_at"] = now.isoformat()
    updated_meta["saved_path"] = str(target)
    updated_meta["saved_overwrite"] = bool(body.overwrite and target.exists())
    proposal.metadata_ = updated_meta
    await db.commit()
    await db.refresh(proposal)

    logger.info(
        "artifact.finalize.saved",
        proposal_id=str(proposal_id),
        path=str(target),
        bytes=len(content),
        overwrite=body.overwrite,
    )
    return {
        "status": "approved_and_saved",
        "path": str(target),
        "bytes_written": len(content),
        "proposal": proposal.to_dict(),
    }
