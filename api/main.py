"""
MiganCore API — FastAPI Gateway
Entry point for the autonomous digital organism.
"""

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
from routers import chat as chat_router

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
    """Application lifespan manager."""
    # 1. Init database engine (lazy, avoids module-level side effects)
    init_engine()
    # 2. Eager-load JWT keys — fail fast if keys are missing
    from services.jwt import _get_keys
    _get_keys()
    logger.info("migan.startup", message="MiganCore API starting up")
    yield
    logger.info("migan.shutdown", message="MiganCore API shutting down")


app = FastAPI(
    title="MiganCore API",
    description="Autonomous Digital Organism — Core Gateway",
    version="0.2.0",
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
app.include_router(chat_router.router)


@app.get("/health", tags=["system"])
async def health_check():
    """Liveness probe for orchestrators and load balancers."""
    return {
        "status": "healthy",
        "service": "migancore-api",
        "version": "0.2.0",
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
        "version": "0.2.0",
        "tagline": "Every vision deserves a digital organism.",
        "endpoints": {
            "health": "/health",
            "ready": "/ready",
            "docs": "/docs",
            "auth": "/v1/auth",
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
