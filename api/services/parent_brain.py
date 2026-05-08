"""
Parent Brain Service — Knowledge Accumulation & Distribution

The parent is the family's collective memory.
Each child contributes segments. The parent synthesizes and redistributes.

Flow:
  1. Child contributes knowledge → Hafidz Ledger → Ingestion
  2. Ingestion calls accumulate_segment() → stores in brain_segments
  3. Child (live or newborn) calls sync_brain() → fetches new segments
  4. Parent calls push_segment() → pushes specific segment to specific child
  5. Child dies → transfer_all_segments() → all knowledge moves to parent

Philosophy:
  - The parent becomes smarter over time by learning from all children.
  - Newborn children inherit the accumulated wisdom of the entire family.
  - Live children sync periodically to stay up-to-date.
  - Dead children's knowledge lives on in the parent's brain.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.brain_segment import BrainSegment
from models.hafidz import HafidzContribution

logger = structlog.get_logger()

SEGMENT_TYPES = {"skill", "domain_knowledge", "tool_pattern", "voice_pattern", "dpo_pair"}


# ─────────────────────────────────────────────────────────────────────────────
# Accumulation — Child → Parent
# ─────────────────────────────────────────────────────────────────────────────

async def accumulate_segment(
    session: AsyncSession,
    contribution: HafidzContribution,
) -> BrainSegment:
    """Convert an incorporated Hafidz contribution into a Brain Segment.

    This is how the parent 'learns' from the child.
    """
    segment_type = contribution.contribution_type
    if segment_type not in SEGMENT_TYPES:
        segment_type = "domain_knowledge"  # fallback

    # Build human-readable name
    name = _build_segment_name(contribution)

    segment = BrainSegment(
        segment_type=segment_type,
        name=name,
        description=contribution.anonymized_payload.get("description", ""),
        source_child_license_id=contribution.child_license_id,
        source_contribution_id=contribution.id,
        payload=contribution.anonymized_payload,
        quality_score=contribution.quality_score,
        version=1,
        transferable=True,
        auto_push=True,
        synced_to_children=[],
    )
    session.add(segment)
    await session.commit()
    await session.refresh(segment)

    logger.info(
        "parent_brain.segment_accumulated",
        segment_id=str(segment.id),
        segment_type=segment_type,
        source_child=contribution.child_license_id,
        quality_score=contribution.quality_score,
    )
    return segment


def _build_segment_name(contribution: HafidzContribution) -> str:
    """Generate a human-readable name for a segment."""
    payload = contribution.anonymized_payload or {}
    name_hint = payload.get("name", "")
    if name_hint:
        return name_hint

    type_labels = {
        "dpo_pair": "Training Example",
        "tool_pattern": "Tool Usage Pattern",
        "domain_cluster": "Domain Knowledge",
        "voice_pattern": "Voice Style Pattern",
    }
    label = type_labels.get(contribution.contribution_type, "Knowledge")
    child_short = contribution.child_display_name[:20]
    return f"{label} from {child_short}"


# ─────────────────────────────────────────────────────────────────────────────
# Distribution — Parent → Child
# ─────────────────────────────────────────────────────────────────────────────

async def get_segments_for_child(
    session: AsyncSession,
    child_license_id: str,
    segment_type: Optional[str] = None,
    min_quality: Optional[float] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[BrainSegment], int]:
    """List all segments available for a specific child to fetch.

    Filters:
      - transferable = true
      - Not already synced to this child (unless force resync)
      - Optional: segment_type filter
      - Optional: minimum quality_score
    """
    stmt = select(BrainSegment).where(
        BrainSegment.transferable == True,
    )
    count_stmt = select(func.count()).select_from(BrainSegment).where(
        BrainSegment.transferable == True,
    )

    # Exclude already synced (unless we want resync)
    # JSONB containment: synced_to_children @> [child_license_id]
    from sqlalchemy import not_
    from sqlalchemy.dialects.postgresql import array as pg_array
    stmt = stmt.where(
        not_(BrainSegment.synced_to_children.contains([child_license_id]))
    )
    count_stmt = count_stmt.where(
        not_(BrainSegment.synced_to_children.contains([child_license_id]))
    )

    if segment_type:
        stmt = stmt.where(BrainSegment.segment_type == segment_type)
        count_stmt = count_stmt.where(BrainSegment.segment_type == segment_type)

    if min_quality is not None:
        stmt = stmt.where(BrainSegment.quality_score >= min_quality)
        count_stmt = count_stmt.where(BrainSegment.quality_score >= min_quality)

    stmt = stmt.order_by(desc(BrainSegment.quality_score))
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    items_result = await session.execute(stmt)
    count_result = await session.execute(count_stmt)

    items = list(items_result.scalars().all())
    total = count_result.scalar() or 0
    return items, total


async def sync_brain_for_child(
    session: AsyncSession,
    child_license_id: str,
    segment_types: Optional[list[str]] = None,
    min_quality: Optional[float] = None,
) -> dict[str, Any]:
    """Child calls this to sync all new segments from the parent.

    Returns the segments + marks them as synced to this child.
    """
    # If no segment_types specified, get all transferable types
    if segment_types:
        valid_types = [t for t in segment_types if t in SEGMENT_TYPES]
    else:
        valid_types = None

    stmt = select(BrainSegment).where(
        BrainSegment.transferable == True,
        not_(BrainSegment.synced_to_children.contains([child_license_id])),
    )

    if valid_types:
        stmt = stmt.where(BrainSegment.segment_type.in_(valid_types))
    if min_quality is not None:
        stmt = stmt.where(BrainSegment.quality_score >= min_quality)

    stmt = stmt.order_by(desc(BrainSegment.quality_score))
    result = await session.execute(stmt)
    segments = result.scalars().all()

    synced_ids = []
    for segment in segments:
        if child_license_id not in segment.synced_to_children:
            segment.synced_to_children = list(segment.synced_to_children) + [child_license_id]
            synced_ids.append(str(segment.id))

    if synced_ids:
        await session.commit()

    logger.info(
        "parent_brain.child_synced",
        child_license_id=child_license_id,
        segments_synced=len(synced_ids),
    )

    return {
        "child_license_id": child_license_id,
        "segments_synced": len(synced_ids),
        "segments": [
            {
                "id": str(s.id),
                "type": s.segment_type,
                "name": s.name,
                "description": s.description,
                "quality_score": s.quality_score,
                "source_child": s.source_child_license_id,
                "version": s.version,
                "payload": s.payload,
            }
            for s in segments
        ],
    }


async def push_segment_to_child(
    session: AsyncSession,
    segment_id: uuid.UUID,
    child_license_id: str,
) -> dict[str, Any]:
    """Parent (admin) pushes a specific segment to a specific child."""
    segment = await session.get(BrainSegment, segment_id)
    if segment is None:
        raise ValueError("Segment not found")

    if not segment.transferable:
        raise ValueError("Segment is not transferable")

    if child_license_id not in segment.synced_to_children:
        segment.synced_to_children = list(segment.synced_to_children) + [child_license_id]
        await session.commit()

    logger.info(
        "parent_brain.segment_pushed",
        segment_id=str(segment_id),
        child_license_id=child_license_id,
    )

    return {
        "segment_id": str(segment_id),
        "child_license_id": child_license_id,
        "pushed": True,
        "segment": {
            "id": str(segment.id),
            "type": segment.segment_type,
            "name": segment.name,
            "quality_score": segment.quality_score,
            "payload": segment.payload,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Death Transfer — Child → Parent (ALL knowledge)
# ─────────────────────────────────────────────────────────────────────────────

async def transfer_all_segments_on_death(
    session: AsyncSession,
    child_license_id: str,
) -> dict[str, Any]:
    """When a child dies, transfer ALL its segments to the parent.

    This ensures no knowledge is lost. The child's segments are:
      1. Marked as owned by "parent" (source_child_license_id = "parent")
      2. Their version is incremented
      3. auto_push is set to true (so other children can inherit)

    Returns summary of transferred segments.
    """
    stmt = select(BrainSegment).where(
        BrainSegment.source_child_license_id == child_license_id,
    )
    result = await session.execute(stmt)
    segments = result.scalars().all()

    transferred = 0
    for segment in segments:
        segment.source_child_license_id = "parent"
        segment.version += 1
        segment.auto_push = True
        segment.transferable = True
        segment.synced_to_children = []  # Reset sync — all children can now receive
        transferred += 1

    await session.commit()

    logger.info(
        "parent_brain.death_transfer_complete",
        child_license_id=child_license_id,
        segments_transferred=transferred,
    )

    return {
        "child_license_id": child_license_id,
        "segments_transferred": transferred,
        "message": f"All {transferred} segments from deceased child transferred to parent brain.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Parent Intelligence — Query accumulated knowledge
# ─────────────────────────────────────────────────────────────────────────────

async def get_parent_intelligence_summary(
    session: AsyncSession,
) -> dict[str, Any]:
    """Return summary of the parent's accumulated intelligence."""
    from sqlalchemy import func

    total_stmt = select(func.count()).select_from(BrainSegment)
    by_type_stmt = (
        select(BrainSegment.segment_type, func.count())
        .group_by(BrainSegment.segment_type)
    )
    avg_quality_stmt = select(func.avg(BrainSegment.quality_score)).select_from(BrainSegment)
    sources_stmt = (
        select(BrainSegment.source_child_license_id, func.count())
        .group_by(BrainSegment.source_child_license_id)
    )

    total = (await session.execute(total_stmt)).scalar() or 0
    by_type = dict((await session.execute(by_type_stmt)).all())
    avg_quality = (await session.execute(avg_quality_stmt)).scalar() or 0.0
    sources = dict((await session.execute(sources_stmt)).all())

    return {
        "total_segments": total,
        "by_type": by_type,
        "average_quality": round(float(avg_quality), 4) if avg_quality else 0.0,
        "sources": sources,
        "parent_native_segments": sources.get("parent", 0),
        "child_contributed_segments": total - sources.get("parent", 0),
    }
