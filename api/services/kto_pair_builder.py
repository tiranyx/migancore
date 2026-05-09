"""KTO Pair Builder â€” convert user feedback signals to KTO training format.

Kahneman-Tversky Optimization (KTO) uses direct signals:
  â€¢ thumb_up   â†’ positive signal  (label=True)
  â€¢ thumb_down â†’ negative signal (label=False)

Unlike DPO/SimPO, KTO does NOT need a paired (chosen, rejected) dataset.
It optimizes the policy directly from binary feedback signals.

Reference: Ethayarajh et al. (2024) â€” "KTO: Model Alignment as Prospect Theoretic Optimization"
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.feedback import FeedbackEvent
from models.preference_pair import PreferencePair

logger = structlog.get_logger()


async def build_kto_dataset(
    session: AsyncSession,
    tenant_id: Optional[uuid.UUID] = None,
    since: Optional[datetime] = None,
    limit: int = 1000,
) -> list[dict]:
    """Build a KTO-compatible dataset from user feedback signals.

    Each item:
        {"prompt": str, "completion": str, "label": bool}

    For thumb_up:   label=True  (the completion is desired)
    For thumb_down: label=False (the completion is undesired)
    """
    from sqlalchemy import select, and_

    query = select(FeedbackEvent).where(
        FeedbackEvent.source == "user",
        FeedbackEvent.signal_type.in_(["thumb_up", "thumb_down"]),
    )

    if tenant_id:
        query = query.where(FeedbackEvent.tenant_id == tenant_id)
    if since:
        query = query.where(FeedbackEvent.created_at >= since)

    query = query.order_by(FeedbackEvent.created_at.desc()).limit(limit)
    result = await session.execute(query)
    events = result.scalars().all()

    dataset: list[dict] = []
    for event in events:
        # Get the associated preference pair to extract prompt + completion
        pair = None
        if event.preference_pair_id:
            pair = await session.get(PreferencePair, event.preference_pair_id)

        if not pair:
            continue

        # For thumb_up: the 'chosen' response is the positive completion
        # For thumb_down: the 'rejected' response is the negative completion
        if event.signal_type == "thumb_up":
            # Skip if pair is still awaiting the rejected side
            if pair.rejected.startswith("__AWAITING"):
                continue
            dataset.append({
                "prompt": pair.prompt,
                "completion": pair.chosen,
                "label": True,
                "source": "user_thumbs_up",
                "feedback_id": str(event.id),
            })
        elif event.signal_type == "thumb_down":
            # Skip if pair is still awaiting the chosen side
            if pair.chosen.startswith("__AWAITING"):
                continue
            dataset.append({
                "prompt": pair.prompt,
                "completion": pair.rejected,
                "label": False,
                "source": "user_thumbs_down",
                "feedback_id": str(event.id),
            })

    logger.info(
        "kto.dataset_built",
        total_signals=len(events),
        valid_pairs=len(dataset),
        tenant_id=str(tenant_id) if tenant_id else None,
    )
    return dataset


async def export_kto_jsonl(
    session: AsyncSession,
    output_path: str,
    tenant_id: Optional[uuid.UUID] = None,
    since: Optional[datetime] = None,
    limit: int = 1000,
) -> int:
    """Export KTO dataset to a JSONL file. Returns number of rows written."""
    dataset = await build_kto_dataset(session, tenant_id, since, limit)

    with open(output_path, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    logger.info(
        "kto.exported",
        path=output_path,
        rows=len(dataset),
    )
    return len(dataset)


def format_kto_for_trl(dataset: list[dict]) -> list[dict]:
    """Reformat dataset for TRL KTOTrainer.

    TRL expects:
        {"prompt": str, "completion": str, "label": bool}

    Our dataset is already in this format, but this function provides
    a single point of transformation if TRL changes its expected schema.
    """
    return [
        {
            "prompt": item["prompt"],
            "completion": item["completion"],
            "label": item["label"],
        }
        for item in dataset
    ]
