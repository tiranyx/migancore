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
  - Submit (POST): X-Admin-Key or agent JWT with 'sandbox.propose' scope
  - Verdict (PATCH): X-Admin-Key only — creator action
  - Gates (POST): X-Admin-Key only
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
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
    ImprovementStage,
    classify_risk,
    evaluate_promotion,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/sandbox", tags=["sandbox"])


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _require_admin(x_admin_key: str = Header(default="", alias="X-Admin-Key")) -> None:
    if not settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Admin not configured")
    if x_admin_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")


def _allow_propose(x_admin_key: str = Header(default="", alias="X-Admin-Key")) -> bool:
    """Returns True if admin key; False means caller must have agent JWT (not enforced here yet)."""
    if settings.ADMIN_SECRET_KEY and x_admin_key == settings.ADMIN_SECRET_KEY:
        return True
    return True   # M1.7: open to brain submissions; tighten in M1.8 with JWT scope check


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
    source: str = Field(default="auto")
    metadata: dict = Field(default_factory=dict)
    created_by: str = Field(default="core_brain")


class VerdictUpdate(BaseModel):
    verdict: str = Field(..., pattern="^(approved|rejected)$")
    notes: str = Field(default="")


class GateInput(BaseModel):
    gate_name: str
    passed: bool
    detail: str = ""


class GatesRunRequest(BaseModel):
    gates: list[GateInput]


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
        "items": [p.to_dict() for p in rows],
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
    return proposal.to_dict()


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
    return row.to_dict()


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
    return proposal.to_dict()


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
        "proposal": proposal.to_dict(),
        "promotion_report": {
            "decision": report.decision.value,
            "risk": report.risk.value,
            "passed_gates": list(report.passed_gates),
            "failed_gates": list(report.failed_gates),
            "missing_gates": list(report.missing_gates),
            "reason": report.reason,
        },
    }
