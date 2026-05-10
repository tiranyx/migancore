"""User Feedback Processor â€” background worker for completing preference pairs.

Runs every 60 minutes as an asyncio task (started in main.py lifespan).
Processes preference pairs with __AWAITING_* placeholders:
  â€¢ __AWAITING_CHOSEN__  (thumb_down) â†’ ask teacher for better response
  â€¢ __AWAITING_REJECTED__ (thumb_up)  â†’ ask local model for worse response

Cost controls:
  â€¢ Hard cap per run: $0.50 for teacher calls, $0.10 for local inference
  â€¢ Max 50 pairs processed per run
  â€¢ Failed pairs retried next run (max 3 attempts)
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.base import AsyncSessionLocal
from models.preference_pair import PreferencePair
from services.teacher_api import call_gemini, TeacherError
from services.ollama import OllamaClient

logger = structlog.get_logger()

# Cost caps per run (USD)
TEACHER_BUDGET_PER_RUN = 0.50
LOCAL_BUDGET_PER_RUN = 0.10
MAX_PAIRS_PER_RUN = 50

# Retry tracking: failed pairs get retried up to MAX_RETRIES times
MAX_RETRIES = 3

# How often the worker runs (seconds)
WORKER_INTERVAL_SECONDS = 600   # 10 minutes (was 1 hour)


async def _get_awaiting_pairs(session: AsyncSession) -> list[PreferencePair]:
    """Query preference_pairs that need completion."""
    result = await session.execute(
        select(PreferencePair).where(
            (
                (PreferencePair.chosen.like("__AWAITING_CHOSEN__%"))
                | (PreferencePair.rejected.like("__AWAITING_REJECTED__%"))
            )
            & (PreferencePair.processing_attempts < MAX_RETRIES)
        ).order_by(PreferencePair.created_at.asc()).limit(MAX_PAIRS_PER_RUN)
    )
    return list(result.scalars().all())


async def _complete_awaiting_chosen(
    session: AsyncSession,
    pair: PreferencePair,
    cost_tracker: dict,
) -> bool:
    """Generate a better 'chosen' response for a thumb_down pair using teacher API.

    Returns True if successfully completed, False if budget exceeded or failed.
    """
    if cost_tracker["teacher"] >= TEACHER_BUDGET_PER_RUN:
        logger.warning("feedback.worker.teacher_budget_exceeded", pair_id=str(pair.id))
        return False

    prompt = (
        f"User asked:\n{pair.prompt}\n\n"
        f"The assistant gave this poor response:\n{pair.rejected}\n\n"
        "Generate a significantly better, more helpful response. "
        "Be concise, accurate, and directly address the user's question."
    )

    try:
        resp = await call_gemini(prompt, max_tokens=600)
        cost_tracker["teacher"] += resp.cost_usd

        pair.chosen = resp.text.strip()
        pair.judge_model = f"teacher:{resp.provider}:{resp.model}"
        await session.flush()

        logger.info(
            "feedback.worker.chosen_completed",
            pair_id=str(pair.id),
            cost_usd=resp.cost_usd,
            provider=resp.provider,
        )
        return True

    except TeacherError as exc:
        logger.warning(
            "feedback.worker.teacher_failed",
            pair_id=str(pair.id),
            error=str(exc),
        )
        return False
    except Exception as exc:
        logger.error(
            "feedback.worker.chosen_error",
            pair_id=str(pair.id),
            error=str(exc),
        )
        return False


async def _complete_awaiting_rejected(
    session: AsyncSession,
    pair: PreferencePair,
    cost_tracker: dict,
) -> bool:
    """Generate a worse 'rejected' response for a thumb_up pair using local model.

    Returns True if successfully completed, False if budget exceeded or failed.
    """
    if cost_tracker["local"] >= LOCAL_BUDGET_PER_RUN:
        logger.warning("feedback.worker.local_budget_exceeded", pair_id=str(pair.id))
        return False

    # Use Ollama with a lightweight prompt to generate a worse/different response
    client = OllamaClient(base_url=settings.OLLAMA_URL)
    prompt = (
        f"User asked:\n{pair.prompt}\n\n"
        f"The assistant gave this good response:\n{pair.chosen}\n\n"
        "Generate a worse, less helpful, or slightly incorrect response "
        "for the same question. Keep it short."
    )

    try:
        resp_text = await client.generate(
            model=settings.DEFAULT_MODEL,
            prompt=prompt,
            options={"temperature": 0.9, "num_predict": 300},
        )
        # Rough cost estimate: local inference â‰ˆ $0.001 per 1K tokens (electricity/GPU amortized)
        cost_tracker["local"] += 0.001

        pair.rejected = resp_text.strip()
        pair.judge_model = f"local:{settings.DEFAULT_MODEL}"
        await session.flush()

        logger.info(
            "feedback.worker.rejected_completed",
            pair_id=str(pair.id),
        )
        return True

    except Exception as exc:
        logger.error(
            "feedback.worker.rejected_error",
            pair_id=str(pair.id),
            error=str(exc),
        )
        return False


async def _process_batch() -> dict:
    """Process one batch of awaiting pairs. Returns stats."""
    stats = {"processed": 0, "failed": 0, "teacher_cost": 0.0, "local_cost": 0.0}
    cost_tracker = {"teacher": 0.0, "local": 0.0}

    async with AsyncSessionLocal() as session:
        pairs = await _get_awaiting_pairs(session)
        if not pairs:
            logger.info("feedback.worker.no_pairs_to_process")
            return stats

        logger.info("feedback.worker.batch_start", count=len(pairs))

        for pair in pairs:
            pair.processing_attempts += 1
            ok = False
            if pair.chosen.startswith("__AWAITING_CHOSEN__"):
                ok = await _complete_awaiting_chosen(session, pair, cost_tracker)
            elif pair.rejected.startswith("__AWAITING_REJECTED__"):
                ok = await _complete_awaiting_rejected(session, pair, cost_tracker)

            if ok:
                stats["processed"] += 1
            else:
                stats["failed"] += 1

        await session.commit()

    stats["teacher_cost"] = cost_tracker["teacher"]
    stats["local_cost"] = cost_tracker["local"]
    logger.info(
        "feedback.worker.batch_done",
        processed=stats["processed"],
        failed=stats["failed"],
        teacher_cost=stats["teacher_cost"],
        local_cost=stats["local_cost"],
    )
    return stats


async def start_feedback_worker() -> None:
    """Entry point for the background asyncio task."""
    logger.info("feedback.worker.started", interval_seconds=WORKER_INTERVAL_SECONDS)

    while True:
        try:
            await _process_batch()
        except Exception as exc:
            logger.error("feedback.worker.batch_fatal", error=str(exc))

        await asyncio.sleep(WORKER_INTERVAL_SECONDS)
