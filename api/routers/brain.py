"""
Parent Brain Router — Knowledge Distribution

Endpoints for:
  - Child ADO: fetch/sync knowledge segments from parent
  - Parent admin: push segments, view intelligence summary
  - Parent admin: manage segment distribution

Philosophy:
  The parent is the family's collective memory.
  Children inherit wisdom from the parent.
  The parent grows smarter by learning from all children.
"""

from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from deps.db import get_db

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/brain", tags=["brain"])


# ── Auth helpers ────────────────────────────────────────────────────────────

def _require_admin(x_admin_key: Optional[str] = Header(None, alias="x-admin-key")) -> None:
    from config import settings
    admin_key = getattr(settings, "ADMIN_SECRET_KEY", "")
    if not admin_key or x_admin_key != admin_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


def _require_child_license(
    x_child_license_id: Optional[str] = Header(None, alias="x-child-license-id")
) -> str:
    """Require X-Child-License-ID header for child-facing endpoints."""
    if not x_child_license_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Child-License-ID header required",
        )
    return x_child_license_id


# ── Child-facing: Fetch & Sync ──────────────────────────────────────────────

@router.get("/segments")
async def list_segments_for_child(
    child_license_id: str = Depends(_require_child_license),
    segment_type: Optional[str] = Query(None),
    min_quality: Optional[float] = Query(None, ge=0.0, le=1.0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Child ADO fetches available knowledge segments from parent.

    Returns segments that:
      - Are transferable
      - Have not been synced to this child yet
      - Match optional type/quality filters
    """
    from services.parent_brain import get_segments_for_child

    items, total = await get_segments_for_child(
        session=db,
        child_license_id=child_license_id,
        segment_type=segment_type,
        min_quality=min_quality,
        page=page,
        page_size=page_size,
    )

    return {
        "child_license_id": child_license_id,
        "items": [
            {
                "id": str(s.id),
                "type": s.segment_type,
                "name": s.name,
                "description": s.description,
                "quality_score": s.quality_score,
                "source_child": s.source_child_license_id,
                "version": s.version,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/sync")
async def sync_brain(
    child_license_id: str = Depends(_require_child_license),
    segment_types: Optional[list[str]] = None,
    min_quality: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Child ADO syncs all new segments from parent.

    Marks synced segments so they won't be returned again on next sync.
    Returns the actual segment payloads for the child to ingest.
    """
    from services.parent_brain import sync_brain_for_child

    result = await sync_brain_for_child(
        session=db,
        child_license_id=child_license_id,
        segment_types=segment_types,
        min_quality=min_quality,
    )
    return result


# ── Admin: Push & Manage ────────────────────────────────────────────────────

@router.post("/admin/push", dependencies=[Depends(_require_admin)])
async def push_segment(
    segment_id: uuid.UUID,
    child_license_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Admin pushes a specific brain segment to a specific child."""
    from services.parent_brain import push_segment_to_child

    try:
        result = await push_segment_to_child(db, segment_id, child_license_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return result


@router.get("/admin/intelligence", dependencies=[Depends(_require_admin)])
async def intelligence_summary(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return summary of the parent's accumulated intelligence."""
    from services.parent_brain import get_parent_intelligence_summary

    return await get_parent_intelligence_summary(db)


@router.get("/admin/segments", dependencies=[Depends(_require_admin)])
async def list_all_segments(
    segment_type: Optional[str] = Query(None),
    source_child: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Admin: list all brain segments with filters."""
    from sqlalchemy import select, func, desc
    from models.brain_segment import BrainSegment

    stmt = select(BrainSegment)
    count_stmt = select(func.count()).select_from(BrainSegment)

    if segment_type:
        stmt = stmt.where(BrainSegment.segment_type == segment_type)
        count_stmt = count_stmt.where(BrainSegment.segment_type == segment_type)
    if source_child:
        stmt = stmt.where(BrainSegment.source_child_license_id == source_child)
        count_stmt = count_stmt.where(BrainSegment.source_child_license_id == source_child)

    stmt = stmt.order_by(desc(BrainSegment.quality_score))
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    items_result = await db.execute(stmt)
    count_result = await db.execute(count_stmt)

    items = list(items_result.scalars().all())
    total = count_result.scalar() or 0

    return {
        "items": [
            {
                "id": str(s.id),
                "type": s.segment_type,
                "name": s.name,
                "description": s.description,
                "quality_score": s.quality_score,
                "source_child": s.source_child_license_id,
                "version": s.version,
                "transferable": s.transferable,
                "auto_push": s.auto_push,
                "synced_to": s.synced_to_children,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
