"""
Admin endpoints — CAI flywheel monitoring and dataset export (Day 17).

Provides visibility into the preference_pairs training data flywheel:
  - /v1/admin/stats       → aggregate health metrics (pair count, quality, rate)
  - /v1/admin/preference-pairs → paginated pair listing with filters
  - /v1/admin/export      → JSONL download in Unsloth/TRL DPO-compatible format

Auth: X-Admin-Key header checked against settings.ADMIN_SECRET_KEY.
      Empty ADMIN_SECRET_KEY → 503 (admin not configured).
      Wrong key → 401.

All endpoints are READ-ONLY — no training data is mutated here.
Export marks nothing as "used" — that happens during the training run itself.

Training readiness thresholds (from Day 17 research, arxiv 2502.14560):
  - < 500 pairs  → "not_ready" (insufficient gradient signal)
  - 500–999      → "approaching" (experimental run possible, noisy results)
  - 1000+        → "ready" (first meaningful training run)
  - 2000+        → "ideal" (results statistically trustworthy)
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from deps.db import get_db
from models.preference_pair import PreferencePair

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/admin", tags=["admin"])

# Training readiness thresholds (Day 17 research: arxiv 2502.14560, Unsloth benchmarks)
_THRESHOLD_APPROACHING = 500
_THRESHOLD_READY = 1_000
_THRESHOLD_IDEAL = 2_000


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

async def require_admin_key(x_admin_key: Optional[str] = Header(default=None)) -> None:
    """Validate X-Admin-Key header against settings.ADMIN_SECRET_KEY.

    Raises 503 if admin is not configured (empty key in settings).
    Raises 401 if the provided key does not match.
    """
    if not settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin endpoints not configured. Set ADMIN_SECRET_KEY in environment.",
        )
    if x_admin_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key.",
            headers={"WWW-Authenticate": "X-Admin-Key"},
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/stats", dependencies=[Depends(require_admin_key)])
async def get_admin_stats(db: AsyncSession = Depends(get_db)):
    """Aggregate health metrics for the CAI preference data flywheel.

    Returns pair counts, quality distribution, collection rate,
    and a training readiness assessment with progress percentage.
    """
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)

    # Total pairs
    total_result = await db.execute(
        text("SELECT COUNT(*) FROM preference_pairs")
    )
    total: int = total_result.scalar_one()

    # Unused pairs (not yet consumed by a training run)
    unused_result = await db.execute(
        text("SELECT COUNT(*) FROM preference_pairs WHERE used_in_training_run_id IS NULL")
    )
    unused: int = unused_result.scalar_one()

    # Average judge score
    avg_result = await db.execute(
        text("SELECT AVG(judge_score) FROM preference_pairs")
    )
    avg_score_raw = avg_result.scalar_one()
    avg_score: float | None = round(float(avg_score_raw), 3) if avg_score_raw is not None else None

    # Score distribution (1–3, since only low-scored pairs are stored by CAI pipeline)
    dist_result = await db.execute(
        text(
            "SELECT ROUND(judge_score) AS bucket, COUNT(*) AS cnt "
            "FROM preference_pairs "
            "GROUP BY bucket ORDER BY bucket"
        )
    )
    score_distribution: dict[str, int] = {
        str(int(row.bucket)): int(row.cnt)
        for row in dist_result
    }

    # Recent collection rates
    last_24h_result = await db.execute(
        text("SELECT COUNT(*) FROM preference_pairs WHERE created_at >= :since"),
        {"since": since_24h},
    )
    last_24h: int = last_24h_result.scalar_one()

    last_7d_result = await db.execute(
        text("SELECT COUNT(*) FROM preference_pairs WHERE created_at >= :since"),
        {"since": since_7d},
    )
    last_7d: int = last_7d_result.scalar_one()

    # By source method
    method_result = await db.execute(
        text(
            "SELECT source_method, COUNT(*) AS cnt "
            "FROM preference_pairs "
            "GROUP BY source_method"
        )
    )
    by_source: dict[str, int] = {row.source_method: int(row.cnt) for row in method_result}

    # Training readiness assessment
    if unused < _THRESHOLD_APPROACHING:
        readiness_status = "not_ready"
        readiness_msg = (
            f"{unused} unused pairs available — minimum {_THRESHOLD_APPROACHING} needed for any training signal. "
            f"Keep conversations flowing; CAI pipeline samples at 50%."
        )
    elif unused < _THRESHOLD_READY:
        readiness_status = "approaching"
        readiness_msg = (
            f"{unused} unused pairs — approaching {_THRESHOLD_READY} minimum threshold. "
            f"Experimental run possible but expect noisy results. Wait for {_THRESHOLD_READY}+ for reliability."
        )
    elif unused < _THRESHOLD_IDEAL:
        readiness_status = "ready"
        readiness_msg = (
            f"{unused} unused pairs — READY for first training run (SimPO/DPO on RunPod). "
            f"Ideal target is {_THRESHOLD_IDEAL}+ for statistically trustworthy results."
        )
    else:
        readiness_status = "ideal"
        readiness_msg = (
            f"{unused} unused pairs — IDEAL dataset size. "
            f"Strong training signal. Proceed with SimPO on RunPod (~$3-8 per run)."
        )

    # Progress toward 1000-pair threshold (capped at 100%)
    progress_pct: float = min(round((unused / _THRESHOLD_READY) * 100, 1), 100.0)

    logger.info(
        "admin.stats_fetched",
        total=total,
        unused=unused,
        readiness=readiness_status,
        avg_score=avg_score,
    )

    return {
        "total_pairs": total,
        "unused_pairs": unused,
        "used_in_training": total - unused,
        "avg_judge_score": avg_score,
        "score_distribution": score_distribution,
        "collection_rate": {
            "last_24h": last_24h,
            "last_7d": last_7d,
            "daily_avg_7d": round(last_7d / 7, 1),
        },
        "by_source_method": by_source,
        "training_readiness": {
            "status": readiness_status,
            "message": readiness_msg,
            "progress_toward_1k_pct": progress_pct,
            "thresholds": {
                "approaching": _THRESHOLD_APPROACHING,
                "ready": _THRESHOLD_READY,
                "ideal": _THRESHOLD_IDEAL,
            },
        },
    }


@router.get("/preference-pairs", dependencies=[Depends(require_admin_key)])
async def list_preference_pairs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    score_max: Optional[float] = Query(default=None, ge=1.0, le=5.0,
                                        description="Filter: only pairs with judge_score <= this value"),
    unused_only: bool = Query(default=False, description="Filter: only pairs not yet used in training"),
    db: AsyncSession = Depends(get_db),
):
    """Paginated listing of preference pairs with optional filters.

    Use score_max=3 to see only the pairs CAI generates (score <= CRITIQUE_THRESHOLD).
    Use unused_only=True to see the dataset that will be fed to the next training run.
    """
    # Build filter conditions
    conditions = []
    params: dict = {}

    if score_max is not None:
        conditions.append("judge_score <= :score_max")
        params["score_max"] = score_max

    if unused_only:
        conditions.append("used_in_training_run_id IS NULL")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Count total matching
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM preference_pairs {where_clause}"),
        params,
    )
    total_matching: int = count_result.scalar_one()

    # Fetch page
    rows_result = await db.execute(
        text(
            f"SELECT id, prompt, chosen, rejected, judge_score, judge_model, "
            f"source_method, source_message_id, created_at, used_in_training_run_id "
            f"FROM preference_pairs {where_clause} "
            f"ORDER BY created_at DESC "
            f"LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": limit, "offset": offset},
    )

    items = []
    for row in rows_result:
        items.append({
            "id": str(row.id),
            "prompt": row.prompt,
            "chosen": row.chosen,
            "rejected": row.rejected,
            "judge_score": row.judge_score,
            "judge_model": row.judge_model,
            "source_method": row.source_method,
            "source_message_id": str(row.source_message_id) if row.source_message_id else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "used_in_training": row.used_in_training_run_id is not None,
        })

    logger.info(
        "admin.pairs_listed",
        total_matching=total_matching,
        limit=limit,
        offset=offset,
        filters={"score_max": score_max, "unused_only": unused_only},
    )

    return {
        "items": items,
        "total": total_matching,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total_matching,
    }


@router.get("/export", dependencies=[Depends(require_admin_key)])
async def export_dataset(
    score_max: float = Query(
        default=3.0, ge=1.0, le=5.0,
        description="Include pairs with judge_score <= this value (default: 3 = CAI threshold)",
    ),
    limit: int = Query(
        default=2000, ge=1, le=10000,
        description="Max pairs to export (default: 2000 = ideal DPO dataset size)",
    ),
    unused_only: bool = Query(
        default=True,
        description="Export only pairs not yet used in a training run",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Stream preference pairs as JSONL in Unsloth/TRL DPO-compatible format.

    Each line is a JSON object: {"prompt": "...", "chosen": "...", "rejected": "..."}
    This is the exact format expected by Unsloth DPOTrainer and TRL DPOTrainer.

    Usage:
        curl -H "X-Admin-Key: <key>" \\
             "https://api.migancore.com/v1/admin/export" \\
             -o training_data.jsonl

    Then in Unsloth:
        dataset = load_dataset("json", data_files="training_data.jsonl", split="train")
        trainer = DPOTrainer(model=model, train_dataset=dataset, ...)

    For SimPO (recommended over DPO for first run, arxiv 2405.14734):
        The same JSONL format works with SimPO via TRL SimPOTrainer.
    """
    conditions = ["judge_score <= :score_max"]
    params: dict = {"score_max": score_max, "limit": limit}

    if unused_only:
        conditions.append("used_in_training_run_id IS NULL")

    where_clause = f"WHERE {' AND '.join(conditions)}"

    result = await db.execute(
        text(
            f"SELECT prompt, chosen, rejected, judge_score "
            f"FROM preference_pairs {where_clause} "
            f"ORDER BY judge_score ASC, created_at DESC "  # lowest scores first = clearest signal
            f"LIMIT :limit"
        ),
        params,
    )
    rows = result.fetchall()

    logger.info(
        "admin.export_started",
        count=len(rows),
        score_max=score_max,
        unused_only=unused_only,
        limit=limit,
    )

    def generate_jsonl():
        """Yield one JSONL line per preference pair."""
        for row in rows:
            record = {
                "prompt": row.prompt,
                "chosen": row.chosen,
                "rejected": row.rejected,
            }
            yield json.dumps(record, ensure_ascii=False) + "\n"

    filename = f"migancore_dpo_{len(rows)}pairs_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
    return StreamingResponse(
        generate_jsonl(),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Total-Pairs": str(len(rows)),
        },
    )
