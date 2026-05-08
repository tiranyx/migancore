"""
Hafidz Ledger Router — SP-007

Knowledge return endpoints: "Anak Kembali ke Induk".
Child ADO instances submit anonymized domain knowledge back to the parent.

Endpoints:
  POST /v1/hafidz/contributions          → Child: submit a contribution
  GET  /v1/hafidz/contributions          → Parent admin: list contributions
  GET  /v1/hafidz/contributions/{id}     → Parent admin: get single
  POST /v1/hafidz/contributions/{id}/review → Parent admin: approve / reject
"""

from __future__ import annotations

import os
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from deps.db import get_db
from schemas.hafidz import (
    ContributionCreate,
    ContributionListResponse,
    ContributionResponse,
    ContributionReview,
)
from services.hafidz import (
    create_contribution,
    get_contribution,
    list_contributions,
    review_contribution,
)
from services.ingestion import incorporate_contribution
from services.ingestion_worker import enqueue_contribution

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/hafidz", tags=["hafidz"])


# ─────────────────────────────────────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────────────────────────────────────

def _require_admin(x_admin_key: Optional[str] = Header(None, alias="x-admin-key")) -> None:
    """Require X-Admin-Key header matching ADMIN_SECRET_KEY env var."""
    from config import settings
    admin_key = getattr(settings, "ADMIN_SECRET_KEY", "")
    if not admin_key or x_admin_key != admin_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC — Child ADO submits contribution
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/contributions", status_code=status.HTTP_201_CREATED)
async def submit_contribution(
    req: ContributionCreate,
    db: AsyncSession = Depends(get_db),
) -> ContributionResponse:
    """
    Submit a knowledge contribution from a child ADO to its parent.

    This endpoint is called by child ADO instances when:
      - License is about to expire (knowledge return triggered)
      - User explicitly opts in to contribute
      - Auto-contribute is enabled for the license tier

    The contribution is deduplicated by SHA-256 hash. If the same hash
    has been submitted before, a 409 Conflict is returned.

    The payload is anonymized — PII must be stripped by the child
    before submission. The parent stores only patterns, not identities.
    """
    try:
        contrib = await create_contribution(
            session=db,
            child_license_id=req.child_license_id,
            child_display_name=req.child_display_name,
            child_tier=req.child_tier,
            parent_version=req.parent_version,
            contribution_type=req.contribution_type,
            contribution_hash=req.contribution_hash,
            anonymized_payload=req.anonymized_payload,
        )
    except ValueError as exc:
        if "already exists" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # SP-009: Auto-enqueue for ingestion pipeline
    await enqueue_contribution(contrib.id)

    logger.info(
        "hafidz.submitted",
        license_id=req.child_license_id,
        hash=req.contribution_hash,
        type=req.contribution_type,
    )
    return ContributionResponse.model_validate(contrib)


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — Parent reviews contributions
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/contributions", dependencies=[Depends(_require_admin)])
async def get_contributions(
    status: Optional[str] = Query(None, description="Filter by status: pending | reviewing | incorporated | rejected"),
    contribution_type: Optional[str] = Query(None, description="Filter by type: dpo_pair | tool_pattern | domain_cluster | voice_pattern"),
    child_license_id: Optional[str] = Query(None, description="Filter by child license ID"),
    parent_version: Optional[str] = Query(None, description="Filter by parent version"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> ContributionListResponse:
    """
    List all knowledge contributions — parent admin only.

    Supports filtering by status, type, child license, and parent version.
    Ordered by received_at DESC (newest first).
    """
    items, total = await list_contributions(
        session=db,
        status=status,
        contribution_type=contribution_type,
        child_license_id=child_license_id,
        parent_version=parent_version,
        page=page,
        page_size=page_size,
    )

    return ContributionListResponse(
        items=[ContributionResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/contributions/{contribution_id}", dependencies=[Depends(_require_admin)])
async def get_contribution_detail(
    contribution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ContributionResponse:
    """Get a single contribution by ID — parent admin only."""
    contrib = await get_contribution(session=db, contribution_id=contribution_id)
    if contrib is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contribution not found",
        )
    return ContributionResponse.model_validate(contrib)


@router.post("/contributions/{contribution_id}/review", dependencies=[Depends(_require_admin)])
async def review_contribution_endpoint(
    contribution_id: uuid.UUID,
    req: ContributionReview,
    db: AsyncSession = Depends(get_db),
) -> ContributionResponse:
    """
    Review a contribution: approve (incorporate) or reject.

    **Approve** → status becomes "incorporated", training pipeline can pick it up.
    **Reject** → status becomes "rejected", optional reason recorded.

    Only contributions with status "pending" can be reviewed.
    """
    try:
        contrib = await review_contribution(
            session=db,
            contribution_id=contribution_id,
            action=req.action,
            quality_score=req.quality_score,
            reject_reason=req.reject_reason,
            incorporated_cycle=req.incorporated_cycle,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    logger.info(
        "hafidz.reviewed",
        id=str(contribution_id),
        action=req.action,
        quality_score=req.quality_score,
    )
    return ContributionResponse.model_validate(contrib)


# ─────────────────────────────────────────────────────────────────────────────
# INGESTION PIPELINE — SP-009
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/contributions/{contribution_id}/ingest", dependencies=[Depends(_require_admin)])
async def ingest_contribution_endpoint(
    contribution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Manually trigger ingestion for a contribution.

    Runs quality scoring + auto-incorporate logic synchronously.
    Returns decision, quality_score, and optional training pair_id.
    """
    try:
        result = await incorporate_contribution(db, contribution_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return {
        "contribution_id": str(result["contribution_id"]),
        "quality_score": result["quality_score"],
        "decision": result["decision"],
        "pair_id": str(result["pair_id"]) if result["pair_id"] else None,
    }


@router.get("/queue/status", dependencies=[Depends(_require_admin)])
async def queue_status() -> dict:
    """Return ingestion queue status (Redis-backed)."""
    try:
        import redis.asyncio as aioredis
        from config import settings
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        queue_len = await r.llen("migancore:ingestion:queue")
        await r.aclose()
        return {
            "queue_key": "migancore:ingestion:queue",
            "pending_items": queue_len,
            "worker_running": True,  # Simplified — actual state tracked in worker module
        }
    except Exception as exc:
        return {
            "queue_key": "migancore:ingestion:queue",
            "pending_items": None,
            "worker_running": False,
            "error": str(exc),
        }
