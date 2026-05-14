import pytest
from fastapi import HTTPException

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
