"""
Pydantic schemas for authentication endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = Field(None, max_length=255)
    tenant_name: str = Field(..., min_length=1, max_length=255)
    tenant_slug: str = Field(..., min_length=1, max_length=63)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    display_name: str | None
    tenant_id: uuid.UUID
    created_at: datetime


class LogoutResponse(BaseModel):
    message: str
