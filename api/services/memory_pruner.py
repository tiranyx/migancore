"""
Memory Pruning Daemon (Day 27).

Background asyncio task that periodically deletes old, low-importance points
from Qdrant episodic collections to prevent unbounded growth.

Scheduling:
    - Runs once per 24h (default)
    - Designed to be launched from FastAPI lifespan as `asyncio.create_task()`
    - Wraps each iteration in try/except so a single failure doesn't kill loop

Strategy (from research):
    - Hybrid: time-based (>30d) + importance-based (<0.7) — protects pinned memories
    - Avoids Qdrant collection-level TTL (kills important memories indiscriminately)
    - Requires payload index on `timestamp` for efficient delete-by-filter
      (without index → full scan, ~50× slower at 500K points)
    - Run `optimize` after large deletes to reclaim disk

Pitfalls handled:
    - asyncio task dies silently on uncaught exception → wrapped in try/except + retry
    - First-run before any indexing → no-op (no collections exist yet)
"""
from __future__ import annotations

import asyncio
import time
from typing import List

import structlog

from config import settings

logger = structlog.get_logger()

# How often to run pruning (seconds). 24h default.
PRUNE_INTERVAL_SECONDS = 24 * 60 * 60

# Sleep BEFORE first run — give app time to start cleanly.
PRUNE_INITIAL_DELAY_SECONDS = 5 * 60  # 5 min after startup

# How long to wait after a failed iteration before retrying
PRUNE_RETRY_AFTER_FAIL_SECONDS = 60 * 60  # 1 hour


async def _list_episodic_collections(client) -> List[str]:
    """Find all collections matching the episodic_<agent_id> pattern."""
    try:
        cols = await client.get_collections()
        return [c.name for c in cols.collections if c.name.startswith("episodic_")]
    except Exception as exc:
        logger.warning("memory_pruner.list_collections_failed", error=str(exc))
        return []


async def _ensure_indexes(client, collection_name: str) -> None:
    """Create payload indexes if missing — required for efficient filter delete.

    Idempotent — Qdrant returns success even if index already exists.
    """
    from qdrant_client.models import PayloadSchemaType
    for field, schema in [
        ("timestamp", PayloadSchemaType.INTEGER),
        ("importance", PayloadSchemaType.FLOAT),
    ]:
        try:
            await client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=schema,
                wait=False,
            )
        except Exception:
            # already exists or schema mismatch — ignore (defense in depth)
            pass


async def _prune_collection(client, collection_name: str, days: int, importance_max: float) -> int:
    """Prune one collection. Returns approximate deleted count (best-effort).

    Filter: timestamp < cutoff AND importance < importance_max
    Points without `importance` field are NOT pruned (default = pinned).
    """
    from qdrant_client.models import (
        Filter, FieldCondition, Range,
    )

    cutoff = int(time.time()) - days * 86400

    # Make sure indexes exist
    await _ensure_indexes(client, collection_name)

    # Build filter: timestamp range + importance range
    # Using two separate filter conditions joined by `must`
    filter_obj = Filter(
        must=[
            FieldCondition(key="timestamp", range=Range(lt=cutoff)),
            FieldCondition(key="importance", range=Range(lt=importance_max)),
        ]
    )

    # Count first (best-effort, may fail if no points match)
    try:
        before = await client.count(
            collection_name=collection_name,
            count_filter=filter_obj,
            exact=False,
        )
        before_count = before.count
    except Exception:
        before_count = -1

    if before_count == 0:
        return 0

    try:
        await client.delete(
            collection_name=collection_name,
            points_selector=filter_obj,
            wait=False,
        )
    except Exception as exc:
        logger.warning(
            "memory_pruner.delete_failed",
            collection=collection_name,
            error=str(exc),
        )
        return -1

    return before_count


async def prune_once() -> dict:
    """Run one pruning pass across all episodic collections.

    Returns summary dict for logging.
    """
    from services.vector_memory import _get_client

    client = await _get_client()
    collections = await _list_episodic_collections(client)

    if not collections:
        return {"collections": 0, "pruned": 0}

    total_pruned = 0
    per_collection = []
    for col in collections:
        deleted = await _prune_collection(
            client,
            col,
            days=settings.MEMORY_PRUNE_DAYS,
            importance_max=settings.MEMORY_PRUNE_IMPORTANCE_MAX,
        )
        per_collection.append({"collection": col, "deleted_approx": deleted})
        if deleted > 0:
            total_pruned += deleted

    return {
        "collections": len(collections),
        "pruned": total_pruned,
        "per_collection": per_collection,
        "policy": {
            "days": settings.MEMORY_PRUNE_DAYS,
            "importance_max": settings.MEMORY_PRUNE_IMPORTANCE_MAX,
        },
    }


async def prune_loop() -> None:
    """Forever-loop daemon. Launch via asyncio.create_task() from lifespan.

    Safety:
        - Sleeps PRUNE_INITIAL_DELAY before first run (let app warm up)
        - Wraps each iteration in try/except (silent death prevention)
        - On failure, sleeps shorter retry interval
    """
    logger.info(
        "memory_pruner.loop_starting",
        initial_delay_s=PRUNE_INITIAL_DELAY_SECONDS,
        interval_s=PRUNE_INTERVAL_SECONDS,
    )
    await asyncio.sleep(PRUNE_INITIAL_DELAY_SECONDS)

    while True:
        try:
            summary = await prune_once()
            logger.info("memory_pruner.run_done", **summary)
        except asyncio.CancelledError:
            logger.info("memory_pruner.loop_cancelled")
            raise
        except Exception as exc:
            logger.error("memory_pruner.run_failed", error=str(exc))
            await asyncio.sleep(PRUNE_RETRY_AFTER_FAIL_SECONDS)
            continue

        await asyncio.sleep(PRUNE_INTERVAL_SECONDS)
