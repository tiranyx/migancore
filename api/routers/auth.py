"""
Authentication router: register, login, refresh, logout, me.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from deps.auth import get_current_user
from models import get_db, User, Tenant, RefreshToken
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


@router.post("/register", response_model=TokenPairResponse, status_code=status.HTTP_201_CREATED)
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

    # Create token pair
    scopes = "agents:read agents:write chat:write"
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
    )

    # Store refresh token hash
    rt = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token_plain(refresh_token),
        session_family=session_family,
        expires_at=expires_at,
    )
    db.add(rt)
    await db.commit()

    await log_audit_event(
        db=db,
        event_type="auth.register",
        tenant_id=str(tenant.id),
        user_id=str(user.id),
        details={"email": data.email, "tenant_slug": data.tenant_slug},
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()

    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenPairResponse)
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Authenticate user and issue token pair."""
    ip, ua = _client_info(request)

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        await log_audit_event(
            db=db,
            event_type="security.suspicious_activity",
            tenant_id=None,
            user_id=None,
            details={"reason": "failed_login", "email": data.email, "ip": ip},
            ip_address=ip,
            user_agent=ua,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)

    scopes = "agents:read agents:write chat:write"
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
    )

    rt = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token_plain(refresh_token),
        session_family=session_family,
        expires_at=expires_at,
    )
    db.add(rt)
    await db.commit()

    await log_audit_event(
        db=db,
        event_type="auth.login",
        tenant_id=str(user.tenant_id),
        user_id=str(user.id),
        details={"method": "password"},
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()

    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(data: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Rotate refresh token and issue new access token."""
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
    session_family = payload.get("session_family")
    token_hash = _hash_token_plain(data.refresh_token)

    # Find token in DB
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.session_family == session_family,
        )
    )
    rt = result.scalar_one_or_none()

    if not rt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if rt.is_revoked or rt.is_expired:
        # Token reuse detected — revoke entire session family
        await db.execute(
            RefreshToken.__table__.update()
            .where(RefreshToken.session_family == session_family)
            .where(RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.commit()

        await log_audit_event(
            db=db,
            event_type="security.session_terminated",
            tenant_id=None,
            user_id=uuid.UUID(user_id) if user_id else None,
            details={"reason": "token_reuse", "session_family": session_family, "ip": ip},
            ip_address=ip,
            user_agent=ua,
        )
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session terminated",
        )

    # Load user
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Revoke old refresh token
    rt.revoked_at = datetime.now(timezone.utc)

    # Issue new token pair
    scopes = "agents:read agents:write chat:write"
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
    )
    db.add(new_rt)
    await db.commit()

    await log_audit_event(
        db=db,
        event_type="auth.refresh",
        tenant_id=str(user.tenant_id),
        user_id=str(user.id),
        details={"session_family": session_family},
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()

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
    token_hash = _hash_token_plain(data.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()

    if rt and not rt.is_revoked:
        rt.revoked_at = datetime.now(timezone.utc)
        await db.commit()

        await log_audit_event(
            db=db,
            event_type="auth.logout",
            tenant_id=None,
            user_id=uuid.UUID(user_id) if user_id else None,
            details={"token_jti": payload.get("jti")},
            ip_address=ip,
            user_agent=ua,
        )
        await db.commit()

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
