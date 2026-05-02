"""
MiganCore API — FastAPI Gateway
Entry point for the autonomous digital organism.
"""

import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("migan.startup", message="MiganCore API starting up")
    yield
    logger.info("migan.shutdown", message="MiganCore API shutting down")


app = FastAPI(
    title="MiganCore API",
    description="Autonomous Digital Organism — Core Gateway",
    version="0.1.0",
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


@app.get("/health", tags=["system"])
async def health_check():
    """Liveness probe for orchestrators and load balancers."""
    return {
        "status": "healthy",
        "service": "migancore-api",
        "version": "0.1.0",
    }


@app.get("/ready", tags=["system"])
async def readiness_check():
    """Readiness probe — checks downstream dependencies."""
    # TODO: check postgres, redis, qdrant connectivity
    return {
        "status": "ready",
        "checks": {
            "postgres": "pending",
            "redis": "pending",
            "qdrant": "pending",
        },
    }


@app.get("/", tags=["system"])
async def root():
    """API root — returns service metadata."""
    return {
        "name": "MiganCore",
        "version": "0.1.0",
        "tagline": "Every vision deserves a digital organism.",
        "endpoints": {
            "health": "/health",
            "ready": "/ready",
            "docs": "/docs",
        },
    }


# Placeholder router imports — uncomment as modules are built
# from routers import auth, agents, conversations, tools, training
# app.include_router(auth.router, prefix="/auth", tags=["auth"])
# app.include_router(agents.router, prefix="/agents", tags=["agents"])
# app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
# app.include_router(tools.router, prefix="/tools", tags=["tools"])
# app.include_router(training.router, prefix="/training", tags=["training"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
    )
