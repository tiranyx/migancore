"""
MiganCore API â€” FastAPI Gateway
Entry point for the autonomous digital organism.
"""

import asyncio
import os
import subprocess
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
import structlog


# â”€â”€â”€ Day 68 (Codex C4): build metadata exposed via /health â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Computed once at import time so subsequent /health calls are O(1).
# Falls back to env vars if git not available (e.g. inside slim Docker image).
def _resolve_build_metadata() -> tuple[str, str, str]:
    sha = os.getenv("BUILD_COMMIT_SHA", "")
    build_time = os.getenv("BUILD_TIME", "")
    day = os.getenv("BUILD_DAY", "")
    if not sha:
        try:
            sha = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL, timeout=2,
            ).decode().strip()
        except Exception:
            sha = "unknown"
    if not build_time:
        build_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not day:
        day = "Day 68"
    return sha, build_time, day


_BUILD_COMMIT_SHA, _BUILD_TIME, _BUILD_DAY = _resolve_build_metadata()
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from deps.rate_limit import limiter
from models.base import init_engine
from routers import auth as auth_router
from routers import agents as agents_router
from routers import admin as admin_router
from routers import chat as chat_router
from routers import conversations as conversations_router
from routers import api_keys as api_keys_router  # Day 27
from routers import onboarding as onboarding_router  # Day 37
from routers import speech as speech_router  # Day 38
from routers import vision as vision_router  # Day 40
from routers import license as license_router  # Day 61
from routers import metrics as metrics_router  # Day 72: Sprint 0 Observability
from routers import hafidz as hafidz_router  # Day 72: Sprint 1 Hafidz Ledger
from routers import brain as brain_router  # Day 72: Parent Brain â€” knowledge distribution
from routers import owner_datasets as owner_datasets_router  # Sprint 1: Owner Data Pathway

# Day 26: MCP Streamable HTTP server (lazy import â€” degrades gracefully if SDK missing)
try:
    from mcp_server import get_mcp_app
    _MCP_AVAILABLE = True
except Exception as _mcp_import_err:
    _MCP_AVAILABLE = False
    _MCP_IMPORT_ERROR = str(_mcp_import_err)

logger = structlog.get_logger()


