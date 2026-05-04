"""
Admin endpoints — CAI flywheel monitoring, dataset export, synthetic generation (Day 17+19).

Provides visibility and control over the preference_pairs training data flywheel:
  - /v1/admin/stats              → aggregate health metrics (pair count, quality, rate)
  - /v1/admin/preference-pairs   → paginated pair listing with filters
  - /v1/admin/export             → JSONL download in Unsloth/TRL DPO-compatible format
  - /v1/admin/synthetic/start    → start synthetic conversation generation (Day 19)
  - /v1/admin/synthetic/status   → monitor synthetic generation progress
  - /v1/admin/synthetic/stop     → cancel running synthetic generation

Auth: X-Admin-Key header checked against settings.ADMIN_SECRET_KEY.
      Empty ADMIN_SECRET_KEY → 503 (admin not configured).
      Wrong key → 401.

All endpoints are READ-ONLY except synthetic/start and synthetic/stop.
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
from pydantic import BaseModel, Field
from sqlalchemy import text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from deps.db import get_db
from models.preference_pair import PreferencePair
from services.synthetic_pipeline import (
    get_synthetic_status,
    start_synthetic_generation,
    stop_synthetic_generation,
)

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


# ---------------------------------------------------------------------------
# Synthetic generation endpoints (Day 19 + Day 21)
# ---------------------------------------------------------------------------

class SyntheticStartRequest(BaseModel):
    """Request body for POST /v1/admin/synthetic/start.

    target_pairs: If set, auto-rerun rounds until total synthetic pairs in DB
                  reaches this number. Each round processes 120 seeds.
                  If omitted, runs exactly one round (original behavior).
    """
    target_pairs: Optional[int] = Field(
        default=None,
        ge=1,
        le=10_000,
        description=(
            "Auto-rerun target: keep running rounds until synthetic pairs in DB >= this value. "
            "Omit for single-run mode (120 seeds, one round)."
        ),
    )


@router.post("/synthetic/start", dependencies=[Depends(require_admin_key)])
async def start_synthetic(body: SyntheticStartRequest = SyntheticStartRequest()):
    """Start a synthetic conversation generation run.

    Generates 120 seeds through the CAI pipeline to produce DPO preference pairs.
    Only one run allowed at a time (CPU-only VPS constraint).

    **Single-run mode** (default, no body):
      Processes 120 seeds once. ~50-60 pairs stored per run.
      curl -X POST -H "X-Admin-Key: <key>" .../synthetic/start

    **Auto-rerun mode** (Day 21):
      Loops rounds automatically until total synthetic pairs in DB >= target_pairs.
      Each round = 120 seeds. Stop anytime with POST /synthetic/stop.
      curl -X POST -H "X-Admin-Key: <key>" -H "Content-Type: application/json" \\
           -d '{"target_pairs": 1000}' .../synthetic/start

    Tracks progress at GET /v1/admin/synthetic/status (includes round, cumulative_stored, target_pairs).
    Tagged as source_method="synthetic_seed_v1" in preference_pairs table.
    """
    success, run_id, message = await start_synthetic_generation(
        target_pairs=body.target_pairs
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )

    logger.info(
        "admin.synthetic_started",
        run_id=run_id,
        target_pairs=body.target_pairs,
        mode="auto_rerun" if body.target_pairs else "single_run",
    )
    return {
        "run_id": run_id,
        "message": message,
        "mode": "auto_rerun" if body.target_pairs else "single_run",
        "target_pairs": body.target_pairs,
        "monitor": "/v1/admin/synthetic/status",
        "stop": "/v1/admin/synthetic/stop",
    }


@router.get("/synthetic/status", dependencies=[Depends(require_admin_key)])
async def synthetic_status():
    """Get current synthetic generation status and progress counters.

    Returns:
        status:            "idle" | "running" | "done" | "done_target_reached" | "cancelled" | "error"
        run_id:            UUID of current/last round
        round:             current round number (1 = single-run or first round of auto-rerun)
        total:             seeds per round (120)
        processed:         seeds processed in current round
        stored:            pairs stored in current round
        cumulative_stored: total pairs stored across all rounds this session
        target_pairs:      auto-rerun target (null = single-run mode)
        progress_pct:      processed/total × 100 for current round
        started_at:        ISO timestamp of first round start
        is_running:        True if task is active in event loop

    Usage:
        curl -H "X-Admin-Key: <key>" https://api.migancore.com/v1/admin/synthetic/status
    """
    status_data = await get_synthetic_status()
    logger.info("admin.synthetic_status_checked", status=status_data.get("status"))
    return status_data


@router.post("/synthetic/stop", dependencies=[Depends(require_admin_key)])
async def stop_synthetic():
    """Cancel the running synthetic generation.

    Cancellation is asynchronous — the task will update Redis status to 'cancelled'
    shortly after this call returns. Check /status to confirm.

    Returns 404 if no generation is running.

    Usage:
        curl -X POST -H "X-Admin-Key: <key>" https://api.migancore.com/v1/admin/synthetic/stop
    """
    success, message = await stop_synthetic_generation()
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    logger.info("admin.synthetic_stop_requested")
    return {"message": message}


# ---------------------------------------------------------------------------
# Distillation endpoints (Day 28)
# ---------------------------------------------------------------------------

class StartDistillRequest(BaseModel):
    teacher: str = Field(..., description="One of: kimi, claude, gpt, gemini")
    target_pairs: int = Field(default=30, ge=1, le=2000)
    judge_teacher: str = Field(default="claude", description="Independent judge teacher (default claude)")
    budget_cap_usd: Optional[float] = Field(default=None, description="Override default budget cap")


@router.post("/distill/start", dependencies=[Depends(require_admin_key)])
async def start_distill(body: StartDistillRequest):
    """Start a distillation run.

    Generates `target_pairs` DPO pairs by comparing MiganCore (student) vs the
    chosen teacher LLM, scored by an independent judge. Stores margin-passing
    pairs in preference_pairs with source_method='distill_<teacher>_v1'.

    Usage:
        curl -X POST -H "X-Admin-Key: <key>" -H "Content-Type: application/json" \
          -d '{"teacher":"kimi","target_pairs":30}' \
          https://api.migancore.com/v1/admin/distill/start
    """
    from services.distillation import start_distillation, list_available_teachers

    available = list_available_teachers()
    if body.teacher not in available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Teacher '{body.teacher}' not available. Available: {available}",
        )
    if body.judge_teacher not in available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Judge '{body.judge_teacher}' not available. Available: {available}",
        )

    result = await start_distillation(
        teacher=body.teacher,
        target_pairs=body.target_pairs,
        judge_teacher=body.judge_teacher,
        budget_cap_usd=body.budget_cap_usd,
    )
    if result.get("status") == "rejected":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result)
    return result


@router.get("/distill/status", dependencies=[Depends(require_admin_key)])
async def distill_status():
    """Live status of the current distillation run (if any)."""
    from services.distillation import get_run_status, list_available_teachers
    cur = await get_run_status()
    return {
        "current_run": cur,
        "available_teachers": list_available_teachers(),
    }


@router.post("/distill/stop", dependencies=[Depends(require_admin_key)])
async def distill_stop():
    """Cancel the running distillation."""
    from services.distillation import stop_distillation
    return await stop_distillation()


@router.get("/distill/summary", dependencies=[Depends(require_admin_key)])
async def distill_summary():
    """Aggregate stats per teacher across all distillation runs."""
    from services.distillation import get_distill_summary
    return await get_distill_summary()


# ---------------------------------------------------------------------------
# Genealogy view (Day 30) — system-wide for admin dashboard
# ---------------------------------------------------------------------------

@router.get("/genealogy", dependencies=[Depends(require_admin_key)])
async def admin_genealogy(db: AsyncSession = Depends(get_db)):
    """System-wide agent genealogy across ALL tenants (admin only).

    Used by dashboard.html Lineage tab to render D3.js force-directed graph.
    """
    from models.agent import Agent

    result = await db.execute(
        text(
            "SELECT a.id, a.name, a.parent_agent_id, a.generation, a.template_id, "
            "a.status, a.created_at, a.model_version, a.tenant_id, t.name AS tenant_name "
            "FROM agents a "
            "LEFT JOIN tenants t ON t.id = a.tenant_id "
            "WHERE a.status != 'archived' "
            "ORDER BY a.generation ASC, a.created_at ASC"
        )
    )
    rows = result.fetchall()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "parent_id": str(r.parent_agent_id) if r.parent_agent_id else None,
            "generation": r.generation,
            "template_id": r.template_id,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "model_version": r.model_version,
            "tenant_id": str(r.tenant_id),
            "tenant_name": r.tenant_name,
        }
        for r in rows
    ]
