"""
API Keys router (Day 27).

Endpoints for managing long-lived API keys used by headless MCP/REST clients.

POST   /v1/api-keys           — create new key (returns full secret ONCE)
GET    /v1/api-keys           — list keys for current tenant (no secrets)
DELETE /v1/api-keys/{id}      — revoke key (idempotent)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from deps.auth import get_current_user
from deps.db import get_db
from models import User
from services.api_keys import create_key, list_keys, revoke_key

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/api-keys", tags=["api-keys"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    scopes: Optional[list[str]] = Field(
        default=None,
        description="Override default scopes. Defaults to ['tools:exec','chat:read','chat:write']",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="ISO-8601 datetime. NULL = no expiry.",
    )


class ApiKeyCreatedResponse(BaseModel):
    """Returned ONCE after key creation. The `key` field cannot be recovered later."""
    id: str
    name: str
    prefix: str
    key: str = Field(
        ...,
        description=(
            "The full API key. SAVE THIS NOW — it will not be shown again. "
            "Format: mgn_live_<id>_<secret>"
        ),
    )
    scopes: list[str]
    expires_at: Optional[datetime]
    created_at: datetime


class ApiKeySummary(BaseModel):
    """Returned in listings — no secret material."""
    id: str
    name: str
    prefix: str
    scopes: list[str]
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    revoked_at: Optional[datetime]
    created_at: datetime


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new API key for the current tenant.

    The full `key` field is returned ONCE in the response — store it immediately.
    Revocation: DELETE /v1/api-keys/{id}.
    """
    full_key, api_key = await create_key(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        name=body.name,
        scopes=body.scopes,
        expires_at=body.expires_at,
    )
    return ApiKeyCreatedResponse(
        id=str(api_key.id),
        name=api_key.name,
        prefix=api_key.prefix,
        key=full_key,
        scopes=list(api_key.scopes),
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get("", response_model=list[ApiKeySummary])
async def list_api_keys(
    include_revoked: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all API keys for the current tenant. Secrets are never included."""
    keys = await list_keys(db, current_user.tenant_id, include_revoked=include_revoked)
    return [
        ApiKeySummary(
            id=str(k.id),
            name=k.name,
            prefix=k.prefix,
            scopes=list(k.scopes),
            last_used_at=k.last_used_at,
            expires_at=k.expires_at,
            revoked_at=k.revoked_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    api_key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke an API key. Idempotent — returns 204 even if already revoked.

    Raises 404 only if the key does not exist or belongs to another tenant.
    """
    try:
        key_uuid = uuid.UUID(api_key_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    ok = await revoke_key(db, key_uuid, current_user.tenant_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return None
