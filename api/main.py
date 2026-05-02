"""
MiganCore API — FastAPI Gateway
Entry point for the autonomous digital organism.
"""

import os
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import auth as auth_router

logger = structlog.get_logger()


async def _check_postgres() -> dict:
    """Check PostgreSQL connectivity."""
    from sqlalchemy import text
    from models import engine
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
    """Check Ollama connectivity."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "unknown") for m in data.get("models", [])]
                return {"status": "ok", "detail": f"{len(models)} models loaded", "models": models[:5]}
            return {"status": "error", "detail": f"HTTP {resp.status_code}"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("migan.startup", message="MiganCore API starting up")
    # Eager-load JWT keys — fail fast if keys are missing
    from services.jwt import _get_keys
    _get_keys()
    yield
    logger.info("migan.shutdown", message="MiganCore API shutting down")


app = FastAPI(
    title="MiganCore API",
    description="Autonomous Digital Organism — Core Gateway",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS — restrict to known domains in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.migancore.com", "https://lab.migancore.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wire routers
app.include_router(auth_router.router)


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
