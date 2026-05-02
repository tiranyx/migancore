"""
Authentication router: register, login, refresh, logout, me.

Security features:
- RS256 JWT with access (15min) + refresh (7d) rotation
- Argon2id password hashing
- Refresh token race-condition protection via atomic UPDATE
- Rate limiting on auth endpoints (slowapi)
- Audit logging with fire-and-forget async writer
"""

import asyncio
import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi.util import get_remote_address
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from deps.auth import get_current_user
from deps.db import get_db, set_tenant_context
from deps.rate_limit import limiter
from models import User, Tenant, RefreshToken
from schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenPairResponse,
    UserResponse,
    LogoutResponse,
)
from services.audit import log_audit_event
from services.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from services.password import hash_password, verify_password
from services.scope_resolver import resolve_scopes

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _hash_token_plain(plain_token: str) -> str:
    """Hash a plain refresh token for DB storage (not reversible)."""
    return hashlib.sha256(plain_token.encode()).hexdigest()


def _client_info(request: Request) -> tuple[str | None, str | None]:
    """Extract client IP and user agent from request."""
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


async def _fire_audit(
    event_type: str,
    tenant_id: str | uuid.UUID | None,
    user_id: str | uuid.UUID | None,
    details: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Fire audit event in a background task so it survives caller rollback."""
    # Detach the event data from the current session/transaction
    # and write via a fresh session in a background task.
    asyncio.create_task(
        _async_audit_write(
            event_type=event_type,
            tenant_id=str(tenant_id) if tenant_id else None,
            user_id=str(user_id) if user_id else None,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )


async def _async_audit_write(**kwargs) -> None:
    """Background task: write audit event with a fresh DB session."""
    from models.base import AsyncSessionLocal
    from services.audit import log_audit_event
    if AsyncSessionLocal is None:
        return
    async with AsyncSessionLocal() as session:
        try:
            await log_audit_event(db=session, **kwargs)
            await session.commit()
        except Exception:
            # Audit write failure must not crash the request
            pass


@router.post("/register", response_model=TokenPairResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(data: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Register a new tenant + owner user."""
    ip, ua = _client_info(request)

    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check slug uniqueness
    existing_slug = await db.execute(select(Tenant).where(Tenant.slug == data.tenant_slug))
    if existing_slug.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant slug already taken",
        )

    # Create tenant + user atomically
    tenant = Tenant(
        name=data.tenant_name,
        slug=data.tenant_slug,
        plan="free",
    )
    db.add(tenant)
    await db.flush()

    # Set RLS tenant context so the user insert is allowed
    await set_tenant_context(db, str(tenant.id))

    user = User(
        tenant_id=tenant.id,
        email=data.email,
        password_hash=hash_password(data.password),
        role="owner",
        display_name=data.display_name,
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        err = str(exc.orig)
        if "users_email_key" in err or "users.email" in err:
            raise HTTPException(409, "Email already registered")
        if "tenants_slug_key" in err or "tenants.slug" in err:
            raise HTTPException(409, "Tenant slug already taken")
        raise HTTPException(409, "Registration conflict")

    # Create token pair with role-derived scopes
    scopes = resolve_scopes(user.role, tenant.plan)
    access_token = create_access_token(
        subject=str(user.id),
        tenant_id=str(tenant.id),
        role=user.role,
        scopes=scopes,
    )

    session_family = secrets.token_urlsafe(16)
    refresh_token, refresh_jti, expires_at = create_refresh_token(
        subject=str(user.id),
        session_family=session_family,
        tenant_id=str(tenant.id),
    )

    # Store refresh token hash
    rt = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token_plain(refresh_token),
        session_family=session_family,
        expires_at=expires_at,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(rt)
    await db.commit()

    # Fire audit event (background, survives rollback)
    await _fire_audit(
        event_type="auth.register",
        tenant_id=str(tenant.id),
        user_id=str(user.id),
        details={"email": data.email, "tenant_slug": data.tenant_slug},
        ip_address=ip,
        user_agent=ua,
    )

    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenPairResponse)
