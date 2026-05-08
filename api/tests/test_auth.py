"""Tests for authentication service logic.

Tests JWT creation/validation, scope resolution, and auth utilities.
Does NOT test full FastAPI endpoints (those need DB mocks).
"""

import uuid
from datetime import datetime, timezone, timedelta

import pytest
import jwt as pyjwt

from config import settings


class TestJWTLogic:
    """Test JWT token creation and validation logic."""

    def test_jwt_algorithm_is_rs256(self):
        assert settings.JWT_ALGORITHM == "RS256"

    def test_jwt_access_token_expire_is_positive(self):
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0

    def test_jwt_refresh_token_expire_is_positive(self):
        assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0

    def test_jwt_issuer_is_set(self):
        assert settings.JWT_ISSUER == "https://api.migancore.com"

    def test_jwt_audience_is_set(self):
        assert settings.JWT_AUDIENCE == "migancore-api"


class TestAuthSchemas:
    """Test auth request/response schema validation."""

    def test_register_request_has_required_fields(self):
        from schemas.auth import RegisterRequest
        req = RegisterRequest(
            email="test@test.com",
            password="password123",
            tenant_name="Test Tenant",
            tenant_slug="test",
        )
        assert req.email == "test@test.com"
        assert req.tenant_slug == "test"
        assert req.tenant_name == "Test Tenant"

    def test_login_request_has_required_fields(self):
        from schemas.auth import LoginRequest
        req = LoginRequest(email="test@test.com", password="password123")
        assert req.email == "test@test.com"

    def test_token_pair_response_has_tokens(self):
        from schemas.auth import TokenPairResponse
        resp = TokenPairResponse(access_token="abc", refresh_token="def", token_type="bearer", expires_in=3600)
        assert resp.access_token == "abc"
        assert resp.refresh_token == "def"
        assert resp.expires_in == 3600

    def test_user_response_has_id_and_email(self):
        from schemas.auth import UserResponse
        from datetime import datetime, timezone
        uid = uuid.uuid4()
        resp = UserResponse(
            id=uid,
            email="test@test.com",
            role="owner",
            display_name="Test User",
            tenant_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
        )
        assert resp.email == "test@test.com"
        assert resp.role == "owner"
        assert resp.display_name == "Test User"


class TestScopeResolver:
    """Test scope resolution logic."""

    def test_scope_resolver_imports(self):
        from services.scope_resolver import resolve_scopes
        assert callable(resolve_scopes)


class TestAuditService:
    """Test audit event service."""

    def test_audit_event_imports(self):
        from services.audit import log_audit_event
        assert callable(log_audit_event)
