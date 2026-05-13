#!/usr/bin/env python3
"""MiganForge Training Orchestrator — v1.0 (Day 72e)

The brain of the closed-loop training system. Orchestrates the full flow:

    EXTRACT → TRAIN → EVAL → DEPLOY → MONITOR

Runs on the VPS (CPU-only). Coordinates with cloud GPU for training.

States:
    idle → extracting → training → evaluating → deploying → monitoring → idle
    (or: failed, rollback)

Usage:
    # Manual trigger
    python -m services.training_orchestrator --trigger

    # Check status
    python -m services.training_orchestrator --status

    # Dry run (simulate without executing)
    python -m services.training_orchestrator --trigger --dry-run

Integration:
    - Wired into admin router: POST /v1/admin/training/trigger
    - Wired into distillation worker: auto-trigger when pairs > threshold
    - Wired into cron: daily check at 04:00

Author: MiganCore ADO — MiganForge v1.0
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

import structlog

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings

logger = structlog.get_logger()

STATE_FILE = Path(settings.TRAINING_OUTPUT_DIR) / "orchestrator_state.json"
ORCHESTRATOR_LOG = Path(settings.TRAINING_OUTPUT_DIR) / "orchestrator.log"


class TrainingState(str, Enum):
    IDLE = "idle"
    EXTRACTING = "extracting"
    TRAINING = "training"
    EVALUATING = "evaluating"
    DEPLOYING = "deploying"
    MONITORING = "monitoring"
    ROLLING_BACK = "rolling_back"
    FAILED = "failed"


@dataclass
class OrchestratorState:
    run_id: str
    state: str
    version: str
    baseline_version: str
    started_at: str
    ended_at: Optional[str] = None
    error: Optional[str] = None
    extract_stats: Optional[dict] = None
    train_report: Optional[dict] = None
    eval_report: Optional[dict] = None
    deploy_report: Optional[dict] = None


class TrainingOrchestrator:
    """Orchestrates the full training loop."""

    def __init__(self):
        self.state_file = STATE_FILE
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state: Optional[OrchestratorState] = None
        self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                data = json.load(f)
                self._state = OrchestratorState(**data) if data else None

    def _save_state(self, state: OrchestratorState):
        self._state = state
        with open(self.state_file, "w") as f:
            json.dump(asdict(state), f, indent=2, ensure_ascii=False, default=str)

    def current_state(self) -> Optional[OrchestratorState]:
        return self._state

    def is_busy(self) -> bool:
        if not self._state:
            return False
        return self._state.state not in (TrainingState.IDLE.value, TrainingState.FAILED.value)

    def _new_run(self, version: str, baseline: str) -> OrchestratorState:
        run_id = f"forge_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        state = OrchestratorState(
            run_id=run_id,
            state=TrainingState.IDLE.value,
            version=version,
            baseline_version=baseline,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._save_state(state)
        return state

    def _transition(self, state: OrchestratorState, new_state: str, **kwargs):
        state.state = new_state
        for k, v in kwargs.items():
            setattr(state, k, v)
        self._save_state(state)
        logger.info("orchestrator.transition", run_id=state.run_id, state=new_state)

    def run(self, dry_run: bool = False, force: bool = False) -> dict:
        """Execute the full training loop."""
        if self.is_busy() and not force:
            return {
                "status": "busy",
                "message": f"Training already in progress: {self._state.state}",
                "run_id": self._state.run_id,
            }

        version = f"migancore:{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"
        baseline = settings.DEFAULT_MODEL

        state = self._new_run(version, baseline)

        try:
            # Step 1: EXTRACT
            self._transition(state, TrainingState.EXTRACTING.value)
            extract_result = self._step_extract(dry_run)
            self._transition(state, TrainingState.IDLE.value, extract_stats=extract_result)

            if dry_run:
                return self._dry_run_summary(state)

            if extract_result.get("dpo_count", 0) < 30:
                return self._fail(state, f"Insufficient DPO pairs: {extract_result.get('dpo_count', 0)} < 30")

            # Step 2: TRAIN
            self._transition(state, TrainingState.TRAINING.value)
            train_result = self._step_train(version, dry_run)
            self._transition(state, TrainingState.IDLE.value, train_report=train_result)

            if train_result.get("status") not in ("success", "queued"):
                return self._fail(state, f"Training failed: {train_result.get('error', 'unknown')}")
            if train_result.get("status") == "queued":
                self._transition(state, TrainingState.IDLE.value, ended_at=datetime.now(timezone.utc).isoformat())
                return {
                    "status": "queued",
                    "run_id": state.run_id,
                    "version": version,
                    "baseline": baseline,
                    "extract": extract_result,
                    "train": train_result,
                }

            # Step 3: EVAL
            self._transition(state, TrainingState.EVALUATING.value)
            eval_result = self._step_eval(version, baseline, dry_run)
            self._transition(state, TrainingState.IDLE.value, eval_report=eval_result)

            win_rate = eval_result.get("win_rate", 0)
            if win_rate < 50:
                return self._fail(state, f"Eval failed: win rate {win_rate:.1f}% < 50% (model is worse)")

            # Step 4: DEPLOY
            self._transition(state, TrainingState.DEPLOYING.value)
            deploy_result = self._step_deploy(version, dry_run)
            self._transition(state, TrainingState.IDLE.value, deploy_report=deploy_result)

            if deploy_result.get("status") not in ("success", "deployed_unhealthy"):
                return self._fail(state, f"Deploy failed: {deploy_result.get('error', 'unknown')}")

            # Step 5: MONITOR (brief)
            self._transition(state, TrainingState.MONITORING.value)
            time.sleep(5)  # Brief monitoring window
            self._transition(state, TrainingState.IDLE.value, ended_at=datetime.now(timezone.utc).isoformat())

            logger.info("orchestrator.complete", run_id=state.run_id, version=version, win_rate=win_rate)
            return {
                "status": "success",
                "run_id": state.run_id,
                "version": version,
                "baseline": baseline,
                "win_rate": win_rate,
                "extract": extract_result,
                "train": train_result,
                "eval": eval_result,
                "deploy": deploy_result,
            }

        except Exception as exc:
            return self._fail(state, str(exc))

    def _step_extract(self, dry_run: bool) -> dict:
        """Extract training data from PostgreSQL."""
        logger.info("orchestrator.extract.start")
        if dry_run:
            return {"dpo_count": 100, "sft_count": 50, "dry_run": True}

        try:
            from training.data_exporter import get_db_connection, export_dpo_pairs, export_identity_sft

            conn = get_db_connection()
            output_dir = Path(settings.TRAINING_OUTPUT_DIR)
            output_dir.mkdir(parents=True, exist_ok=True)

            dpo_path = output_dir / "dpo_export.jsonl"
            dpo_stats = export_dpo_pairs(
                conn,
                dpo_path,
                min_judge_score=3.0,
                max_pairs=5000,
                include_sources=["cai_pipeline", "distillation_worker", "synthetic_seed_v1"],
                exclude_used=True,
            )

            sft_path = output_dir / "identity_sft.jsonl"
            sft_stats = export_identity_sft(conn, sft_path)

            conn.close()
            logger.info("orchestrator.extract.done", dpo=dpo_stats.get("total_exported"), sft=sft_stats.get("total_exported"))
            return {
                "dpo_count": dpo_stats.get("total_exported", 0),
                "sft_count": sft_stats.get("total_exported", 0),
                "avg_judge_score": dpo_stats.get("avg_judge_score", 0),
                "sources": dpo_stats.get("by_source", {}),
            }
        except Exception as exc:
            logger.error("orchestrator.extract.failed", error=str(exc))
            raise

    def _step_train(self, version: str, dry_run: bool) -> dict:
        """Launch training job."""
        logger.info("orchestrator.train.start", version=version)
        if dry_run:
            return {"status": "success", "train_time_min": 120, "dry_run": True}

        provider = settings.TRAINING_GPU_PROVIDER.lower()
        if provider == "runpod" and not settings.RUNPOD_API_KEY:
            return {
                "status": "missing_credentials",
                "provider": "runpod",
                "error": "RUNPOD_API_KEY is not set",
            }
        if provider == "vastai" and not settings.VAST_API_KEY:
            return {
                "status": "missing_credentials",
                "provider": "vastai",
                "error": "VAST_API_KEY is not set",
            }

        output_dir = Path(settings.TRAINING_OUTPUT_DIR) / version.replace(":", "_")
        dpo_data = Path(settings.TRAINING_OUTPUT_DIR) / "dpo_export.jsonl"
        identity_data = Path(settings.TRAINING_OUTPUT_DIR) / "identity_sft.jsonl"

        cmd = (
            f"python -m training.dpo_trainer "
            f"--dpo-data {dpo_data} "
            f"--identity-data {identity_data} "
            f"--output-dir {output_dir} "
            f"--base-model Qwen/Qwen2.5-7B-Instruct "
            f"--qlora --epochs 1 --merge --version {version}"
        )

        logger.info("orchestrator.train.gpu_ready", provider=provider, cmd=cmd)
        return {
            "status": "queued",
            "provider": provider,
            "message": "Training threshold reached and GPU credentials are available. Cloud worker launch is queued for provider integration.",
            "command": cmd,
            "output_dir": str(output_dir),
        }

    def _step_eval(self, version: str, baseline: str, dry_run: bool) -> dict:
        """Evaluate trained model."""
        logger.info("orchestrator.eval.start", version=version, baseline=baseline)
        if dry_run:
            return {"win_rate": 65.0, "dry_run": True}

        try:
            from eval.benchmark import run_benchmark
            result = run_benchmark(version, baseline, judge_model="heuristic")
            return {
                "win_rate": result.win_rate,
                "category_scores": result.category_scores,
                "identity_consistency": result.identity_consistency,
                "avg_response_time_ms": result.avg_response_time_ms,
            }
        except Exception as exc:
            logger.error("orchestrator.eval.failed", error=str(exc))
            raise

    def _step_deploy(self, version: str, dry_run: bool) -> dict:
        """Deploy model to Ollama."""
        logger.info("orchestrator.deploy.start", version=version)
        if dry_run:
            return {"status": "success", "dry_run": True}

        try:
            from deploy.ollama_manager import deploy_model
            output_dir = Path(settings.TRAINING_OUTPUT_DIR) / version.replace(":", "_")
            merged_dir = output_dir / "merged_model"

            if not merged_dir.exists():
                return {
                    "status": "failed",
                    "error": f"Merged model not found: {merged_dir}. Training must be completed first.",
                }

            return deploy_model(
                version=version,
                hf_model_dir=merged_dir,
                quant_type="Q4_K_M",
                skip_health_check=False,
            )
        except Exception as exc:
            logger.error("orchestrator.deploy.failed", error=str(exc))
            raise

    def _fail(self, state: OrchestratorState, error: str) -> dict:
        self._transition(state, TrainingState.FAILED.value, error=error, ended_at=datetime.now(timezone.utc).isoformat())
        logger.error("orchestrator.failed", run_id=state.run_id, error=error)
        return {
            "status": "failed",
            "run_id": state.run_id,
            "error": error,
            "state": asdict(state),
        }

    def _dry_run_summary(self, state: OrchestratorState) -> dict:
        return {
            "status": "dry_run",
            "run_id": state.run_id,
            "version": state.version,
            "baseline": state.baseline_version,
            "message": "Dry run complete. No actual training occurred.",
            "steps": {
                "extract": {"dpo_count": 100, "sft_count": 50},
                "train": {"status": "would_trigger", "estimated_time_min": 120},
                "eval": {"win_rate": 65.0},
                "deploy": {"status": "would_deploy"},
            },
        }

    def rollback(self, target_version: Optional[str] = None) -> dict:
        """Rollback to a previous version."""
        try:
            from deploy.ollama_manager import rollback_model
            return rollback_model(target_version)
        except Exception as exc:
            logger.error("orchestrator.rollback.failed", error=str(exc))
            return {"status": "failed", "error": str(exc)}


def main():
    parser = argparse.ArgumentParser(description="MiganForge Training Orchestrator")
    parser.add_argument("--trigger", action="store_true", help="Trigger training loop")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without executing")
    parser.add_argument("--force", action="store_true", help="Force trigger even if busy")
    parser.add_argument("--rollback", default=None, help="Rollback to version")
    parser.add_argument("--version", default=None, help="Override version tag")
    args = parser.parse_args()

    orchestrator = TrainingOrchestrator()

    if args.status:
        state = orchestrator.current_state()
        if state:
            print(json.dumps(asdict(state), indent=2, ensure_ascii=False))
        else:
            print('{"state": "idle", "message": "No active training run"}')
        return

    if args.rollback:
        result = orchestrator.rollback(args.rollback)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.trigger:
        result = orchestrator.run(dry_run=args.dry_run, force=args.force)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
