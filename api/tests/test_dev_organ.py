from services.dev_organ import (
    GateResult,
    ImprovementProposal,
    PromotionDecision,
    RiskLevel,
    classify_risk,
    evaluate_promotion,
    required_gates,
)


def passing_gates(*, live_deploy: bool = False, risk: RiskLevel = RiskLevel.LOW):
    return [GateResult(name=name, passed=True) for name in required_gates(risk, live_deploy=live_deploy)]


def test_docs_only_change_is_low_risk():
    assert classify_risk(["docs/SELF_IMPROVEMENT_NORTHSTAR.md"]) is RiskLevel.LOW


def test_secret_or_tenant_paths_are_critical():
    assert classify_risk(["config/.env.production"]) is RiskLevel.CRITICAL
    assert classify_risk(["api/services/tenant_isolation.py"]) is RiskLevel.CRITICAL


def test_missing_gate_blocks_promotion():
    proposal = ImprovementProposal(
        proposal_id="m16-001",
        title="Docs update",
        problem="Need roadmap",
        hypothesis="A canonical doc improves handoff quality",
        touched_paths=("docs/SELF_IMPROVEMENT_NORTHSTAR.md",),
        rollback_plan="git revert <commit>",
    )

    report = evaluate_promotion(proposal, [GateResult("syntax", True)])

    assert report.decision is PromotionDecision.BLOCK
    assert "unit_tests" in report.missing_gates


def test_low_risk_can_be_marked_ready_when_auto_promote_enabled():
    proposal = ImprovementProposal(
        proposal_id="m16-002",
        title="Docs update",
        problem="Need roadmap",
        hypothesis="A canonical doc improves handoff quality",
        touched_paths=("docs/SELF_IMPROVEMENT_NORTHSTAR.md",),
        rollback_plan="git revert <commit>",
    )

    report = evaluate_promotion(
        proposal,
        passing_gates(),
        low_risk_auto_promote_enabled=True,
    )

    assert report.decision is PromotionDecision.READY_FOR_LOW_RISK_PROMOTION


def test_live_or_high_risk_changes_require_owner_approval():
    proposal = ImprovementProposal(
        proposal_id="m16-003",
        title="Deploy patch",
        problem="Need runtime change",
        hypothesis="Deployment fixes the issue",
        touched_paths=("api/Dockerfile",),
        rollback_plan="docker compose up previous image",
    )

    report = evaluate_promotion(
        proposal,
        passing_gates(live_deploy=True, risk=RiskLevel.HIGH),
        live_deploy=True,
    )

    assert report.risk is RiskLevel.HIGH
    assert report.decision is PromotionDecision.OWNER_APPROVAL_REQUIRED

