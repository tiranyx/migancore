"""
Synthetic conversation generator — DPO data flywheel accelerator (Day 19+21).

Problem: Only 3 real preference pairs after Day 18. Need 1000+ for SimPO training.
Real user traffic too sparse on CPU-only VPS without a user base.

Solution: Synthetic data generation using Triple-Source Seed Architecture.
  - 120 diverse seed messages across 7 domains (see seed_bank.py)
  - Each seed: Ollama generates initial response (T=0.7) → CAI critique → revise if needed
  - Expected yield: ~50-60 pairs per run (40-50% pass critique threshold ≤3)

Architecture:
  - asyncio.Task: runs fully async, never blocks HTTP responses
  - asyncio.Lock: only one generation run at a time (CPU-only VPS constraint)
  - Redis tracking: status, run_id, round, cumulative_stored, target_pairs, total/processed/stored
  - Graceful cancellation: CancelledError sets status="cancelled" in Redis
  - source_method="synthetic_seed_v1": tagged for easy exclusion from real-data training

Auto-rerun (Day 21):
  - start_synthetic_generation(target_pairs=1000): loops rounds automatically until
    the DB total of synthetic pairs >= target. Each round runs all 120 seeds.
  - New run_id generated per round (traceability). cumulative_stored tracks total.
  - Safety: if a round yields 0 pairs (Ollama down?), stops with status="error".
  - stop_synthetic_generation() cancels immediately at any point in any round.

Safety:
  - Seeds are question templates, not domain-specific facts
  - CAI pipeline provides quality filter — only revised pairs stored
  - source_method tag allows separating synthetic vs real data at training time
  - Pairs can be excluded by filtering source_method != "cai_pipeline"

Usage:
  # Single run (original behavior):
  success, run_id, msg = await start_synthetic_generation()

  # Auto-rerun until target:
  success, run_id, msg = await start_synthetic_generation(target_pairs=1000)

  # Monitor:
  status = await get_synthetic_status()

  # Cancel:
  ok, msg = await stop_synthetic_generation()
"""

import asyncio
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
import structlog

from config import settings
from services.cai_pipeline import (
    _CAI_TIMEOUT,
    CRITIQUE_THRESHOLD,
    JUDGE_MODEL,
    _critique,
    _revise,
    _store_preference_pair,
)
from services.ollama import OllamaClient, OllamaError
from services.seed_bank import SEEDS

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Redis keys
# ---------------------------------------------------------------------------
_KEY_STATUS = "synthetic:status"
_KEY_RUN_ID = "synthetic:run_id"
_KEY_TOTAL = "synthetic:total"
_KEY_PROCESSED = "synthetic:processed"
_KEY_STORED = "synthetic:stored"
_KEY_STARTED_AT = "synthetic:started_at"
# Day 21 — auto-rerun tracking
_KEY_ROUND = "synthetic:round"
_KEY_CUMULATIVE_STORED = "synthetic:cumulative_stored"
_KEY_TARGET_PAIRS = "synthetic:target_pairs"

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_current_task: asyncio.Task | None = None
_task_lock = asyncio.Lock()

# ---------------------------------------------------------------------------
# Redis pool — reuses same pattern as services/memory.py
# ---------------------------------------------------------------------------
_pool: aioredis.ConnectionPool | None = None
_pool_lock = asyncio.Lock()

_GENERATE_MAX_TOKENS: int = 400  # Matches CAI revision token budget


async def _get_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = aioredis.ConnectionPool.from_url(
                    settings.REDIS_URL,
                    max_connections=5,
                    decode_responses=True,
                )
    return _pool


async def _redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=await _get_pool())


async def _count_synthetic_pairs() -> int:
    """Count total synthetic preference pairs currently in the DB.

    Used by auto-rerun to check progress toward target_pairs.
    Counts all rows where source_method starts with 'synthetic' —
    includes pairs from previous sessions and previous runs.
    Returns 0 on any error (conservative — allows another round to run).
    """
    import models.base as _models_base
    from sqlalchemy import text as _text

    if _models_base.AsyncSessionLocal is None:
        logger.warning("synthetic.count_db_unavailable")
        return 0
    try:
        async with _models_base.AsyncSessionLocal() as db:
            result = await db.execute(
                _text(
                    "SELECT COUNT(*) FROM preference_pairs "
                    "WHERE source_method LIKE 'synthetic%'"
                )
            )
            return int(result.scalar_one() or 0)
    except Exception as exc:
        logger.warning("synthetic.count_error", error=str(exc))
        return 0


