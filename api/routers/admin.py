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
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status
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

async def _check_admin_rate_limit(client_ip: str, max_per_min: int = 10) -> None:
    """Day 48 [H2] — Redis-backed per-IP rate limit on admin endpoints.

    Defends against brute-force of ADMIN_SECRET_KEY. Counts ALL admin
    requests per IP per minute (failed AND successful), since legit admin
    use is bursty-low (a few clicks per minute at most).

    Silent on Redis failure — never block admin during infra issue.
    """
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        # Fixed-window counter: bucket per (IP, minute)
        bucket = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        key = f"admin:ratelimit:{client_ip}:{bucket}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, 65)  # bucket lifetime + small grace
        await r.aclose()
        if count > max_per_min:
            logger.warning(
                "admin.rate_limit_exceeded",
                ip=client_ip,
                count=count,
                limit=max_per_min,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Admin rate limit exceeded ({max_per_min}/min per IP).",
                headers={"Retry-After": "60"},
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Redis down or other — log but don't block (admin must stay reachable)
        logger.warning("admin.rate_limit_check_failed", error=str(exc))


async def require_admin_key(
    request: Request,
    x_admin_key: Optional[str] = Header(default=None),
) -> None:
    """Validate X-Admin-Key header against settings.ADMIN_SECRET_KEY.

    Day 48: Now also enforces per-IP rate limit (10/min) to defend against
    brute-force of ADMIN_SECRET_KEY ([H2] from QA_FULLREVIEW Sprint 2).

    Raises:
      503 if admin is not configured (empty key in settings)
      429 if rate limit exceeded
      401 if the provided key does not match
    """
    if not settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin endpoints not configured. Set ADMIN_SECRET_KEY in environment.",
        )
    # Rate-limit FIRST so wrong-key attempts are throttled before they leak timing
    client_ip = request.client.host if request.client else "unknown"
    # Trust X-Forwarded-For only when nginx terminates TLS for us — already
    # validated upstream in nginx config. Take leftmost (real client).
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        client_ip = fwd.split(",")[0].strip() or client_ip
    await _check_admin_rate_limit(client_ip)

    if not secrets.compare_digest(x_admin_key or "", settings.ADMIN_SECRET_KEY):
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
    # Build query using SQLAlchemy Core (safe from SQL injection)
    from sqlalchemy import select, and_

    stmt_count = select(func.count()).select_from(PreferencePair)
    stmt_rows = select(
        PreferencePair.id,
        PreferencePair.prompt,
        PreferencePair.chosen,
        PreferencePair.rejected,
        PreferencePair.judge_score,
        PreferencePair.judge_model,
        PreferencePair.source_method,
        PreferencePair.source_message_id,
        PreferencePair.created_at,
        PreferencePair.used_in_training_run_id,
    ).order_by(PreferencePair.created_at.desc())

    filters = []
    if score_max is not None:
        filters.append(PreferencePair.judge_score <= score_max)
    if unused_only:
        filters.append(PreferencePair.used_in_training_run_id.is_(None))

    if filters:
        stmt_count = stmt_count.where(and_(*filters))
        stmt_rows = stmt_rows.where(and_(*filters))

    stmt_rows = stmt_rows.limit(limit).offset(offset)

    # Count total matching
    total_matching: int = (await db.execute(stmt_count)).scalar_one()

    # Fetch page
    rows_result = await db.execute(stmt_rows)

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
    from sqlalchemy import select, and_

    stmt = select(
        PreferencePair.prompt,
        PreferencePair.chosen,
        PreferencePair.rejected,
        PreferencePair.judge_score,
    ).order_by(PreferencePair.judge_score.asc(), PreferencePair.created_at.desc())

    filters = [PreferencePair.judge_score <= score_max]
    if unused_only:
        filters.append(PreferencePair.used_in_training_run_id.is_(None))

    stmt = stmt.where(and_(*filters)).limit(limit)

    result = await db.execute(stmt)
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

    NOTE: agents table has RLS — must iterate per tenant_id with set_tenant_context.
    Single global query returns 0 rows because no tenant context is active.
    """
    from deps.db import set_tenant_context

    # 1. List all tenants (tenants table has no RLS policy blocking admin)
    tenants_res = await db.execute(text("SELECT id, name FROM tenants"))
    tenants = [(str(r[0]), r[1]) for r in tenants_res.fetchall()]

    all_agents = []
    for tenant_id, tenant_name in tenants:
        try:
            await set_tenant_context(db, tenant_id)
            agents_res = await db.execute(
                text(
                    "SELECT id, name, parent_agent_id, generation, template_id, "
                    "status, created_at, model_version, tenant_id "
                    "FROM agents WHERE status != 'archived' "
                    "ORDER BY generation ASC, created_at ASC"
                )
            )
            for r in agents_res.fetchall():
                all_agents.append({
                    "id": str(r[0]),
                    "name": r[1],
                    "parent_id": str(r[2]) if r[2] else None,
                    "generation": r[3],
                    "template_id": r[4],
                    "status": r[5],
                    "created_at": r[6].isoformat() if r[6] else None,
                    "model_version": r[7],
                    "tenant_id": str(r[8]),
                    "tenant_name": tenant_name,
                })
        except Exception as exc:
            logger.warning("admin.genealogy.tenant_failed", tenant_id=tenant_id, error=str(exc))

    return all_agents


# ---------------------------------------------------------------------------
# Clone mechanism (Day 67, GAP-01) — P0 for first paid client
# ---------------------------------------------------------------------------

class CloneRequestBody(BaseModel):
    """HTTP request body for POST /v1/admin/clone."""
    client_name: str = Field(..., description="Legal name of client organization")
    ado_display_name: str = Field(..., description="White-label ADO name, e.g. SARI or LEX")
    tier: str = Field("PERAK", description="BERLIAN / EMAS / PERAK / PERUNGGU")
    language_pack: list[str] = Field(["id", "en"])
    vps_ip: str = Field(..., description="Client VPS IP address")
    vps_ssh_port: int = Field(22)
    vps_ssh_key_path: str = Field(..., description="Path to SSH key on THIS server")
    ado_domain: Optional[str] = Field(None)
    ollama_model: str = Field("qwen2.5:7b-instruct-q4_K_M")
    admin_email: str = Field(...)
    admin_password: str = Field(...)
    deploy_dir: str = Field("/opt/ado-client")
    dry_run: bool = Field(False, description="Simulate only — no real SSH/deploy")


@router.post("/clone", dependencies=[Depends(require_admin_key)])
async def admin_clone(body: CloneRequestBody):
    """
    Launch ADO clone pipeline for a client VPS.

    Steps (async, returns immediately with result after all steps complete):
      1. Detect client VPS spec (RAM, CPU, disk)
      2. Mint license (requires LICENSE_ISSUER_MODE=true)
      3. Render docker-compose.yml + setup_ado.sh from templates
      4. Deploy: SCP files to client VPS + run setup wizard
      5. Verify /health on deployed instance

    Use dry_run=true to simulate all steps without real SSH.

    Auth: X-Admin-Key required.
    """
    from services.clone_manager import CloneManager, CloneRequest

    req = CloneRequest(
        client_name=body.client_name,
        ado_display_name=body.ado_display_name,
        tier=body.tier,
        language_pack=body.language_pack,
        vps_ip=body.vps_ip,
        vps_ssh_port=body.vps_ssh_port,
        vps_ssh_key_path=body.vps_ssh_key_path,
        ado_domain=body.ado_domain,
        ollama_model=body.ollama_model,
        admin_email=body.admin_email,
        admin_password=body.admin_password,
        deploy_dir=body.deploy_dir,
        dry_run=body.dry_run,
    )

    manager = CloneManager()
    result = await manager.clone(req)

    http_status = 200 if result.status.value in ("LIVE",) else 422
    if result.status.value == "FAILED":
        http_status = 500

    return {
        "clone_id":        result.clone_id,
        "status":          result.status.value,
        "client_name":     result.client_name,
        "ado_display_name": result.ado_display_name,
        "license_id":      result.license_id,
        "vps_ip":          result.vps_ip,
        "api_url":         result.api_url,
        "health_status":   result.health_status,
        "error":           result.error,
        "created_at":      result.created_at,
        "log":             result.log,
    }


@router.get("/clone/dry-run", dependencies=[Depends(require_admin_key)])
async def admin_clone_dry_run(
    client_name: str = Query("Test Client"),
    ado_display_name: str = Query("TEST"),
    tier: str = Query("PERAK"),
    vps_ip: str = Query("127.0.0.1"),
    vps_ssh_key_path: str = Query("/opt/secrets/migancore/id_ed25519_client"),
    admin_email: str = Query("admin@test.com"),
    admin_password: str = Query("TestPass123!"),
):
    """
    Quick dry-run test for clone pipeline. Uses query params for convenience.
    Does NOT SSH anywhere — validates templates + license minting only.
    """
    from services.clone_manager import CloneManager, CloneRequest

    req = CloneRequest(
        client_name=client_name,
        ado_display_name=ado_display_name,
        tier=tier,
        vps_ip=vps_ip,
        vps_ssh_key_path=vps_ssh_key_path,
        admin_email=admin_email,
        admin_password=admin_password,
        dry_run=True,
    )

    manager = CloneManager()
    result = await manager.clone(req)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Day 76 — Thinking Mode Metrics
# ---------------------------------------------------------------------------

@router.get("/mode-stats")
async def get_mode_stats(
    hours: int = Query(24, ge=1, le=168),
    admin_key: str = Header("", alias="X-Admin-Key"),
):
    """Get thinking mode detection statistics.
    
    Returns:
        - Mode distribution (which modes were detected)
        - Average confidence per mode
        - Override rate (user vs auto-detected)
        - Detection latency stats
    """
    if not settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Admin not configured")
    if not secrets.compare_digest(admin_key, settings.ADMIN_SECRET_KEY):
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    from core.cognitive.metrics import mode_metrics
    
    stats = await mode_metrics.get_stats(hours=hours)
    return {
        "status": "ok",
        "period_hours": hours,
        **stats,
    }


@router.get("/mode-test")
async def test_mode_detection(
    message: str = Query(..., min_length=1),
    admin_key: str = Header("", alias="X-Admin-Key"),
):
    """Test mode detection on a sample message (no side effects).
    
    Useful for debugging mode selection logic without sending to LLM.
    """
    if not settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Admin not configured")
    if not secrets.compare_digest(admin_key, settings.ADMIN_SECRET_KEY):
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    from core.cognitive.mode_selector import ModeSelector
    from core.cognitive import _THINKING_MODE_INSTRUCTIONS
    
    mode, confidence = ModeSelector.select(message)
    instruction = _THINKING_MODE_INSTRUCTIONS.get(mode, "")
    
    return {
        "status": "ok",
        "input": message,
        "detected_mode": mode,
        "confidence": confidence,
        "instruction_length": len(instruction),
        "instruction_preview": instruction[:200] + "..." if len(instruction) > 200 else instruction,
    }
