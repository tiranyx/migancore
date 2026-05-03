"""
Authentication and authorization dependencies.
"""

import structlog
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from deps.db import get_db, set_tenant_context
from models import User
from services.jwt import decode_token, get_token_jti
from services.api_keys import is_api_key_format, verify_key

security = HTTPBearer(auto_error=False)
logger = structlog.get_logger()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate access token and return the authenticated user.

    Also sets PostgreSQL RLS tenant context so subsequent queries
    on tenant-scoped tables are automatically filtered.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    presented = credentials.credentials

    # Day 27: Check if presented credential is an API key (mgn_live_*) first
    # — this is cheaper than JWT decode (just a prefix check)
    if is_api_key_format(presented):
        api_key = await verify_key(db, presented)
        if api_key is None:
            logger.warning("auth.api_key_invalid", prefix_hint=presented[:14])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = str(api_key.user_id) if api_key.user_id else None
        tenant_id = str(api_key.tenant_id)
    else:
        # Standard JWT path
        try:
            payload = decode_token(presented, token_type="access")
        except Exception as exc:
            logger.warning(
                "auth.token_invalid",
                error=str(exc),
                jti=get_token_jti(presented),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Activate RLS tenant context BEFORE querying tenant-scoped tables
    await set_tenant_context(db, tenant_id)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Defense-in-depth: verify tenant match
    if str(user.tenant_id) != tenant_id:
        logger.warning(
            "auth.tenant_mismatch",
            user_id=user_id,
            token_tenant=tenant_id,
            user_tenant=str(user.tenant_id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Store tenant_id on request.state for downstream use
    request.state.tenant_id = tenant_id
    request.state.user_id = user_id

    return user


class RoleChecker:
    """Dependency factory for RBAC role checks."""

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user
