"""
MiganCore API — FastAPI Gateway
Entry point for the autonomous digital organism.
"""

import asyncio
import os
import uuid
from contextlib import asynccontextmanager

import httpx
import structlog
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

# Day 26: MCP Streamable HTTP server (lazy import — degrades gracefully if SDK missing)
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
    # 2. Eager-load JWT keys — fail fast if keys are missing
    from services.jwt import _get_keys
    _get_keys()
    # 3. Pre-warm dense fastembed model — avoids 10-30s cold start on first chat
    from services.embedding import get_model, get_sparse_model
    await get_model()
    # 4. Pre-warm BM42 sparse model — optional, degrades gracefully if unavailable
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

    logger.info("migan.startup", message="MiganCore API starting up")
    yield
    logger.info("migan.shutdown", message="MiganCore API shutting down")

    # Tear down memory pruner
    if pruner_task is not None and not pruner_task.done():
        pruner_task.cancel()
        try:
            await pruner_task
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
    description="Autonomous Digital Organism — Core Gateway",
    version="0.4.9",
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


# CORS — restrict to known domains in production
# TODO: move to environment variable for flexibility
_cors_origins = [
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
    """Liveness probe for orchestrators and load balancers."""
    return {
        "status": "healthy",
        "service": "migancore-api",
        "version": app.version,
    }


@app.get("/ready", tags=["system"])
async def readiness_check():
    """Readiness probe — checks downstream dependencies."""
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
    """API root — returns service metadata."""
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
    )