# ---------------------------------------------------------------------------
# Core generation logic
# ---------------------------------------------------------------------------

async def _generate_initial_response(user_message: str) -> str | None:
    """Generate initial assistant response for a seed message.

    Temperature=0.7 for response diversity across re-runs.
    Uses same judge model (qwen2.5:7b) as CAI pipeline.
    Returns None on any failure — caller handles gracefully.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "Kamu adalah AI asisten yang membantu pengguna dengan berbagai tugas. "
                "Jawab pertanyaan dengan jelas, relevan, dan memberikan nilai nyata. "
                "Gunakan bahasa yang sama dengan pengguna."
            ),
        },
        {"role": "user", "content": user_message},
    ]
    try:
        async with OllamaClient(timeout=_CAI_TIMEOUT) as client:
            data = await client.chat(
                model=JUDGE_MODEL,
                messages=messages,
                options={"num_predict": _GENERATE_MAX_TOKENS, "temperature": 0.7},
            )
        response = data.get("message", {}).get("content", "").strip()
        if not response or len(response) < 20:
            logger.warning("synthetic.generate_too_short", length=len(response))
            return None
        return response
    except OllamaError as exc:
        logger.warning("synthetic.generate_ollama_error", error=str(exc))
        return None
    except Exception as exc:
        logger.warning("synthetic.generate_error", error=str(exc))
        return None


async def _process_seed(
    r: aioredis.Redis,
    seed_msg: str,
    run_id: str,
    processed: int,
    stored: int,
) -> tuple[int, int]:
    """Process one seed message through the full CAI pipeline.

    Returns (processed+1, stored) or (processed+1, stored+1) if a pair was stored.
    Raises asyncio.CancelledError — caller must handle.
    """
    # Generate initial response
    initial_response = await _generate_initial_response(seed_msg)
    if not initial_response:
        logger.warning("synthetic.generate_failed", seed_preview=seed_msg[:60])
        processed += 1
        await r.set(_KEY_PROCESSED, processed)
        return processed, stored

    # CAI critique
    critique = await _critique(seed_msg, initial_response)
    if critique is None:
        processed += 1
        await r.set(_KEY_PROCESSED, processed)
        return processed, stored

    score = critique["score"]
    logger.debug(
        "synthetic.critique_done",
        score=score,
        run_id=run_id,
        seed_preview=seed_msg[:60],
    )

    if score > CRITIQUE_THRESHOLD:
        # Response already good (4-5) — no pair generated (CAI design)
        logger.debug("synthetic.response_ok_skip", score=score)
        processed += 1
        await r.set(_KEY_PROCESSED, processed)
        return processed, stored

    # Score <= 3: revise and store as preference pair
    revised = await _revise(seed_msg, initial_response, critique)
    if not revised:
        processed += 1
        await r.set(_KEY_PROCESSED, processed)
        return processed, stored

    # chosen=revised (better), rejected=initial (worse)
    await _store_preference_pair(
        prompt=seed_msg,
        chosen=revised,
        rejected=initial_response,
        score=float(score),
        source_message_id=None,
        source_method="synthetic_seed_v1",
    )
    stored += 1
    processed += 1

    pipe = r.pipeline()
    pipe.set(_KEY_PROCESSED, processed)
    pipe.set(_KEY_STORED, stored)
    await pipe.execute()

    logger.info(
        "synthetic.pair_stored",
        run_id=run_id,
        processed=processed,
        stored=stored,
        score=score,
    )
    return processed, stored


# ---------------------------------------------------------------------------
# Main generation task
# ---------------------------------------------------------------------------

async def run_synthetic_generation(
    run_id: str,
    auto_target: int | None = None,
) -> None:
    """Main synthetic generation loop — runs as asyncio background task.

    Processes all 120 seeds sequentially (CPU-only VPS constraint).
    Tracks progress in Redis. Handles cancellation gracefully.

    If auto_target is set, loops over all seeds in multiple rounds until
    the total DB count of synthetic pairs >= auto_target, or cancelled.
    Each round gets a fresh run_id for traceability.

    Flow per seed:
      1. Generate initial response (T=0.7)
      2. CAI critique against Constitution principles
      3. If score <= CRITIQUE_THRESHOLD: revise + store as DPO preference pair

    Redis state:
      synthetic:round            — current round number (1-based)
      synthetic:cumulative_stored — total pairs stored across all rounds
      synthetic:target_pairs     — target set by caller (empty string = single run)
    """
    r = await _redis()
    seeds = list(SEEDS)  # snapshot — never mutate module constant

    round_num = 1
    cumulative_stored = 0
    overall_start = datetime.now(timezone.utc).isoformat()

    # Write overall run metadata to Redis (persists across rounds)
    pipe = r.pipeline()
    pipe.set(_KEY_STARTED_AT, overall_start)
    pipe.set(_KEY_TARGET_PAIRS, str(auto_target) if auto_target is not None else "")
    pipe.set(_KEY_ROUND, round_num)
    pipe.set(_KEY_CUMULATIVE_STORED, 0)
    await pipe.execute()

    logger.info(
        "synthetic.run_started",
        run_id=run_id,
        auto_target=auto_target,
        total_seeds=len(seeds),
    )

    try:
        while True:
            # Init per-round counters atomically
            pipe = r.pipeline()
            pipe.set(_KEY_STATUS, "running")
            pipe.set(_KEY_RUN_ID, run_id)
            pipe.set(_KEY_TOTAL, len(seeds))
            pipe.set(_KEY_PROCESSED, 0)
            pipe.set(_KEY_STORED, 0)
            pipe.set(_KEY_ROUND, round_num)
            await pipe.execute()

            logger.info(
                "synthetic.round_started",
                run_id=run_id,
                round=round_num,
                cumulative_so_far=cumulative_stored,
            )

            stored = 0
            processed = 0

            for seed_msg in seeds:
                try:
                    processed, stored = await _process_seed(
                        r, seed_msg, run_id, processed, stored
                    )
                    # Keep cumulative up to date in Redis after every successful store
                    await r.set(_KEY_CUMULATIVE_STORED, cumulative_stored + stored)
                except asyncio.CancelledError:
                    raise  # Bubble to outer try — sets status=cancelled
                except Exception as exc:
                    logger.warning(
                        "synthetic.seed_error",
                        error=str(exc),
                        seed_preview=seed_msg[:60],
                    )
                    processed += 1
                    await r.set(_KEY_PROCESSED, processed)

            # Round finished — update cumulative total
            cumulative_stored += stored
            await r.set(_KEY_CUMULATIVE_STORED, cumulative_stored)

            logger.info(
                "synthetic.round_complete",
                run_id=run_id,
                round=round_num,
                processed=processed,
                stored=stored,
                cumulative_stored=cumulative_stored,
            )

            # ── Single-run mode (no target) ──────────────────────────────
            if auto_target is None:
                await r.set(_KEY_STATUS, "done")
                break

            # ── Safety: abort if this round yielded nothing ───────────────
            # (All Ollama calls failed — likely service down. Don't loop forever.)
            if stored == 0:
                await r.set(_KEY_STATUS, "error")
                logger.warning(
                    "synthetic.zero_yield_abort",
                    round=round_num,
                    msg="All seeds failed this round — possible Ollama outage. Aborting auto-rerun.",
                )
                break

            # ── Check DB total vs target ──────────────────────────────────
            total_in_db = await _count_synthetic_pairs()
            logger.info(
                "synthetic.target_check",
                db_count=total_in_db,
                target=auto_target,
                remaining=max(0, auto_target - total_in_db),
                round=round_num,
            )

            if total_in_db >= auto_target:
                await r.set(_KEY_STATUS, "done_target_reached")
                logger.info(
                    "synthetic.target_reached",
                    total_in_db=total_in_db,
                    target=auto_target,
                    rounds_completed=round_num,
                )
                break

            # ── Prepare next round ─────────────────────────────────────────
            round_num += 1
            run_id = str(uuid.uuid4())
            logger.info(
                "synthetic.next_round",
                new_run_id=run_id,
                round=round_num,
                remaining=auto_target - total_in_db,
            )

    except asyncio.CancelledError:
        await r.set(_KEY_STATUS, "cancelled")
        logger.info(
            "synthetic.run_cancelled",
            run_id=run_id,
            round=round_num,
            cumulative_stored=cumulative_stored,
        )

    except Exception as exc:
        await r.set(_KEY_STATUS, "error")
        logger.warning("synthetic.run_error", run_id=run_id, error=str(exc))


# ---------------------------------------------------------------------------
# Public API (called from admin endpoints)
# ---------------------------------------------------------------------------

async def get_synthetic_status() -> dict:
    """Read current synthetic generation status from Redis.

    Returns dict with status, run_id, round, total, processed, stored,
    cumulative_stored, target_pairs, started_at, is_running, progress_pct.

    New in Day 21 (auto-rerun):
      round            — current round number (1 = single-run mode)
      cumulative_stored — total pairs stored across all rounds this session
      target_pairs     — auto-rerun target (None = single-run mode)
    """
    try:
        r = await _redis()
        values = await r.mget(
            _KEY_STATUS,
            _KEY_RUN_ID,
            _KEY_TOTAL,
            _KEY_PROCESSED,
            _KEY_STORED,
            _KEY_STARTED_AT,
            _KEY_ROUND,
            _KEY_CUMULATIVE_STORED,
            _KEY_TARGET_PAIRS,
        )
        status, run_id, total, processed, stored, started_at, \
            round_num, cumulative_stored, target_pairs = values

        is_running = _current_task is not None and not _current_task.done()
        progress_pct = 0.0
        if total and int(total) > 0:
            progress_pct = round((int(processed or 0) / int(total)) * 100, 1)

        return {
            "status": status or "idle",
            "run_id": run_id,
            "round": int(round_num) if round_num else 1,
            "total": int(total) if total else 0,
            "processed": int(processed) if processed else 0,
            "stored": int(stored) if stored else 0,
            "cumulative_stored": int(cumulative_stored) if cumulative_stored else 0,
            "target_pairs": int(target_pairs) if target_pairs else None,
            "started_at": started_at,
            "is_running": is_running,
            "progress_pct": progress_pct,
        }
    except Exception as exc:
        logger.warning("synthetic.status_error", error=str(exc))
        return {
            "status": "unknown",
            "run_id": None,
            "round": 1,
            "total": 0,
            "processed": 0,
            "stored": 0,
            "cumulative_stored": 0,
            "target_pairs": None,
            "started_at": None,
            "is_running": False,
            "progress_pct": 0.0,
        }


async def start_synthetic_generation(
    target_pairs: int | None = None,
) -> tuple[bool, str, str]:
    """Start a new synthetic generation run.

    Args:
        target_pairs: If set, auto-rerun rounds until total synthetic pairs
                      in DB >= target_pairs. If None, run exactly one round (120 seeds).

    Returns (success, run_id, message).
    Returns (False, "", message) if already running.

    Only one run allowed at a time — CPU-only VPS constraint.
    """
    global _current_task

    async with _task_lock:
        if _current_task is not None and not _current_task.done():
            return False, "", "Synthetic generation already running. Use /status to monitor or /stop to cancel."

        run_id = str(uuid.uuid4())
        _current_task = asyncio.create_task(
            run_synthetic_generation(run_id, auto_target=target_pairs),
            name=f"synthetic_gen_{run_id[:8]}",
        )
        logger.info("synthetic.task_created", run_id=run_id, target_pairs=target_pairs)

        if target_pairs is not None:
            msg = (
                f"Synthetic auto-rerun started — target: {target_pairs} pairs. "
                f"Rounds will continue until DB total >= {target_pairs}. "
                f"Seeds per round: {len(SEEDS)}."
            )
        else:
            msg = f"Synthetic generation started with {len(SEEDS)} seeds (single run)."

        return True, run_id, msg


async def stop_synthetic_generation() -> tuple[bool, str]:
    """Cancel the current synthetic generation run.

    Returns (success, message).
    Does not await cancellation — Redis status updates to 'cancelled' async.
    """
    global _current_task

    async with _task_lock:
        if _current_task is None or _current_task.done():
            return False, "No synthetic generation is currently running."

        _current_task.cancel()
        logger.info("synthetic.task_cancel_requested")
        return True, "Cancellation requested. Status will update to 'cancelled' shortly."
