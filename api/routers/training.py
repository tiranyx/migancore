"""Admin training router — MiganForge control endpoints.

Endpoints:
    POST /v1/admin/training/trigger     — Trigger training loop
    GET  /v1/admin/training/status      — Get current training status
    POST /v1/admin/training/rollback    — Rollback to previous model
    GET  /v1/admin/training/registry    — List model registry
    GET  /v1/admin/training/benchmark   — Run benchmark eval
    POST /v1/admin/training/deploy      — Deploy specific model

Requires admin secret key (X-Admin-Key header).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from config import settings
from services.training_orchestrator import TrainingOrchestrator, TrainingState

router = APIRouter(prefix="/v1/admin/training", tags=["admin-training"])


def verify_admin(x_admin_key: Optional[str] = Header(None)):
    """Verify admin secret key."""
    if not settings.ADMIN_SECRET_KEY:
        raise HTTPException(403, "Admin endpoints disabled")
    if not x_admin_key or x_admin_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(401, "Invalid admin key")
    return True


@router.post("/trigger")
async def trigger_training(
    dry_run: bool = False,
    force: bool = False,
    _admin: bool = Depends(verify_admin),
):
    """Trigger the full training loop: extract → train → eval → deploy."""
    orchestrator = TrainingOrchestrator()
    result = orchestrator.run(dry_run=dry_run, force=force)
    return result


@router.get("/status")
async def training_status(_admin: bool = Depends(verify_admin)):
    """Get current training orchestrator status."""
    orchestrator = TrainingOrchestrator()
    state = orchestrator.current_state()
    if state:
        return {
            "busy": orchestrator.is_busy(),
            "state": state.state,
            "run_id": state.run_id,
            "version": state.version,
            "baseline": state.baseline_version,
            "started_at": state.started_at,
            "error": state.error,
        }
    return {"busy": False, "state": TrainingState.IDLE.value}


@router.post("/rollback")
async def rollback_model(
    version: Optional[str] = None,
    _admin: bool = Depends(verify_admin),
):
    """Rollback to a previous model version."""
    orchestrator = TrainingOrchestrator()
    return orchestrator.rollback(version)


@router.get("/registry")
async def model_registry(_admin: bool = Depends(verify_admin)):
    """List all models in the registry."""
    from deploy.ollama_manager import ModelRegistry
    reg = ModelRegistry()
    return {"models": reg._data}


@router.post("/benchmark")
async def run_benchmark(
    candidate_model: str = settings.DEFAULT_MODEL,
    baseline_model: str = settings.DEFAULT_MODEL,
    judge: str = "heuristic",
    _admin: bool = Depends(verify_admin),
):
    """Run benchmark evaluation between two models."""
    from eval.benchmark import run_benchmark
    result = run_benchmark(candidate_model, baseline_model, judge)
    return {
        "win_rate": result.win_rate,
        "category_scores": result.category_scores,
        "identity_consistency": result.identity_consistency,
        "avg_response_time_ms": result.avg_response_time_ms,
        "samples": result.samples[:5],  # First 5 samples
    }


@router.post("/deploy")
async def deploy_model(
    version: str,
    hf_model_dir: Optional[str] = None,
    gguf_path: Optional[str] = None,
    _admin: bool = Depends(verify_admin),
):
    """Deploy a specific model to Ollama."""
    from deploy.ollama_manager import deploy_model
    return deploy_model(
        version=version,
        hf_model_dir=Path(hf_model_dir) if hf_model_dir else None,
        gguf_path=Path(gguf_path) if gguf_path else None,
    )
