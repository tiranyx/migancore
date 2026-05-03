"""
API Keys service (Day 27).

Long-lived authentication for headless MCP/REST clients.

Format:
    mgn_live_<key_id_8hex>_<secret_43chars_urlsafe>

Verification flow (hot path):
    1. Parse "Authorization: Bearer mgn_live_..."
    2. Compute hmac(pepper, presented).digest() → key_hash
    3. SQL: SELECT * FROM api_keys
              WHERE key_hash=$1 AND revoked_at IS NULL
                AND (expires_at IS NULL OR expires_at > now())
    4. Optional Redis check: revoked:<hash_hex> for sub-1s revoke

Security notes:
- 256-bit secret entropy → brute force infeasible
- HMAC verify is constant-time at SQL layer (indexed binary equality)
- Server pepper makes hashes useless if DB leaks (must also leak env)
- Never log full keys; structlog middleware redacts Authorization header
- Stripe/OpenAI/Anthropic all use this exact pattern
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.api_key import ApiKey

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Server pepper (loaded once, validated at startup)
# ---------------------------------------------------------------------------
def _get_pepper() -> bytes:
    """Get HMAC pepper from env. Lazily validated on first use."""
    pepper = os.environ.get("API_KEY_PEPPER", "").strip()
    if not pepper:
        # Fallback to JWT private key bytes (already secret) for dev convenience.
        # Production should set explicit API_KEY_PEPPER.
        from config import settings
        try:
            with open(settings.JWT_PRIVATE_KEY_PATH, "rb") as f:
                pepper = hashlib.sha256(f.read()).hexdigest()
        except Exception:
            raise RuntimeError(
                "API_KEY_PEPPER env var not set and JWT key fallback failed. "
                "Set API_KEY_PEPPER to a secret 32+ char string."
            )
    return pepper.encode("utf-8")


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------
def generate_key_pair() -> tuple[str, str, bytes]:
    """Generate a new API key.

    Returns:
        (full_key, prefix, key_hash)

    full_key:  Show to user ONCE. Format: mgn_live_<id>_<secret>
    prefix:    Safe to store/show in UI. ~20 chars (mgn_live_<id>).
    key_hash:  HMAC-SHA256(pepper, full_key). Stored in DB.
    """
    key_id = secrets.token_hex(4)              # 8 hex chars (32 bits) — collision-safe
    secret = secrets.token_urlsafe(32)         # ~43 chars (256 bits entropy)
    full = f"mgn_live_{key_id}_{secret}"
    prefix = f"mgn_live_{key_id}"
    key_hash = hmac.new(_get_pepper(), full.encode("utf-8"), hashlib.sha256).digest()
    return full, prefix, key_hash


def hash_key(presented_key: str) -> bytes:
    """Compute HMAC hash of a presented key (for verify lookup)."""
    return hmac.new(_get_pepper(), presented_key.encode("utf-8"), hashlib.sha256).digest()


def is_api_key_format(token: str) -> bool:
    """Cheap pre-check: does this look like a MiganCore API key?"""
    return token.startswith("mgn_live_") and len(token) > 50


# ---------------------------------------------------------------------------
# Verify (hot path)
# ---------------------------------------------------------------------------
async def verify_key(db: AsyncSession, presented_key: str) -> Optional[ApiKey]:
    """Verify an API key. Returns ApiKey row if valid, None otherwise.

    Updates last_used_at on success (best-effort, async write).
    """
    if not is_api_key_format(presented_key):
        return None

    key_hash = hash_key(presented_key)

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash)
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        return None

    # Check lifecycle
    if api_key.revoked_at is not None:
        logger.info("api_key.rejected_revoked", prefix=api_key.prefix)
        return None
    if api_key.expires_at is not None and api_key.expires_at <= now:
        logger.info("api_key.rejected_expired", prefix=api_key.prefix)
        return None

    # Update last_used_at — fire and forget (don't slow hot path)
    try:
        await db.execute(
            update(ApiKey).where(ApiKey.id == api_key.id).values(last_used_at=now)
        )
        await db.commit()
    except Exception as exc:
        logger.warning("api_key.last_used_update_failed", error=str(exc))

    return api_key


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
async def create_key(
    db: AsyncSession,
    *,
    tenant_id,
    user_id,
    name: str,
    scopes: Optional[list[str]] = None,
    expires_at: Optional[datetime] = None,
) -> tuple[str, ApiKey]:
    """Create a new API key.

    Returns:
        (full_key_string, ApiKey row)

    full_key_string: ONLY returned this one time. NOT recoverable later.
    """
    full, prefix, key_hash = generate_key_pair()

    api_key = ApiKey(
        tenant_id=tenant_id,
        user_id=user_id,
        name=name,
        prefix=prefix,
        key_hash=key_hash,
        scopes=scopes or ["tools:exec", "chat:read", "chat:write"],
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    logger.info(
        "api_key.created",
        api_key_id=str(api_key.id),
        prefix=prefix,
        tenant_id=str(tenant_id),
        scopes=api_key.scopes,
    )
    return full, api_key


# ---------------------------------------------------------------------------
# Revoke
# ---------------------------------------------------------------------------
async def revoke_key(db: AsyncSession, api_key_id, tenant_id) -> bool:
    """Revoke an API key. Returns True if revoked, False if not found / not owned."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == api_key_id,
            ApiKey.tenant_id == tenant_id,
        )
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        return False
    if api_key.revoked_at is not None:
        return True  # already revoked, idempotent

    api_key.revoked_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info("api_key.revoked", api_key_id=str(api_key.id), prefix=api_key.prefix)
    return True


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
async def list_keys(db: AsyncSession, tenant_id, include_revoked: bool = False) -> list[ApiKey]:
    """List all API keys for a tenant."""
    stmt = select(ApiKey).where(ApiKey.tenant_id == tenant_id).order_by(ApiKey.created_at.desc())
    if not include_revoked:
        stmt = stmt.where(ApiKey.revoked_at.is_(None))
    result = await db.execute(stmt)
    return list(result.scalars().all())
