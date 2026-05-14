"""
Sandbox / Playground router — M1.7 Dev Organ Proposal Queue.

This is the interface between MiganCore's self-improvement loop and Fahmi
(the Creator). Every improvement proposal MiganCore generates lands here.
Fahmi reviews them in the Playground UI: approve, reject, or ask for more.

Endpoints:
  GET  /v1/sandbox/proposals            — list all proposals (paginated, filterable)
  POST /v1/sandbox/proposals            — submit a new proposal (brain or admin)
  GET  /v1/sandbox/proposals/{id}       — get single proposal
  PATCH /v1/sandbox/proposals/{id}/verdict — creator approve/reject
  POST /v1/sandbox/proposals/{id}/gates — run QA gate evaluation
  GET  /v1/sandbox/stats                — dashboard stats (stage counts, risk distribution)

Auth:
  - List/Get/Stats: X-Admin-Key header (same as admin router)
  - Submit (POST): X-Admin-Key required. Brain submissions use the internal
    propose_improvement tool, which attaches the admin key server-side.
  - Verdict (PATCH): X-Admin-Key only — creator action
  - Gates (POST): X-Admin-Key only
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import os
from pathlib import Path
import secrets
import shlex
import subprocess
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from deps.db import get_db
from models.proposal import DevOrganProposal
from services.dev_organ import (
    ImprovementProposal,
    GateResult,
    RiskLevel,
    classify_risk,
    evaluate_promotion,
    required_gates,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/sandbox", tags=["sandbox"])
_APP_ROOT = Path(os.getenv("MIGANCORE_APP_ROOT", "/app")).resolve()
_PYTEST_TIMEOUT_SECONDS = int(os.getenv("SANDBOX_GATE_PYTEST_TIMEOUT", "90"))


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _require_admin(x_admin_key: str = Header(default="", alias="X-Admin-Key")) -> None:
    if not settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Admin not configured")
    if not secrets.compare_digest(x_admin_key or "", settings.ADMIN_SECRET_KEY):
        raise HTTPException(status_code=401, detail="Invalid admin key")


def _allow_propose(x_admin_key: str = Header(default="", alias="X-Admin-Key")) -> bool:
    """Authorize proposal creation.

    M1.7 originally left proposal submission open so the brain could create
    rows before scoped agent JWTs existed. Now the brain uses the internal
    propose_improvement tool with the server-side admin key, so public POSTs
    should not be accepted.
    """
    if not settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Admin not configured")
    if not secrets.compare_digest(x_admin_key or "", settings.ADMIN_SECRET_KEY):
        raise HTTPException(status_code=401, detail="Invalid admin key")
    return True


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ProposalCreate(BaseModel):
    title: str = Field(..., min_length=4, max_length=200)
    problem: str = Field(..., min_length=10)
    hypothesis: str = Field(default="")
    touched_paths: list[str] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    rollback_plan: str = Field(default="")
    source: str = Field(
        default="auto",
        pattern="^(auto|owner_command|tool_failure|eval_failure|manual)$",
    )
    metadata: dict = Field(default_factory=dict)
    created_by: str = Field(default="core_brain", max_length=128)


class VerdictUpdate(BaseModel):
    verdict: str = Field(..., pattern="^(approved|rejected)$")
    notes: str = Field(default="")


class GateInput(BaseModel):
    gate_name: str
    passed: bool
    detail: str = ""


class GatesRunRequest(BaseModel):
    gates: list[GateInput]


def _proposal_lifecycle(proposal: DevOrganProposal) -> dict:
    """Return read-only lifecycle/gate visibility for UI and agents."""
    risk = RiskLevel(proposal.risk_level)
    required = sorted(required_gates(risk))
    gate_results = proposal.gate_results or []
    by_name = {
        str(g.get("name")): bool(g.get("passed"))
        for g in gate_results
        if isinstance(g, dict) and g.get("name")
    }
    passed = sorted(name for name in required if by_name.get(name) is True)
    failed = sorted(name for name in required if by_name.get(name) is False)
    missing = sorted(name for name in required if name not in by_name)

    if proposal.creator_verdict == "rejected":
        next_action = "rejected"
    elif failed:
        next_action = "fix_failed_gates"
    elif missing and proposal.creator_verdict == "approved":
        next_action = "run_missing_gates"
    elif missing:
        next_action = "creator_review"
    elif proposal.stage in ("validated", "deployable"):
        next_action = "ready_for_owner_promotion"
    elif proposal.stage in ("deployed", "monitored"):
        next_action = "monitor"
    elif proposal.stage == "blocked":
        next_action = "revise_or_reject"
    else:
        next_action = "sandbox_iteration"

    return {
        "risk": risk.value,
        "required_gates": required,
        "passed_gates": passed,
        "failed_gates": failed,
        "missing_gates": missing,
        "next_action": next_action,
    }


def _proposal_to_response(proposal: DevOrganProposal) -> dict:
    data = proposal.to_dict()
    data["lifecycle"] = _proposal_lifecycle(proposal)
    return data


_SECRET_PATH_MARKERS = (
    ".env",
    "private.pem",
    "public.pem",
    "secret",
    "credential",
    "api_key",
    "token",
)

_DATA_BOUNDARY_MARKERS = (
    "tenant",
    "rls",
    "auth",
    "jwt",
    "password",
    "license",
    "migration",
    "alembic",
    "database",
)


def _safe_repo_path(path: str) -> Path | None:
    """Resolve a proposal path inside the application root only."""
    normalized = (path or "").replace("\\", "/").strip().lstrip("/")
    if not normalized or normalized.startswith("../") or "/../" in normalized:
        return None
    candidate = (_APP_ROOT / normalized).resolve()
    try:
        candidate.relative_to(_APP_ROOT)
    except ValueError:
        return None
    return candidate


def _syntax_gate_result(proposal: DevOrganProposal) -> GateResult:
    """Compile touched Python files without executing them."""
    python_paths = [p for p in (proposal.touched_paths or []) if str(p).endswith(".py")]
    if not python_paths:
        return GateResult(
            name="syntax",
            passed=True,
            detail="No Python files touched.",
        )

    checked: list[str] = []
    failures: list[str] = []
    for path in python_paths:
        resolved = _safe_repo_path(str(path))
        if resolved is None:
            failures.append(f"{path}: unsafe path")
            continue
        if not resolved.exists():
            failures.append(f"{path}: file not found")
            continue
        try:
            source = resolved.read_text(encoding="utf-8")
            compile(source, str(resolved), "exec")
            checked.append(str(path))
        except Exception as exc:
            failures.append(f"{path}: {exc.__class__.__name__}: {exc}")

    if failures:
        return GateResult(
            name="syntax",
            passed=False,
            detail="; ".join(failures)[:800],
        )

    return GateResult(
        name="syntax",
        passed=True,
        detail=f"Compiled {len(checked)} Python file(s): {', '.join(checked)[:500]}",
    )


def _safe_pytest_command(command: str) -> list[str] | None:
    """Allow only bounded pytest commands against repo test paths."""
    try:
        parts = shlex.split(command or "", posix=True)
    except ValueError:
        return None

    if len(parts) < 3 or parts[:3] != ["python", "-m", "pytest"]:
        return None

    allowed_flags_with_values = {"-k", "-m", "--maxfail", "--tb"}
    allowed_single_flags = {"-q", "-s", "-x", "--disable-warnings", "--quiet", "--verbose", "-v"}
    test_targets = 0
    i = 3
    while i < len(parts):
        part = parts[i]
        if any(ch in part for ch in (";", "&", "|", "`", "$", ">", "<")):
            return None
        if part in allowed_single_flags:
            i += 1
            continue
        if part in allowed_flags_with_values:
            if i + 1 >= len(parts):
                return None
            if any(ch in parts[i + 1] for ch in (";", "&", "|", "`", "$", ">", "<")):
                return None
            i += 2
            continue
        normalized = part.replace("\\", "/")
        if normalized.startswith(("-", "../", "/")) or "/../" in normalized:
            return None
        if not (
            normalized.startswith("tests/")
            or normalized.startswith("api/tests/")
            or normalized == "tests"
            or normalized == "api/tests"
        ):
            return None
        test_targets += 1
        i += 1

    return parts if test_targets else None


def _unit_tests_gate_result(proposal: DevOrganProposal) -> GateResult:
    allowed = [_safe_pytest_command(cmd) for cmd in (proposal.tests or [])]
    commands = [cmd for cmd in allowed if cmd]
    if not commands:
        return GateResult(
            name="unit_tests",
            passed=False,
            detail="No allowed pytest command in proposal.tests.",
        )

    details: list[str] = []
    for cmd in commands:
        try:
            completed = subprocess.run(
                cmd,
                cwd=str(_APP_ROOT),
                capture_output=True,
                text=True,
                timeout=_PYTEST_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return GateResult(
                name="unit_tests",
                passed=False,
                detail=f"Timed out after {_PYTEST_TIMEOUT_SECONDS}s: {' '.join(cmd)}",
            )
        excerpt = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
        details.append(f"{' '.join(cmd)} -> exit {completed.returncode}; {excerpt[-500:]}")
        if completed.returncode != 0:
            return GateResult(
                name="unit_tests",
                passed=False,
                detail=" | ".join(details)[-1000:],
            )

    return GateResult(
        name="unit_tests",
        passed=True,
        detail=" | ".join(details)[-1000:],
    )


def _readiness_gate_results(
    proposal: DevOrganProposal,
    *,
    run_unit_tests: bool = False,
) -> list[GateResult]:
    """Compute non-destructive readiness gates.

    This is a sanity/pre-test pass only. It intentionally does not mark
    `unit_tests` as passed because tests must be run and recorded explicitly.
    """
    paths = [str(p) for p in (proposal.touched_paths or [])]
    joined_paths = "\n".join(paths).lower()
    text_surface = "\n".join(
        [
            joined_paths,
            str(proposal.title or "").lower(),
            str(proposal.problem or "").lower(),
            str(proposal.hypothesis or "").lower(),
        ]
    )

    rollback_ok = bool((proposal.rollback_plan or "").strip())
    secret_hit = next((m for m in _SECRET_PATH_MARKERS if m in text_surface), None)
    boundary_hit = next((m for m in _DATA_BOUNDARY_MARKERS if m in joined_paths), None)
    risk = RiskLevel(proposal.risk_level)

    gates = [
        GateResult(
            name="rollback_ready",
            passed=rollback_ok,
            detail="Rollback plan present." if rollback_ok else "Missing rollback plan.",
        ),
        GateResult(
            name="secret_scan",
            passed=secret_hit is None,
            detail="No obvious secret markers." if secret_hit is None else f"Secret marker found: {secret_hit}",
        ),
        GateResult(
            name="data_boundary",
            passed=boundary_hit is None and risk is not RiskLevel.CRITICAL,
            detail=(
                "No obvious tenant/auth/database boundary touch."
                if boundary_hit is None and risk is not RiskLevel.CRITICAL
                else f"Sensitive boundary marker/risk found: {boundary_hit or risk.value}"
            ),
        ),
        GateResult(
            name="contract_check",
            passed=True,
            detail="Sandbox API reachable; readiness check executed successfully.",
        ),
    ]
    gates.append(_syntax_gate_result(proposal))
    if run_unit_tests:
        gates.append(_unit_tests_gate_result(proposal))
    return gates


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_sandbox_stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    stage_counts = (
        await db.execute(
            select(DevOrganProposal.stage, func.count().label("n"))
            .group_by(DevOrganProposal.stage)
        )
    ).all()

    risk_counts = (
        await db.execute(
            select(DevOrganProposal.risk_level, func.count().label("n"))
            .group_by(DevOrganProposal.risk_level)
        )
    ).all()

    pending_approval = (
        await db.execute(
            select(func.count())
            .where(
                DevOrganProposal.stage == "proposed",
                DevOrganProposal.creator_verdict.is_(None),
            )
        )
    ).scalar_one()

    return {
        "stage_counts": {row.stage: row.n for row in stage_counts},
        "risk_counts": {row.risk_level: row.n for row in risk_counts},
        "pending_creator_review": pending_approval,
    }


# ---------------------------------------------------------------------------
# List proposals
# ---------------------------------------------------------------------------

@router.get("/proposals")
async def list_proposals(
    stage: Optional[str] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    verdict: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    q = select(DevOrganProposal).order_by(DevOrganProposal.created_at.desc())

    if stage:
        q = q.where(DevOrganProposal.stage == stage)
    if risk_level:
        q = q.where(DevOrganProposal.risk_level == risk_level)
    if verdict == "pending":
        q = q.where(DevOrganProposal.creator_verdict.is_(None))
    elif verdict in ("approved", "rejected"):
        q = q.where(DevOrganProposal.creator_verdict == verdict)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.limit(limit).offset(offset))).scalars().all()

    return {
        "total": total,
        "items": [_proposal_to_response(p) for p in rows],
    }


# ---------------------------------------------------------------------------
# Get single proposal
# ---------------------------------------------------------------------------

@router.get("/proposals/{proposal_id}")
async def get_proposal(
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    proposal = await db.get(DevOrganProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return _proposal_to_response(proposal)


# ---------------------------------------------------------------------------
# Submit proposal (brain or admin)
# ---------------------------------------------------------------------------

@router.post("/proposals", status_code=status.HTTP_201_CREATED)
async def submit_proposal(
    body: ProposalCreate,
    db: AsyncSession = Depends(get_db),
    _allow: bool = Depends(_allow_propose),
):
    risk = classify_risk(body.touched_paths).value

    row = DevOrganProposal(
        title=body.title,
        problem=body.problem,
        hypothesis=body.hypothesis,
        touched_paths=body.touched_paths,
        tests=body.tests,
        rollback_plan=body.rollback_plan,
        source=body.source,
        risk_level=risk,
        stage="proposed",
        gate_results=[],
        metadata_=body.metadata,
        created_by=body.created_by,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    logger.info("sandbox.proposal.created", proposal_id=str(row.id), title=row.title, risk=risk)
    return _proposal_to_response(row)


# ---------------------------------------------------------------------------
# Creator verdict (approve / reject)
# ---------------------------------------------------------------------------

@router.patch("/proposals/{proposal_id}/verdict")
async def set_verdict(
    proposal_id: uuid.UUID,
    body: VerdictUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    proposal = await db.get(DevOrganProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal.stage in ("deployed", "rolled_back"):
        raise HTTPException(status_code=409, detail=f"Proposal already in stage '{proposal.stage}'")

    proposal.creator_verdict = body.verdict
    proposal.creator_notes = body.notes
    proposal.decided_at = datetime.now(timezone.utc)

    if body.verdict == "approved" and proposal.stage == "proposed":
        proposal.stage = "diagnosed"

    await db.commit()
    await db.refresh(proposal)

    logger.info(
        "sandbox.verdict.set",
        proposal_id=str(proposal_id),
        verdict=body.verdict,
    )
    return _proposal_to_response(proposal)


# ---------------------------------------------------------------------------
# Run read-only readiness gates
# ---------------------------------------------------------------------------

@router.post("/proposals/{proposal_id}/readiness")
async def run_readiness(
    proposal_id: uuid.UUID,
    run_unit_tests: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    proposal = await db.get(DevOrganProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.stage in ("deployed", "rolled_back"):
        raise HTTPException(status_code=409, detail=f"Proposal already in stage '{proposal.stage}'")

    gate_results = _readiness_gate_results(proposal, run_unit_tests=run_unit_tests)
    existing = {
        str(g.get("name")): g
        for g in (proposal.gate_results or [])
        if isinstance(g, dict) and g.get("name")
    }
    for gate in gate_results:
        existing[gate.name] = {
            "name": gate.name,
            "passed": gate.passed,
            "detail": gate.detail,
        }

    proposal.gate_results = [existing[name] for name in sorted(existing)]
    proposal.gate_run_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(proposal)

    report = evaluate_promotion(
        ImprovementProposal(
            proposal_id=str(proposal_id),
            title=proposal.title,
            problem=proposal.problem,
            hypothesis=proposal.hypothesis,
            touched_paths=tuple(proposal.touched_paths or []),
            tests=tuple(proposal.tests or []),
            rollback_plan=proposal.rollback_plan or "",
            risk=RiskLevel(proposal.risk_level),
        ),
        [GateResult(name=g["name"], passed=bool(g["passed"]), detail=g.get("detail", "")) for g in proposal.gate_results],
    )

    return {
        "proposal": _proposal_to_response(proposal),
        "readiness": {
            "gates": proposal.gate_results,
            "promotion_report": {
                "decision": report.decision.value,
                "risk": report.risk.value,
                "passed_gates": list(report.passed_gates),
                "failed_gates": list(report.failed_gates),
                "missing_gates": list(report.missing_gates),
                "reason": report.reason,
            },
        },
    }


# ---------------------------------------------------------------------------
# Run QA gates manually
# ---------------------------------------------------------------------------

@router.post("/proposals/{proposal_id}/gates")
async def run_gates(
    proposal_id: uuid.UUID,
    body: GatesRunRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    proposal = await db.get(DevOrganProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    gate_results = [GateResult(name=g.gate_name, passed=g.passed, detail=g.detail) for g in body.gates]

    imp = ImprovementProposal(
        proposal_id=str(proposal_id),
        title=proposal.title,
        problem=proposal.problem,
        hypothesis=proposal.hypothesis,
        touched_paths=tuple(proposal.touched_paths or []),
        tests=tuple(proposal.tests or []),
        rollback_plan=proposal.rollback_plan or "",
        risk=RiskLevel(proposal.risk_level),
    )

    report = evaluate_promotion(imp, gate_results)

    proposal.gate_results = [
        {"name": g.name, "passed": g.passed, "detail": g.detail} for g in gate_results
    ]
    proposal.gate_run_at = datetime.now(timezone.utc)

    if report.decision.value == "ready_for_sandbox" and proposal.stage == "diagnosed":
        proposal.stage = "patched"
    elif report.decision.value == "ready_for_low_risk_promotion":
        proposal.stage = "validated"
    elif report.decision.value == "owner_approval_required":
        proposal.stage = "validated"
    elif report.decision.value == "block":
        proposal.stage = "blocked"

    await db.commit()
    await db.refresh(proposal)

    return {
        "proposal": _proposal_to_response(proposal),
        "promotion_report": {
            "decision": report.decision.value,
            "risk": report.risk.value,
            "passed_gates": list(report.passed_gates),
            "failed_gates": list(report.failed_gates),
            "missing_gates": list(report.missing_gates),
            "reason": report.reason,
        },
    }
