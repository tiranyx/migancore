"""
Hafidz Ledger — Child Mortality Protocol

Philosophy: ADO must stand alone. The parent is not a brain router.
The parent is a reference, a teacher, a graveyard-keeper of knowledge.

When a child ADO dies (license expires, instance destroyed, revoked),
the parent records the death and extracts final knowledge —
like a historian archiving the last writings of a fallen scholar.

This protocol ensures:
  1. No knowledge is lost when a child dies
  2. The parent can mourn (track) and learn from (extract) every child
  3. License lineage remains immutable — the dead child's signature lives on
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.hafidz import HafidzContribution
from services.hafidz import get_contribution, list_contributions
from services.ingestion import incorporate_contribution

logger = structlog.get_logger()

DEATH_REASONS = {
    "license_expired": "License reached expiry_date, grace period lapsed",
    "license_revoked": "License revoked by parent (fraud, non-payment, breach)",
    "instance_destroyed": "Child ADO instance voluntarily destroyed by client",
    "instance_crashed": "Child ADO instance crashed and not recovered",
    "knowledge_harvested": "Intentional death for knowledge extraction (parent-initiated)",
}


async def report_child_death(
    session: AsyncSession,
    child_license_id: str,
    death_reason: str,
    death_note: Optional[str] = None,
) -> dict[str, Any]:
    """Report that a child ADO has died. Mark all its contributions accordingly.

    Returns summary of contributions affected and extraction status.
    """
    if death_reason not in DEATH_REASONS:
        raise ValueError(f"death_reason must be one of {list(DEATH_REASONS.keys())}")

    now = datetime.now(timezone.utc)

    # Mark all contributions from this child as belonging to a dead instance
    stmt = (
        select(HafidzContribution)
        .where(HafidzContribution.child_license_id == child_license_id)
        .where(HafidzContribution.child_alive == True)
    )
    result = await session.execute(stmt)
    contributions = result.scalars().all()

    affected = 0
    for contrib in contributions:
        contrib.child_alive = False
        contrib.child_death_reason = death_reason
        contrib.child_death_at = now
        affected += 1

    await session.commit()

    # Transfer all brain segments from child to parent
    brain_transfer = {"segments_transferred": 0}
    try:
        from services.parent_brain import transfer_all_segments_on_death
        brain_transfer = await transfer_all_segments_on_death(session, child_license_id)
    except Exception as exc:
        logger.warning(
            "hafidz.brain_transfer_failed",
            child_license_id=child_license_id,
            error=str(exc),
        )

    logger.info(
        "hafidz.child_death_reported",
        child_license_id=child_license_id,
        death_reason=death_reason,
        contributions_affected=affected,
        segments_transferred=brain_transfer.get("segments_transferred", 0),
    )

    return {
        "child_license_id": child_license_id,
        "death_reason": death_reason,
        "death_reason_human": DEATH_REASONS[death_reason],
        "death_note": death_note,
        "contributions_affected": affected,
        "segments_transferred": brain_transfer.get("segments_transferred", 0),
        "died_at": now.isoformat(),
    }


async def extract_final_knowledge(
    session: AsyncSession,
    child_license_id: str,
    auto_ingest: bool = True,
) -> dict[str, Any]:
    """Extract all unincorporated knowledge from a dead child.

    This is the parent's final act of learning from the child:
    - Gather all pending/reviewing contributions from the dead child
    - Run ingestion (quality scoring + incorporate) on each
    - Mark as final_knowledge_extracted = true

    Returns extraction summary with decisions per contribution.
    """
    stmt = (
        select(HafidzContribution)
        .where(HafidzContribution.child_license_id == child_license_id)
        .where(HafidzContribution.child_alive == False)
        .where(HafidzContribution.final_knowledge_extracted == False)
        .where(HafidzContribution.status.in_(["pending", "reviewing"]))
        .order_by(desc(HafidzContribution.received_at))
    )
    result = await session.execute(stmt)
    contributions = result.scalars().all()

    if not contributions:
        return {
            "child_license_id": child_license_id,
            "extracted_count": 0,
            "message": "No unincorporated knowledge remaining for this child.",
        }

    extracted = []
    for contrib in contributions:
        if auto_ingest:
            try:
                ingest_result = await incorporate_contribution(session, contrib.id)
                decision = ingest_result["decision"]
                quality_score = ingest_result["quality_score"]
            except Exception as exc:
                logger.warning(
                    "hafidz.final_extraction_failed",
                    contribution_id=str(contrib.id),
                    error=str(exc),
                )
                decision = "extraction_failed"
                quality_score = None
        else:
            decision = "queued_for_manual_review"
            quality_score = contrib.quality_score

        contrib.final_knowledge_extracted = True
        extracted.append({
            "contribution_id": str(contrib.id),
            "type": contrib.contribution_type,
            "decision": decision,
            "quality_score": quality_score,
        })

    await session.commit()

    logger.info(
        "hafidz.final_knowledge_extracted",
        child_license_id=child_license_id,
        extracted_count=len(extracted),
    )

    return {
        "child_license_id": child_license_id,
        "extracted_count": len(extracted),
        "contributions": extracted,
        "message": f"Final knowledge extracted from {len(extracted)} contributions of deceased child.",
    }


async def list_deceased_children(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """List all child ADO instances that have died, with summary stats."""
    from sqlalchemy import func

    # Subquery: aggregate per child_license_id
    stmt = (
        select(
            HafidzContribution.child_license_id,
            HafidzContribution.child_display_name,
            HafidzContribution.child_tier,
            func.count().label("total_contributions"),
            func.count(HafidzContribution.status == "incorporated").label("incorporated"),
            func.max(HafidzContribution.child_death_at).label("died_at"),
            func.max(HafidzContribution.child_death_reason).label("death_reason"),
        )
        .where(HafidzContribution.child_alive == False)
        .group_by(
            HafidzContribution.child_license_id,
            HafidzContribution.child_display_name,
            HafidzContribution.child_tier,
        )
        .order_by(desc(func.max(HafidzContribution.child_death_at)))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    count_stmt = (
        select(func.count(func.distinct(HafidzContribution.child_license_id)))
        .where(HafidzContribution.child_alive == False)
    )

    result = await session.execute(stmt)
    count_result = await session.execute(count_stmt)

    rows = []
    for row in result.all():
        rows.append({
            "child_license_id": row.child_license_id,
            "child_display_name": row.child_display_name,
            "child_tier": row.child_tier,
            "total_contributions": row.total_contributions,
            "incorporated_count": row.incorporated,
            "died_at": row.died_at.isoformat() if row.died_at else None,
            "death_reason": row.death_reason,
        })

    total = count_result.scalar() or 0
    return rows, total


async def get_child_obituary(
    session: AsyncSession,
    child_license_id: str,
) -> dict[str, Any]:
    """Return full obituary for a deceased child: contributions, knowledge extracted, legacy."""
    stmt = (
        select(HafidzContribution)
        .where(HafidzContribution.child_license_id == child_license_id)
        .order_by(desc(HafidzContribution.received_at))
    )
    result = await session.execute(stmt)
    contributions = result.scalars().all()

    if not contributions:
        raise ValueError(f"No contributions found for child {child_license_id}")

    first = contributions[0]
    incorporated = [c for c in contributions if c.status == "incorporated"]
    pending = [c for c in contributions if c.status in ("pending", "reviewing")]
    rejected = [c for c in contributions if c.status == "rejected"]

    return {
        "child_license_id": child_license_id,
        "child_display_name": first.child_display_name,
        "child_tier": first.child_tier,
        "born_at": first.created_at.isoformat() if first.created_at else None,
        "died_at": first.child_death_at.isoformat() if first.child_death_at else None,
        "death_reason": first.child_death_reason,
        "is_alive": first.child_alive,
        "legacy": {
            "total_contributions": len(contributions),
            "incorporated": len(incorporated),
            "pending": len(pending),
            "rejected": len(rejected),
            "total_quality": round(sum(c.quality_score or 0 for c in incorporated), 4),
        },
        "contributions": [
            {
                "id": str(c.id),
                "type": c.contribution_type,
                "status": c.status,
                "quality_score": c.quality_score,
                "received_at": c.received_at.isoformat() if c.received_at else None,
            }
            for c in contributions
        ],
    }
