import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.routers import sandbox


def test_proposal_submit_requires_admin_key(monkeypatch):
    monkeypatch.setattr(sandbox.settings, "ADMIN_SECRET_KEY", "test-secret")

    with pytest.raises(HTTPException) as exc:
        sandbox._allow_propose("")

    assert exc.value.status_code == 401


def test_proposal_submit_accepts_admin_key(monkeypatch):
    monkeypatch.setattr(sandbox.settings, "ADMIN_SECRET_KEY", "test-secret")

    assert sandbox._allow_propose("test-secret") is True


def test_proposal_submit_disabled_when_admin_not_configured(monkeypatch):
    monkeypatch.setattr(sandbox.settings, "ADMIN_SECRET_KEY", "")

    with pytest.raises(HTTPException) as exc:
        sandbox._allow_propose("anything")

    assert exc.value.status_code == 503


def test_proposal_source_rejects_values_outside_db_constraint():
    with pytest.raises(ValidationError):
        sandbox.ProposalCreate(
            title="QA auth proposal smoke",
            problem="Verify invalid source is rejected before DB insert.",
            source="qa",
        )


def test_proposal_source_accepts_manual_for_admin_smoke():
    body = sandbox.ProposalCreate(
        title="QA auth proposal smoke",
        problem="Verify manual source is accepted before DB insert.",
        source="manual",
    )

    assert body.source == "manual"


def test_proposal_created_by_matches_db_length_limit():
    with pytest.raises(ValidationError):
        sandbox.ProposalCreate(
            title="QA auth proposal smoke",
            problem="Verify created_by is rejected before varchar overflow.",
            created_by="x" * 129,
        )


class DummyProposal:
    id = "proposal-1"
    title = "Docs proposal"
    problem = "Need docs"
    hypothesis = "Docs help handoff"
    touched_paths = ["docs/example.md"]
    tests = []
    rollback_plan = "git revert <sha>"
    risk_level = "low"
    stage = "proposed"
    gate_results = []
    gate_run_at = None
    creator_verdict = None
    creator_notes = None
    decided_at = None
    created_at = None
    updated_at = None
    created_by = "core_brain"
    source = "auto"
    metadata_ = {}

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "problem": self.problem,
            "hypothesis": self.hypothesis,
            "touched_paths": self.touched_paths,
            "tests": self.tests,
            "rollback_plan": self.rollback_plan,
            "risk_level": self.risk_level,
            "stage": self.stage,
            "gate_results": self.gate_results,
            "gate_run_at": self.gate_run_at,
            "creator_verdict": self.creator_verdict,
            "creator_notes": self.creator_notes,
            "decided_at": self.decided_at,
            "created_by": self.created_by,
            "source": self.source,
            "metadata": self.metadata_,
        }


def test_proposal_response_includes_lifecycle_gate_visibility():
    data = sandbox._proposal_to_response(DummyProposal())
    lifecycle = data["lifecycle"]

    assert lifecycle["risk"] == "low"
    assert lifecycle["required_gates"] == [
        "contract_check",
        "data_boundary",
        "rollback_ready",
        "secret_scan",
        "syntax",
        "unit_tests",
    ]
    assert lifecycle["passed_gates"] == []
    assert lifecycle["missing_gates"] == lifecycle["required_gates"]
    assert lifecycle["failed_gates"] == []
    assert lifecycle["next_action"] == "creator_review"


def test_proposal_response_marks_gate_failures_and_next_action():
    proposal = DummyProposal()
    proposal.creator_verdict = "approved"
    proposal.stage = "diagnosed"
    proposal.gate_results = [
        {"name": "syntax", "passed": True, "detail": "ok"},
        {"name": "secret_scan", "passed": False, "detail": "secret found"},
    ]

    data = sandbox._proposal_to_response(proposal)
    lifecycle = data["lifecycle"]

    assert lifecycle["passed_gates"] == ["syntax"]
    assert lifecycle["failed_gates"] == ["secret_scan"]
    assert "unit_tests" in lifecycle["missing_gates"]
    assert lifecycle["next_action"] == "fix_failed_gates"


def test_readiness_quick_gates_pass_for_low_risk_docs_proposal():
    proposal = DummyProposal()
    gates = sandbox._readiness_gate_results(proposal)
    by_name = {gate.name: gate for gate in gates}

    assert by_name["rollback_ready"].passed is True
    assert by_name["secret_scan"].passed is True
    assert by_name["data_boundary"].passed is True
    assert by_name["contract_check"].passed is True
    assert "unit_tests" not in by_name


def test_readiness_quick_gates_fail_for_secret_and_missing_rollback():
    proposal = DummyProposal()
    proposal.rollback_plan = ""
    proposal.touched_paths = ["config/.env.production"]
    proposal.risk_level = "critical"

    gates = sandbox._readiness_gate_results(proposal)
    by_name = {gate.name: gate for gate in gates}

    assert by_name["rollback_ready"].passed is False
    assert by_name["secret_scan"].passed is False
    assert by_name["data_boundary"].passed is False