async def _check_postgres() -> dict:
    """Check PostgreSQL connectivity."""
    from sqlalchemy import text
    from models.base import engine
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        return {"status": "ok", "detail": "connected"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


async def _check_redis() -> dict:
    """Check Redis connectivity."""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        return {"status": "ok", "detail": "connected"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


async def _check_qdrant() -> dict:
    """Check Qdrant connectivity."""
    try:
        headers = {}
        if settings.QDRANT_API_KEY:
            headers["api-key"] = settings.QDRANT_API_KEY
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.QDRANT_URL}/collections", headers=headers)
            if resp.status_code == 200:
                return {"status": "ok", "detail": "connected"}
            return {"status": "error", "detail": f"HTTP {resp.status_code}"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


async def _check_ollama() -> dict:
    """Check Ollama connectivity and model availability."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "unknown") for m in data.get("models", [])]
                if not models:
                    return {"status": "error", "detail": "no models loaded"}
                return {"status": "ok", "detail": f"{len(models)} models loaded", "models": models[:5]}
            return {"status": "error", "detail": f"HTTP {resp.status_code}"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Day 26: Also runs the MCP session manager lifecycle. FastMCP needs its
    StreamableHTTPSessionManager started via lifespan, otherwise mounted
    requests fail with 'Task group is not initialized'. Starlette mounted
    sub-apps don't get their lifespan called by the parent automatically.
    """
    # 1. Init database engine (lazy, avoids module-level side effects)
    init_engine()
    # 2. Eager-load JWT keys â€” fail fast if keys are missing
    from services.jwt import _get_keys
    _get_keys()
    # 3. Pre-warm dense fastembed model â€” avoids 10-30s cold start on first chat
    from services.embedding import get_model, get_sparse_model
    await get_model()
    # 4. Pre-warm BM42 sparse model â€” optional, degrades gracefully if unavailable
    await get_sparse_model()

    # 5. Start MCP session manager (Day 26)
    mcp_lifespan_cm = None
    if _MCP_AVAILABLE:
        try:
            from mcp_server import get_mcp
            mcp_instance = get_mcp()
            # FastMCP exposes session_manager.run() as an async context manager
            mcp_lifespan_cm = mcp_instance.session_manager.run()
            await mcp_lifespan_cm.__aenter__()
            logger.info("mcp.session_manager.started")
        except Exception as exc:
            logger.error("mcp.session_manager.start_failed", error=str(exc))

    # 6. Day 27: Launch memory pruning daemon (background asyncio task)
    pruner_task = None
    try:
        from services.memory_pruner import prune_loop
        pruner_task = asyncio.create_task(prune_loop())
        logger.info("memory_pruner.task_created")
    except Exception as exc:
        logger.error("memory_pruner.start_failed", error=str(exc))

    # 6b. Sprint 1: Launch knowledge ingestion worker (SP-009)
    ingestion_task = None
    try:
        from services.ingestion_worker import start_worker
        ingestion_task = start_worker()
        logger.info("ingestion.worker.started")
    except Exception as exc:
        logger.error("ingestion.worker.start_failed", error=str(exc))

    # 6c. M1.1: Launch user feedback processor worker
    feedback_worker_task = None
    try:
        from workers.user_feedback_processor import start_feedback_worker
        feedback_worker_task = asyncio.create_task(start_feedback_worker())
        logger.info("feedback.worker.started")
    except Exception as exc:
        logger.error("feedback.worker.start_failed", error=str(exc))

    # 7. Day 44: Start ONAMIX MCP stdio singleton client (Track A)
    #    Replaces per-call subprocess.run pattern (Day 42) â€” eliminates
    #    Node.js cold-start cost per request, unlocks 6 new tools.
    onamix_mcp = None
    try:
        from services.onamix_mcp import OnamixMCPClient, set_global_client
        onamix_mcp = OnamixMCPClient()
        ok = await onamix_mcp.start()
        if ok:
            set_global_client(onamix_mcp)
            logger.info("onamix.mcp.lifespan_started")
        else:
            logger.warning(
                "onamix.mcp.lifespan_start_skipped",
                reason="binary unavailable or session open failed â€” falling back to subprocess",
            )
            onamix_mcp = None
    except Exception as exc:
        logger.error("onamix.mcp.lifespan_start_failed", error=str(exc))
        onamix_mcp = None

    # 8. Day 45 (lesson #45): Auto-resume synthetic generation if Redis
    #    state shows an interrupted auto-rerun run. Background asyncio
    #    tasks die with the container â€” without this, every deploy
    #    silently kills the DPO flywheel until manual restart.
    #
    #    Conditions to resume:
    #      - Redis target_pairs is set (auto-rerun mode, not single-shot)
    #      - cumulative_stored < target_pairs (work remains)
    #      - status not in {idle, completed, stopped} (was actively running)
    try:
        from services.synthetic_pipeline import (
            get_synthetic_status,
            start_synthetic_generation,
        )
        st = await get_synthetic_status()
        target = st.get("target_pairs")
        cumulative = st.get("cumulative_stored", 0)
        prev_status = (st.get("status") or "idle").lower()
        # Day 45 fix: "cancelled" was treated as deploy-kill to recover.
        # Day 67 fix: "cancelled" via admin /stop = INTENTIONAL user action.
        #   Do NOT auto-resume cancelled â€” only resume if status is "running"
        #   or "error" (genuinely killed by deploy restart, not by admin).
        _resume_statuses = {"running", "error", "starting"}
        if target and cumulative < target and prev_status in _resume_statuses:
            logger.info(
                "synthetic.auto_resume.attempt",
                prev_run_id=st.get("run_id"),
                prev_status=prev_status,
                cumulative=cumulative,
                target=target,
            )
            ok, new_run_id, msg = await start_synthetic_generation(target_pairs=target)
            logger.info(
                "synthetic.auto_resume.result",
                ok=ok,
                new_run_id=new_run_id,
                message=msg,
            )
        else:
            logger.info(
                "synthetic.auto_resume.skipped",
                reason="no incomplete auto-rerun in redis",
                target=target,
                cumulative=cumulative,
                prev_status=prev_status,
            )
    except Exception as exc:
        logger.warning("synthetic.auto_resume.error", error=str(exc))

    # 9. Day 47: boot-time contract validation (catches Day 46 tool-config drift)
    #    + start TaskRegistry watchdog (catches Day 39 + Day 44 silent task death)
    watchdog_task = None
    try:
        from services.contracts import boot_check_and_log, watchdog_loop, safe_task
        boot_check_and_log()  # logs ok/warning/error; non-fatal
        watchdog_task = safe_task(
            watchdog_loop(interval_s=60.0),
            name="contracts_watchdog",
            register=False,  # don't register the watchdog itself in its own registry
        )
    except Exception as exc:
        logger.error("contracts.startup_failed", error=str(exc))

    # 9b. Day 71d: Pre-compute tool description embeddings for semantic
    #     filtering (Lesson #181). Cuts tool-detection prompt 5x by selecting
    #     top-K tools per query instead of sending all 29.
    try:
        from services.tool_relevance import precompute_tool_embeddings
        n = await precompute_tool_embeddings()
        logger.info("tool_relevance.boot_ok", count=n)
    except Exception as exc:
        logger.warning("tool_relevance.boot_failed", error=str(exc))

    # 10. Day 61: License validation at startup (GAP-03 Phase 2)
    #     Inspired by Ixonomic coin minting â€” each ADO instance carries a
    #     cryptographically signed license.json (HMAC-SHA256). Offline-capable.
    #     Modes: FULL â†’ READ_ONLY (expired) â†’ DEMO (no license, beta) â†’ INVALID (tampered)
    try:
        from services.license import load_and_validate, set_current_license, LicenseMode
        lic_result = load_and_validate(
            license_path=settings.LICENSE_PATH,
            secret_key=settings.LICENSE_SECRET_KEY,
            demo_mode_allowed=settings.LICENSE_DEMO_MODE,
        )
        set_current_license(lic_result)
        if lic_result.mode == LicenseMode.FULL:
            logger.info(
                "license.ok",
                client=lic_result.client_name,
                display_name=lic_result.ado_display_name,
                tier=lic_result.tier,
                days_remaining=lic_result.days_remaining,
            )
        elif lic_result.mode == LicenseMode.DEMO:
            logger.info("license.demo_mode", reason=lic_result.reason)
        elif lic_result.mode == LicenseMode.READ_ONLY:
            logger.warning(
                "license.read_only",
                reason=lic_result.reason,
                detail="Training and new-data features disabled until license renewed",
            )
        else:  # INVALID
            logger.error(
                "license.invalid",
                reason=lic_result.reason,
                detail="ADO running in DEMO mode despite invalid license â€” set LICENSE_DEMO_MODE=false to enforce",
            )
    except Exception as exc:
        logger.error("license.startup_check_failed", error=str(exc))

    logger.info("migan.startup", message="MiganCore API starting up")
    yield
    logger.info("migan.shutdown", message="MiganCore API shutting down")

    # Tear down contracts watchdog
    if watchdog_task is not None and not watchdog_task.done():
        watchdog_task.cancel()
        try:
            await watchdog_task
        except asyncio.CancelledError:
            pass

    # Tear down ONAMIX MCP client
    if onamix_mcp is not None:
        try:
            await onamix_mcp.stop()
        except Exception as exc:
            logger.error("onamix.mcp.lifespan_stop_failed", error=str(exc))

    # Tear down memory pruner
    if pruner_task is not None and not pruner_task.done():
        pruner_task.cancel()
        try:
            await pruner_task
        except asyncio.CancelledError:
            pass

    # Tear down ingestion worker
    if ingestion_task is not None and not ingestion_task.done():
        ingestion_task.cancel()
        try:
            await ingestion_task
        except asyncio.CancelledError:
            pass

    # Tear down feedback worker
    if feedback_worker_task is not None and not feedback_worker_task.done():
        feedback_worker_task.cancel()
        try:
            await feedback_worker_task
        except asyncio.CancelledError:
            pass

    # Tear down MCP session manager
    if mcp_lifespan_cm is not None:
        try:
            await mcp_lifespan_cm.__aexit__(None, None, None)
            logger.info("mcp.session_manager.stopped")
        except Exception as exc:
            logger.error("mcp.session_manager.stop_failed", error=str(exc))


app = FastAPI(
    title="MiganCore API",
    description="Autonomous Digital Organism â€” Core Gateway",
    version="0.5.16",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Attach request_id and tenant context to every request for tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    """Track request count and latency for Prometheus metrics."""
    from routers.metrics import REQUEST_COUNT, REQUEST_LATENCY
    import time

    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    method = request.method
    endpoint = request.url.path
    status_code = str(response.status_code)

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

    return response

# CORS â€” restrict to known domains in production
# TODO: move to environment variable for flexibility
_cors_origins = [
    "https://migancore.com",       # Day 33: landing page
    "https://app.migancore.com",
    "https://lab.migancore.com",
]
if settings.ENVIRONMENT == "development":
    _cors_origins.extend(["http://localhost:3000", "http://localhost:5173"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wire routers
app.include_router(auth_router.router)
app.include_router(agents_router.router)
app.include_router(admin_router.router)
app.include_router(chat_router.router)
app.include_router(conversations_router.router)
app.include_router(api_keys_router.router)  # Day 27
app.include_router(onboarding_router.router)  # Day 37
app.include_router(speech_router.router)  # Day 38
app.include_router(vision_router.router)   # Day 40
app.include_router(license_router.router)  # Day 61
app.include_router(metrics_router.router)
app.include_router(hafidz_router.router)  # Day 72: Sprint 1 Hafidz Ledger
app.include_router(brain_router.router)  # Day 72: Parent Brain â€” knowledge distribution
app.include_router(owner_datasets_router.router)  # Sprint 1: Owner Data Pathway

# Day 71d Phase 2.1: system telemetry (status + metrics, public, no auth)
try:
    from routers import system as system_router
    app.include_router(system_router.router)
except Exception as _e:
    logger.warning("system_router.import_failed", error=str(_e))

# Day 26: Mount MCP Streamable HTTP server at /mcp
# Degrades gracefully if `mcp` SDK is unavailable (e.g. dev container without rebuild).
if _MCP_AVAILABLE:
    try:
        app.mount("/mcp", get_mcp_app())
        logger.info("mcp.mounted", path="/mcp", transport="streamable-http")
    except Exception as exc:
        logger.error("mcp.mount_failed", error=str(exc))
else:
    logger.warning("mcp.unavailable", reason=_MCP_IMPORT_ERROR)


@app.get("/health", tags=["system"])
async def health_check():
    """Liveness probe for orchestrators and load balancers.

    Day 68 (Codex C4): expose commit_sha + build_time + day so frontend
    labels can be dynamic instead of hardcoded version strings going stale.
    """
    return {
        "status": "healthy",
        "service": "migancore-api",
        "version": app.version,
        "model": settings.DEFAULT_MODEL,
        "commit_sha": _BUILD_COMMIT_SHA,
        "build_time": _BUILD_TIME,
        "day": _BUILD_DAY,
    }


@app.get("/ready", tags=["system"])
async def readiness_check():
    """Readiness probe â€” checks downstream dependencies."""
    checks = {
        "postgres": await _check_postgres(),
        "redis": await _check_redis(),
        "qdrant": await _check_qdrant(),
        "ollama": await _check_ollama(),
    }

    all_ok = all(c["status"] == "ok" for c in checks.values())

    if not all_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": checks},
        )

    return {
        "status": "ready",
        "checks": checks,
    }


@app.get("/", tags=["system"])
async def root():
    """API root â€” returns service metadata."""
    return {
        "name": "MiganCore",
        "version": app.version,
        "tagline": "Every vision deserves a digital organism.",
        "endpoints": {
            "health": "/health",
            "ready": "/ready",
            "docs": "/docs",
            "auth": "/v1/auth",
            "agents": "/v1/agents",
            "conversations": "/v1/conversations",
        },
    }


# ---------------------------------------------------------------------------
# Day 33: Public stats endpoint for migancore.com landing page
# ---------------------------------------------------------------------------
@app.get("/v1/public/stats", tags=["system"])
async def public_stats():
    """Sanitized public stats for landing page widget.

    No auth required. Rate-limited via slowapi (5 req/min).
    Only exposes aggregate counts â€” no PII, no per-tenant data.
    """
    from sqlalchemy import text as sql_text
    from models.base import AsyncSessionLocal

    if AsyncSessionLocal is None:
        return {"total_pairs": 0, "by_source_method": {}, "training_readiness": {"status": "loading"}}

    async with AsyncSessionLocal() as session:
        # Total + by source (preference_pairs has no RLS â€” safe)
        total_res = await session.execute(sql_text("SELECT COUNT(*) FROM preference_pairs"))
        total = total_res.scalar_one()

        sources_res = await session.execute(
            sql_text("SELECT source_method, COUNT(*) FROM preference_pairs GROUP BY source_method")
        )
        by_source = {r[0]: r[1] for r in sources_res.fetchall()}

        # Last 24h
        rate_res = await session.execute(
            sql_text("SELECT COUNT(*) FROM preference_pairs WHERE created_at >= NOW() - INTERVAL '24 hours'")
        )
        last_24h = rate_res.scalar_one()

    # Training readiness
    if total >= 2000:
        ready = {"status": "ideal", "message": f"{total} pairs â€” ideal for training"}
    elif total >= 1000:
        ready = {"status": "ready", "message": f"{total} pairs â€” training-ready"}
    elif total >= 500:
        ready = {"status": "approaching", "message": f"{total} pairs â€” approaching threshold"}
    else:
        ready = {"status": "building", "message": f"{total} pairs â€” building flywheel"}

    return {
        "total_pairs": total,
        "by_source_method": by_source,
        "last_24h": last_24h,
        "training_readiness": ready,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
    )
