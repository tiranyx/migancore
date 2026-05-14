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
