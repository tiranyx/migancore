"""
JWT service for RS256 token creation and verification.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from jwt import PyJWTError

from config import settings, load_jwt_keys

# Lazy-load keys on first use
_private_key: Optional[str] = None
_public_key: Optional[str] = None


def _get_keys() -> tuple[str, str]:
    global _private_key, _public_key
    if _private_key is None or _public_key is None:
        _private_key, _public_key = load_jwt_keys()
    return _private_key, _public_key


def create_access_token(
    subject: str,
    tenant_id: str,
    role: str,
    scopes: str = "",
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Create a signed RS256 access token."""
    private_key, _ = _get_keys()

    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())

    payload = {
        "iss": settings.JWT_ISSUER,
        "sub": subject,
        "aud": settings.JWT_AUDIENCE,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "nbf": now,
        "iat": now,
        "jti": jti,
        "tenant_id": tenant_id,
        "role": role,
        "scope": scopes,
        "type": "access",
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, private_key, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, session_family: str, tenant_id: str) -> tuple[str, str, datetime]:
    """Create a signed RS256 refresh token.

    Returns: (token, jti, expires_at)
    """
    private_key, _ = _get_keys()

    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    expires_at = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "iss": settings.JWT_ISSUER,
        "sub": subject,
        "aud": settings.JWT_AUDIENCE,
        "exp": expires_at,
        "nbf": now,
        "iat": now,
        "jti": jti,
        "tenant_id": tenant_id,
        "session_family": session_family,
        "type": "refresh",
    }

    token = jwt.encode(payload, private_key, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires_at


def decode_token(token: str, token_type: Optional[str] = None) -> dict[str, Any]:
    """Decode and verify an RS256 token.

    Raises PyJWTError on any validation failure.
    """
    _, public_key = _get_keys()

    payload = jwt.decode(
        token,
        public_key,
        algorithms=[settings.JWT_ALGORITHM],
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
        options={"require": ["exp", "iat", "sub", "jti", "type"]},
    )

    if token_type and payload.get("type") != token_type:
        raise PyJWTError(f"Expected token type '{token_type}', got '{payload.get('type')}'")

    return payload


def get_token_jti(token: str) -> str:
    """Extract JTI from an unverified token (for revocation checks)."""
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload.get("jti", "")
    except PyJWTError:
        return ""
