"""
Hafidz Ledger service layer — business logic for knowledge contributions.

Handles:
  - Creating contributions (with deduplication via SHA-256 hash)
  - Listing / filtering contributions
  - Review workflow (approve / reject)
  - Summary queries
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.hafidz import HafidzContribution
from schemas.hafidz import CONTRIBUTION_TYPES, STATUSES

logger = structlog.get_logger()


# ─────────────────────────────────────────────────────────────────────────────
# Create
# ─────────────────────────────────────────────────────────────────────────────

async def create_contribution(
    session: AsyncSession,
    child_license_id: str,
    child_display_name: str,
    child_tier: str,
    parent_version: str,
    contribution_type: str,
    contribution_hash: str,
    anonymized_payload: dict[str, Any],
) -> HafidzContribution:
    """Create a new contribution after validating type and checking hash uniqueness."""

    if contribution_type not in CONTRIBUTION_TYPES:
        raise ValueError(f"Invalid contribution_type: {contribution_type}")

    # Deduplication: check if hash already exists
    existing = await session.execute(
        select(HafidzContribution).where(
            HafidzContribution.contribution_hash == contribution_hash
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Contribution hash already exists (deduplication)")

    contrib = HafidzContribution(
        child_license_id=child_license_id,
        child_display_name=child_display_name,
        child_tier=child_tier,
        parent_version=parent_version,
        contribution_type=contribution_type,
        contribution_hash=contribution_hash,
        anonymized_payload=anonymized_payload,
        status="pending",
    )
    session.add(contrib)
    await session.commit()
    await session.refresh(contrib)

    logger.info(
        "hafidz.contribution_created",
        id=str(contrib.id),
        child_license_id=child_license_id,
        type=contribution_type,
        hash=contribution_hash,
    )
    return contrib


# ─────────────────────────────────────────────────────────────────────────────
# Read
# ─────────────────────────────────────────────────────────────────────────────

async def get_contribution(
    session: AsyncSession,
    contribution_id: uuid.UUID,
) -> Optional[HafidzContribution]:
    """Get a single contribution by ID."""
    result = await session.execute(
        select(HafidzContribution).where(HafidzContribution.id == contribution_id)
    )
    return result.scalar_one_or_none()


async def get_contribution_by_hash(
    session: AsyncSession,
    contribution_hash: str,
) -> Optional[HafidzContribution]:
    """Get a single contribution by its SHA-256 hash."""
    result = await session.execute(
        select(HafidzContribution).where(
            HafidzContribution.contribution_hash == contribution_hash
        )
    )
    return result.scalar_one_or_none()


async def list_contributions(
    session: AsyncSession,
    *,
    status: Optional[str] = None,
    contribution_type: Optional[str] = None,
    child_license_id: Optional[str] = None,
    parent_version: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[HafidzContribution], int]:
    """List contributions with optional filtering and pagination.

    Returns (items, total_count).
    """
    stmt = select(HafidzContribution)
    count_stmt = select(func.count()).select_from(HafidzContribution)

    if status:
        stmt = stmt.where(HafidzContribution.status == status)
        count_stmt = count_stmt.where(HafidzContribution.status == status)
    if contribution_type:
        stmt = stmt.where(HafidzContribution.contribution_type == contribution_type)
        count_stmt = count_stmt.where(
            HafidzContribution.contribution_type == contribution_type
        )
    if child_license_id:
        stmt = stmt.where(HafidzContribution.child_license_id == child_license_id)
        count_stmt = count_stmt.where(
            HafidzContribution.child_license_id == child_license_id
        )
    if parent_version:
        stmt = stmt.where(HafidzContribution.parent_version == parent_version)
        count_stmt = count_stmt.where(
            HafidzContribution.parent_version == parent_version
        )

    # Order by received_at DESC (newest first)
    stmt = stmt.order_by(desc(HafidzContribution.received_at))

    # Pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    items_result = await session.execute(stmt)
    count_result = await session.execute(count_stmt)

    items = list(items_result.scalars().all())
    total = count_result.scalar() or 0

    return items, total


# ─────────────────────────────────────────────────────────────────────────────
# Review workflow
# ─────────────────────────────────────────────────────────────────────────────

async def review_contribution(
    session: AsyncSession,
    contribution_id: uuid.UUID,
    *,
    action: str,  # "approve" | "reject"
    quality_score: Optional[float] = None,
    reject_reason: Optional[str] = None,
    incorporated_cycle: Optional[int] = None,
) -> HafidzContribution:
    """Parent review: approve or reject a pending contribution."""

    contrib = await get_contribution(session, contribution_id)
    if contrib is None:
        raise ValueError("Contribution not found")

    if contrib.status != "pending":
        raise ValueError(f"Cannot review contribution with status '{contrib.status}'")

    if action == "approve":
        contrib.status = "incorporated"
        contrib.incorporated_at = datetime.now(timezone.utc)
        if quality_score is not None:
            contrib.quality_score = quality_score
        if incorporated_cycle is not None:
            contrib.incorporated_cycle = incorporated_cycle
        logger.info(
            "hafidz.contribution_approved",
            id=str(contrib.id),
            quality_score=quality_score,
            cycle=incorporated_cycle,
        )

    elif action == "reject":
        contrib.status = "rejected"
        if reject_reason:
            contrib.reject_reason = reject_reason
        logger.info(
            "hafidz.contribution_rejected",
            id=str(contrib.id),
            reason=reject_reason,
        )
    else:
        raise ValueError("action must be 'approve' or 'reject'")

    await session.commit()
    await session.refresh(contrib)
    return contrib


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

async def get_child_summary(
    session: AsyncSession,
    child_license_id: str,
) -> dict[str, Any]:
    """Return aggregate stats for a specific child license."""
    from sqlalchemy import func

    stmt = select(
        func.count().label("total"),
        func.count(HafidzContribution.status == "incorporated").label("incorporated"),
        func.count(HafidzContribution.status == "pending").label("pending"),
        func.max(HafidzContribution.received_at).label("last_at"),
    ).where(HafidzContribution.child_license_id == child_license_id)

    result = await session.execute(stmt)
    row = result.one()

    return {
        "child_license_id": child_license_id,
        "total_contributions": row.total,
        "incorporated_count": row.incorporated,
        "pending_count": row.pending,
        "last_contribution": row.last_at.isoformat() if row.last_at else None,
    }
