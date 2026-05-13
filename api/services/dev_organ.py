"""
MiganCore Dev Organ primitives.

This module defines the first safe skeleton for self-improvement decisions:
proposals, risk classification, gate evaluation, and append-only run logging.
It is intentionally side-effect free unless `append_run_log` is called.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence


class ImprovementStage(str, Enum):
    OBSERVED = "observed"
    DIAGNOSED = "diagnosed"
    PROPOSED = "proposed"
    PATCHED = "patched"
    TESTED = "tested"
    ITERATED = "iterated"
    VALIDATED = "validated"
    DEPLOYABLE = "deployable"
    DEPLOYED = "deployed"
    MONITORED = "monitored"
    ROLLED_BACK = "rolled_back"
    BLOCKED = "blocked"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PromotionDecision(str, Enum):
    BLOCK = "block"
    OWNER_APPROVAL_REQUIRED = "owner_approval_required"
    READY_FOR_SANDBOX = "ready_for_sandbox"
    READY_FOR_LOW_RISK_PROMOTION = "ready_for_low_risk_promotion"


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class ImprovementProposal:
    proposal_id: str
    title: str
    problem: str
    hypothesis: str
    touched_paths: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    rollback_plan: str = ""
    stage: ImprovementStage = ImprovementStage.PROPOSED
    risk: RiskLevel | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PromotionReport:
    proposal_id: str
    risk: RiskLevel
    decision: PromotionDecision
    passed_gates: tuple[str, ...]
    failed_gates: tuple[str, ...]
    missing_gates: tuple[str, ...]
    reason: str


LOW_RISK_PREFIXES = ("docs/", "README", "api/tests/", "tests/")
HIGH_RISK_MARKERS = (
    "auth",
    "jwt",
    "password",
    "license",
    "migration",
    "alembic",
    "database",
    "memory",
    "knowledge_graph",
    "docker-compose",
    "Dockerfile",
    "deploy",
)
CRITICAL_RISK_MARKERS = (
    ".env",
    "private.pem",
    "public.pem",
    "secret",
    "credential",
    "tenant",
    "rls",
)

BASE_GATES = frozenset(
    {
        "syntax",
        "unit_tests",
        "contract_check",
        "secret_scan",
        "data_boundary",
        "rollback_ready",
    }
)
LIVE_PROMOTION_GATES = frozenset({"health_check", "identity_check"})


def classify_risk(touched_paths: Sequence[str], *, live_deploy: bool = False) -> RiskLevel:
    """Classify the highest risk implied by touched paths and deploy intent."""

    normalized = tuple(path.replace("\\", "/") for path in touched_paths)
    joined = "\n".join(normalized).lower()

    if any(marker.lower() in joined for marker in CRITICAL_RISK_MARKERS):
        return RiskLevel.CRITICAL

    if any(marker.lower() in joined for marker in HIGH_RISK_MARKERS):
        return RiskLevel.HIGH

    if live_deploy:
        return RiskLevel.HIGH

    if normalized and all(path.startswith(LOW_RISK_PREFIXES) for path in normalized):
        return RiskLevel.LOW

    return RiskLevel.MEDIUM


def required_gates(risk: RiskLevel, *, live_deploy: bool = False) -> frozenset[str]:
    """Return the gates needed before a proposal can be promoted."""

    gates = set(BASE_GATES)
    if live_deploy or risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        gates.update(LIVE_PROMOTION_GATES)
    return frozenset(gates)


def evaluate_promotion(
    proposal: ImprovementProposal,
    gate_results: Iterable[GateResult],
    *,
    live_deploy: bool = False,
    low_risk_auto_promote_enabled: bool = False,
) -> PromotionReport:
    """Evaluate whether a proposed self-improvement can advance."""

    risk = proposal.risk or classify_risk(proposal.touched_paths, live_deploy=live_deploy)
    gates_by_name = {gate.name: gate for gate in gate_results}
    needed = required_gates(risk, live_deploy=live_deploy)

    missing = tuple(sorted(needed - gates_by_name.keys()))
    failed = tuple(sorted(name for name, gate in gates_by_name.items() if name in needed and not gate.passed))
    passed = tuple(sorted(name for name, gate in gates_by_name.items() if name in needed and gate.passed))

    if not proposal.rollback_plan.strip():
        failed = tuple(sorted(set(failed) | {"rollback_ready"}))

    if missing or failed:
        return PromotionReport(
            proposal_id=proposal.proposal_id,
            risk=risk,
            decision=PromotionDecision.BLOCK,
            passed_gates=passed,
            failed_gates=failed,
            missing_gates=missing,
            reason="Required gates are missing or failed.",
        )

    if risk in {RiskLevel.HIGH, RiskLevel.CRITICAL} or live_deploy:
        return PromotionReport(
            proposal_id=proposal.proposal_id,
            risk=risk,
            decision=PromotionDecision.OWNER_APPROVAL_REQUIRED,
            passed_gates=passed,
            failed_gates=(),
            missing_gates=(),
            reason="High-impact or live changes require owner approval.",
        )

    if risk is RiskLevel.LOW and low_risk_auto_promote_enabled:
        return PromotionReport(
            proposal_id=proposal.proposal_id,
            risk=risk,
            decision=PromotionDecision.READY_FOR_LOW_RISK_PROMOTION,
            passed_gates=passed,
            failed_gates=(),
            missing_gates=(),
            reason="Low-risk proposal passed all gates and auto-promote is enabled.",
        )

    return PromotionReport(
        proposal_id=proposal.proposal_id,
        risk=risk,
        decision=PromotionDecision.READY_FOR_SANDBOX,
        passed_gates=passed,
        failed_gates=(),
        missing_gates=(),
        reason="Proposal passed gates and is ready for sandbox iteration.",
    )


def append_run_log(path: str | Path, proposal: ImprovementProposal, report: PromotionReport) -> None:
    """Append an immutable JSONL record for a Dev Organ run."""

    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "proposal": _to_jsonable(asdict(proposal)),
        "report": _to_jsonable(asdict(report)),
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _to_jsonable(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value

