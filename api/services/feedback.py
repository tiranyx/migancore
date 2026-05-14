"""
Feedback Service â€” convert user signals into auditable events and preference pairs.

Design:
  1. Every signal is first recorded in FeedbackEvent (audit trail).
  2. PreferencePair is created immediately but may have AWAITING_* placeholders.
  3. Background workers fill in the missing side (teacher distillation, synthetic).
"""

from __future__ import annotations

import uuid
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from deps.db import set_tenant_context
from models.feedback import FeedbackEvent
from models.preference_pair import PreferencePair

logger = structlog.get_logger()


async def record_feedback(
    session: AsyncSession,
    *,
    message_id: uuid.UUID,
    tenant_id: uuid.UUID,
    signal_type: str,
    rating: str,
    comment: Optional[str] = None,
    prompt_text: str = "",
    target_text: str = "",
) -> dict:
    """Record a user feedback signal and create a PreferencePair placeholder.

    Returns {"feedback_id": uuid, "pair_id": uuid | None, "status": str}
    """
    # Validate rating before any DB writes
    if rating not in ("thumbs_up", "thumbs_down"):
        logger.warning("feedback.unknown_rating", rating=rating)
        return {
            "feedback_id": None,
            "pair_id": None,
            "status": "unknown_rating",
        }

    # Set RLS tenant context so INSERT into interactions_feedback passes policy.
    await set_tenant_context(session, str(tenant_id))

    # 1. Audit trail
    event = FeedbackEvent(
        message_id=message_id,
        tenant_id=tenant_id,
        signal_type=signal_type,
        comment=comment,
        source="user",
    )
    session.add(event)
    await session.flush()

    # 2. PreferencePair placeholder (may be incomplete â€” worker fills later)
    pair: PreferencePair | None = None

    if rating == "thumbs_up":
        pair = PreferencePair(
            prompt=prompt_text,
            chosen=target_text,
            rejected="__AWAITING_REJECTED__",  # worker will generate worse variant
            judge_score=1.0,
            judge_model="user_signal",
            source_method="user_thumbs_up",
            source_message_id=message_id,
        )
    elif rating == "thumbs_down":
        pair = PreferencePair(
            prompt=prompt_text,
            chosen="__AWAITING_CHOSEN__",  # worker will ask teacher for better variant
            rejected=target_text,
            judge_score=0.0,
            judge_model="user_signal",
            source_method="user_thumbs_down",
            source_message_id=message_id,
        )
    session.add(pair)
    await session.flush()

    # Link event to pair
    event.preference_pair_id = pair.id
    # NOTE: Caller is responsible for session.commit().
    # Do NOT commit here â€” internal commits break caller-managed transactions.

    logger.info(
        "feedback.recorded",
        feedback_id=str(event.id),
        pair_id=str(pair.id),
        rating=rating,
        message_id=str(message_id),
    )

    return {
        "feedback_id": event.id,
        "pair_id": pair.id,
        "status": "recorded",
    }


async def get_feedback_stats(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> dict:
    """Return feedback statistics for a tenant."""
    from sqlalchemy import select, func

    # Set RLS tenant context so SELECT on interactions_feedback passes policy.
    await set_tenant_context(session, str(tenant_id))

    total = await session.scalar(
        select(func.count()).where(FeedbackEvent.tenant_id == tenant_id)
    )
    thumbs_up = await session.scalar(
        select(func.count()).where(
            FeedbackEvent.tenant_id == tenant_id,
            FeedbackEvent.signal_type == "thumb_up",
        )
    )
    thumbs_down = await session.scalar(
        select(func.count()).where(
            FeedbackEvent.tenant_id == tenant_id,
            FeedbackEvent.signal_type == "thumb_down",
        )
    )
    # Count preference pairs that still have AWAITING placeholders
    # (thumbs_up → rejected=__AWAITING_REJECTED__, thumbs_down → chosen=__AWAITING_CHOSEN__)
    awaiting = await session.scalar(
        select(func.count()).where(
            PreferencePair.tenant_id == tenant_id,
            (PreferencePair.chosen.like("__AWAITING_CHOSEN__%"))
            | (PreferencePair.rejected.like("__AWAITING_REJECTED__%")),
        )
    )

    return {
        "total": total or 0,
        "thumbs_up": thumbs_up or 0,
        "thumbs_down": thumbs_down or 0,
        "awaiting_processing": awaiting or 0,
    }
