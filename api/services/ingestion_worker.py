"""
Ingestion Worker — background task that processes Hafidz contributions from Redis queue.

Started in FastAPI lifespan. Uses redis.asyncio for non-blocking queue operations.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Optional

import structlog

from config import settings

logger = structlog.get_logger()

QUEUE_KEY = "migancore:ingestion:queue"
WORKER_RUNNING = False
WORKER_TASK: Optional[asyncio.Task] = None


async def enqueue_contribution(contribution_id: uuid.UUID) -> bool:
    """Push a contribution ID to the ingestion queue."""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=5)
        await r.lpush(QUEUE_KEY, str(contribution_id))
        await r.aclose()
        logger.info("ingestion.enqueued", contribution_id=str(contribution_id))
        return True
    except Exception as exc:
        logger.warning("ingestion.enqueue_failed", contribution_id=str(contribution_id), error=str(exc))
        return False


async def _process_one(contribution_id_str: str) -> None:
    """Process a single contribution from the queue."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from models.base import AsyncSessionLocal
    from services.ingestion import incorporate_contribution

    try:
        contribution_id = uuid.UUID(contribution_id_str)
    except ValueError:
        logger.warning("ingestion.invalid_uuid", value=contribution_id_str)
        return

    async with AsyncSessionLocal() as session:
        async with session.begin():
            try:
                result = await incorporate_contribution(session, contribution_id)
                logger.info(
                    "ingestion.completed",
                    contribution_id=contribution_id_str,
                    decision=result["decision"],
                    quality_score=result["quality_score"],
                )
            except Exception as exc:
                logger.error(
                    "ingestion.failed",
                    contribution_id=contribution_id_str,
                    error=str(exc),
                )


async def worker_loop(poll_interval: float = 5.0) -> None:
    """Main worker loop: blocking pop from Redis, process, repeat."""
    global WORKER_RUNNING
    WORKER_RUNNING = True

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=5)
    except Exception as exc:
        logger.error("ingestion.worker.redis_failed", error=str(exc))
        WORKER_RUNNING = False
        return

    logger.info("ingestion.worker.started", queue_key=QUEUE_KEY)

    while WORKER_RUNNING:
        try:
            # Non-blocking pop with timeout (brpop blocks, but we use timeout to allow graceful shutdown)
            result = await r.brpop(QUEUE_KEY, timeout=int(poll_interval))
            if result is None:
                continue

            _, contribution_id_str = result
            await _process_one(contribution_id_str)
        except asyncio.CancelledError:
            logger.info("ingestion.worker.cancelled")
            break
        except Exception as exc:
            logger.error("ingestion.worker.loop_error", error=str(exc))
            await asyncio.sleep(poll_interval)

    await r.aclose()
    WORKER_RUNNING = False
    logger.info("ingestion.worker.stopped")


def start_worker() -> asyncio.Task:
    """Start the ingestion worker as a background asyncio task."""
    global WORKER_TASK
    if WORKER_TASK is not None and not WORKER_TASK.done():
        logger.warning("ingestion.worker.already_running")
        return WORKER_TASK

    WORKER_TASK = asyncio.create_task(worker_loop(), name="ingestion_worker")
    logger.info("ingestion.worker.task_created")
    return WORKER_TASK


def stop_worker() -> None:
    """Signal the worker to stop gracefully."""
    global WORKER_RUNNING, WORKER_TASK
    WORKER_RUNNING = False
    if WORKER_TASK is not None and not WORKER_TASK.done():
        WORKER_TASK.cancel()
        logger.info("ingestion.worker.stop_requested")
