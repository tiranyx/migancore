"""
Knowledge Ingestion Pipeline — SP-009

Converts approved Hafidz contributions into training data (preference_pairs).
Quality scoring is rule-based heuristics (MVP); ML-based scoring in roadmap.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from models.hafidz import HafidzContribution
from models.preference_pair import PreferencePair
from services.hafidz import get_contribution

logger = structlog.get_logger()

# ─────────────────────────────────────────────────────────────────────────────
# Quality Scoring (rule-based heuristics)
# ─────────────────────────────────────────────────────────────────────────────

QUALITY_WEIGHTS = {
    "payload_size": 0.25,
    "structure": 0.35,
    "novelty": 0.25,
    "type_diversity": 0.15,
}


async def score_contribution(
    session: AsyncSession,
    contrib: HafidzContribution,
) -> float:
    """Return quality score 0.0–1.0 based on rule-based heuristics."""
    payload = contrib.anonymized_payload or {}
    scores: dict[str, float] = {}

    # 1. Payload size score (0–0.25)
    payload_str = json.dumps(payload)
    size = len(payload_str)
    if size >= 5000:
        scores["payload_size"] = 1.0
    elif size >= 1000:
        scores["payload_size"] = 0.7
    elif size >= 200:
        scores["payload_size"] = 0.4
    else:
        scores["payload_size"] = 0.1

    # 2. Structure score (0–0.35)
    # Expected fields depend on contribution_type
    expected_fields = _expected_fields_for_type(contrib.contribution_type)
    matched = sum(1 for f in expected_fields if f in payload)
    scores["structure"] = matched / max(len(expected_fields), 1)

    # 3. Novelty score (0–0.25) — hash uniqueness already enforced,
    #    but we score higher if child hasn't submitted recently
    scores["novelty"] = await _novelty_score(session, contrib)

    # 4. Type diversity score (0–0.15) — rare types score higher
    scores["type_diversity"] = _type_diversity_score(contrib.contribution_type)

    # Weighted total
    total = sum(scores[k] * QUALITY_WEIGHTS[k] for k in QUALITY_WEIGHTS)
    return round(min(max(total, 0.0), 1.0), 4)


def _expected_fields_for_type(contribution_type: str) -> list[str]:
    """Return expected payload fields for a given contribution type."""
    mapping: dict[str, list[str]] = {
        "dpo_pair": ["prompt", "chosen", "rejected"],
        "tool_pattern": ["tool_name", "usage_pattern", "success_rate"],
        "domain_cluster": ["domain", "entities", "relationships"],
        "voice_pattern": ["tone", "style_markers", "sample_utterances"],
    }
    return mapping.get(contribution_type, ["content"])


async def _novelty_score(
    session: AsyncSession,
    contrib: HafidzContribution,
) -> float:
    """Score higher if child hasn't submitted in the last 24h."""
    from sqlalchemy import select, func, and_
    from datetime import timedelta

    from models.hafidz import HafidzContribution as HC

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    stmt = select(func.count()).where(
        and_(
            HC.child_license_id == contrib.child_license_id,
            HC.id != contrib.id,
            HC.received_at >= cutoff,
        )
    )
    result = await session.execute(stmt)
    recent_count = result.scalar() or 0

    if recent_count == 0:
        return 1.0
    elif recent_count <= 2:
        return 0.7
    elif recent_count <= 5:
        return 0.4
    else:
        return 0.1


def _type_diversity_score(contribution_type: str) -> float:
    """Rare contribution types score higher to encourage diversity."""
    rarity: dict[str, float] = {
        "voice_pattern": 1.0,   # rarest
        "domain_cluster": 0.8,
        "tool_pattern": 0.6,
        "dpo_pair": 0.4,        # most common
    }
    return rarity.get(contribution_type, 0.5)


# ─────────────────────────────────────────────────────────────────────────────
# Incorporation
# ─────────────────────────────────────────────────────────────────────────────

async def incorporate_contribution(
    session: AsyncSession,
    contribution_id: uuid.UUID,
) -> dict[str, Any]:
    """Process a contribution: score, decide fate, optionally convert to training data.

    Returns dict with keys: contribution_id, quality_score, decision, pair_id (optional).
    """
    contrib = await get_contribution(session, contribution_id)
    if contrib is None:
        raise ValueError("Contribution not found")

    if contrib.status not in ("pending", "reviewing"):
        raise ValueError(f"Cannot incorporate contribution with status '{contrib.status}'")

    # Score
    quality_score = await score_contribution(session, contrib)
    contrib.quality_score = quality_score

    # Decide
    segment_id = None
    if quality_score >= 0.8:
        decision = "auto_approved"
        contrib.status = "incorporated"
        contrib.incorporated_at = datetime.now(timezone.utc)
        pair_id = await _convert_to_preference_pair(session, contrib)
        # Also accumulate into Parent Brain for distribution to other children
        try:
            from services.parent_brain import accumulate_segment
            segment = await accumulate_segment(session, contrib)
            segment_id = segment.id
        except Exception as exc:
            logger.warning(
                "ingestion.brain_accumulate_failed",
                contribution_id=str(contribution_id),
                error=str(exc),
            )
    elif quality_score >= 0.5:
        decision = "queued_for_review"
        contrib.status = "reviewing"
        pair_id = None
    else:
        decision = "auto_rejected"
        contrib.status = "rejected"
        contrib.reject_reason = f"Quality score {quality_score} below threshold 0.5"
        pair_id = None

    await session.commit()
    await session.refresh(contrib)

    logger.info(
        "ingestion.processed",
        contribution_id=str(contribution_id),
        quality_score=quality_score,
        decision=decision,
        pair_id=str(pair_id) if pair_id else None,
    )

    return {
        "contribution_id": contribution_id,
        "quality_score": quality_score,
        "decision": decision,
        "pair_id": pair_id,
        "segment_id": segment_id,
    }


async def _convert_to_preference_pair(
    session: AsyncSession,
    contrib: HafidzContribution,
) -> uuid.UUID:
    """Convert an approved contribution into a PreferencePair for training."""
    payload = contrib.anonymized_payload or {}

    # Extract prompt / chosen / rejected from payload based on type
    if contrib.contribution_type == "dpo_pair":
        prompt = payload.get("prompt", "")
        chosen = payload.get("chosen", "")
        rejected = payload.get("rejected", "")
    else:
        # For non-DPO types, treat the whole payload as a "chosen" improvement
        prompt = json.dumps({"type": contrib.contribution_type, "source": contrib.child_license_id})
        chosen = json.dumps(payload)
        rejected = "{}"  # empty baseline

    pair = PreferencePair(
        prompt=prompt,
        chosen=chosen,
        rejected=rejected,
        judge_score=contrib.quality_score or 0.0,
        judge_model="hafidz_rule_based_v1",
        source_method="hafidz_ingestion",
        source_message_id=None,
    )
    session.add(pair)
    await session.flush()
    return pair.id