@limiter.limit("10/minute")
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Authenticate user and issue token pair."""
    ip, ua = _client_info(request)

    # Login must bypass RLS because we don't know tenant_id yet.
    # Use the SECURITY DEFINER lookup function to find tenant_id,
    # then set tenant context and load the ORM user normally.
    from sqlalchemy import text
    lookup_result = await db.execute(
        text("SELECT * FROM auth_lookup_user_by_email(:email)"),
        {"email": data.email},
    )
    row = lookup_result.mappings().first()

    if row is None:
        await _fire_audit(
            event_type="security.suspicious_activity",
            tenant_id=None,
            user_id=None,
            details={"reason": "failed_login", "email": data.email, "ip": ip},
            ip_address=ip,
            user_agent=ua,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Set RLS context so subsequent ORM queries work
    await set_tenant_context(db, str(row["tenant_id"]))

    # Load ORM-attached user for updates
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        await _fire_audit(
            event_type="security.suspicious_activity",
            tenant_id=None,
            user_id=None,
            details={"reason": "failed_login", "email": data.email, "ip": ip},
            ip_address=ip,
            user_agent=ua,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)

    # Derive scopes from role + plan
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    plan = tenant.plan if tenant else "free"
    scopes = resolve_scopes(user.role, plan)

    access_token = create_access_token(
        subject=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
        scopes=scopes,
    )

    session_family = secrets.token_urlsafe(16)
    refresh_token, refresh_jti, expires_at = create_refresh_token(
        subject=str(user.id),
        session_family=session_family,
        tenant_id=str(user.tenant_id),
    )

    rt = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token_plain(refresh_token),
        session_family=session_family,
        expires_at=expires_at,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(rt)
    await db.commit()

    # Fire audit event (background)
    await _fire_audit(
        event_type="auth.login",
        tenant_id=str(user.tenant_id),
        user_id=str(user.id),
        details={"method": "password"},
        ip_address=ip,
        user_agent=ua,
    )

    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenPairResponse)
@limiter.limit("10/minute")
async def refresh(data: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Rotate refresh token and issue new access token.

    Uses atomic UPDATE ... WHERE revoked_at IS NULL to prevent race conditions
    where two concurrent requests with the same refresh token both mint
    replacement tokens.
    """
    ip, ua = _client_info(request)

    try:
        payload = decode_token(data.refresh_token, token_type="refresh")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    session_family = payload.get("session_family")
    token_hash = _hash_token_plain(data.refresh_token)

    # Set RLS tenant context before any queries on tenant-scoped tables
    if tenant_id:
        await set_tenant_context(db, tenant_id)

    # ATOMIC UPDATE: revoke the token only if it hasn't been revoked yet.
    # This prevents concurrent refresh requests from both succeeding.
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.session_family == session_family,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
        .returning(RefreshToken)
    )
    rt = result.scalar_one_or_none()

    if not rt:
        # Token was already revoked (concurrent refresh or reuse)
        # Terminate entire session family
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.session_family == session_family)
            .where(RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()

        await _fire_audit(
            event_type="security.session_terminated",
            tenant_id=tenant_id,
            user_id=uuid.UUID(user_id) if user_id else None,
            details={"reason": "token_reuse_or_race", "session_family": session_family, "ip": ip},
            ip_address=ip,
            user_agent=ua,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session terminated",
        )

    # Check expiration after atomic lock acquisition
    if rt.is_expired:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Load user
    user_result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = user_result.scalar_one_or_none()
    if not user:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Derive scopes
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    plan = tenant.plan if tenant else "free"
    scopes = resolve_scopes(user.role, plan)

    # Issue new token pair
    access_token = create_access_token(
        subject=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
        scopes=scopes,
    )

    new_refresh_token, new_refresh_jti, expires_at = create_refresh_token(
        subject=str(user.id),
        session_family=session_family,
    )

    # Store new refresh token
    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token_plain(new_refresh_token),
        session_family=session_family,
        expires_at=expires_at,
        replaced_by_token_hash=token_hash,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(new_rt)
    await db.commit()

    # Fire audit event (background)
    await _fire_audit(
        event_type="auth.refresh",
        tenant_id=str(user.tenant_id),
        user_id=str(user.id),
        details={"session_family": session_family},
        ip_address=ip,
        user_agent=ua,
    )

    return TokenPairResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(data: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Revoke a refresh token (logout)."""
    ip, ua = _client_info(request)

    try:
        payload = decode_token(data.refresh_token, token_type="refresh")
    except Exception:
        return LogoutResponse(message="Logged out successfully")

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    token_hash = _hash_token_plain(data.refresh_token)

    # Atomic update: revoke only if not already revoked
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .where(RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
        .returning(RefreshToken)
    )
    rt = result.scalar_one_or_none()

    if rt and not rt.is_expired:
        await db.commit()

        await _fire_audit(
            event_type="auth.logout",
            tenant_id=tenant_id,
            user_id=uuid.UUID(user_id) if user_id else None,
            details={"token_jti": payload.get("jti")},
            ip_address=ip,
            user_agent=ua,
        )

    return LogoutResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        display_name=current_user.display_name,
        tenant_id=current_user.tenant_id,
        created_at=current_user.created_at,
    )
