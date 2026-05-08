"""
Pydantic schemas for Hafidz Ledger endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Enums / constants (mirrors DB constraints)
# ─────────────────────────────────────────────────────────────────────────────

CONTRIBUTION_TYPES = ["dpo_pair", "tool_pattern", "domain_cluster", "voice_pattern"]
STATUSES = ["pending", "reviewing", "incorporated", "rejected"]


# ─────────────────────────────────────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────────────────────────────────────

class ContributionCreate(BaseModel):
    """Payload yang dikirim oleh child ADO untuk submit kontribusi."""

    child_license_id: str = Field(..., min_length=1, description="License ID child ADO")
    child_display_name: str = Field(..., min_length=1, description="Nama display child ADO")
    child_tier: str = Field(..., min_length=1, description="Tier child ADO (BERLIAN/EMAS/PERAK/PERUNGGU)")
    parent_version: str = Field(default="v0.3", description="Versi parent yang menerima kontribusi")
    contribution_type: str = Field(..., description="Tipe kontribusi")
    contribution_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 hash konten (deduplication)")
    anonymized_payload: dict[str, Any] = Field(default_factory=dict, description="Konten ter-anonymisasi (JSONB)")

    @field_validator("contribution_type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        if v not in CONTRIBUTION_TYPES:
            raise ValueError(f"Must be one of {CONTRIBUTION_TYPES}")
        return v


class ContributionReview(BaseModel):
    """Payload untuk parent review kontribusi (approve / reject)."""

    action: str = Field(..., description="approve | reject")
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Quality score 0.0–1.0")
    reject_reason: Optional[str] = Field(None, max_length=500, description="Alasan penolakan")
    incorporated_cycle: Optional[int] = Field(None, ge=1, description="Training cycle ke-berapa di-incorporate")

    @field_validator("action")
    @classmethod
    def _validate_action(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("action must be 'approve' or 'reject'")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class ContributionResponse(BaseModel):
    """Response shape untuk single contribution."""

    id: uuid.UUID
    child_license_id: str
    child_display_name: str
    child_tier: str
    parent_version: str
    contribution_type: str
    contribution_hash: str
    anonymized_payload: dict[str, Any]
    received_at: datetime
    quality_score: Optional[float]
    status: str
    incorporated_cycle: Optional[int]
    incorporated_at: Optional[datetime]
    reject_reason: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ContributionListResponse(BaseModel):
    """Response shape untuk list kontribusi."""

    items: list[ContributionResponse]
    total: int
    page: int
    page_size: int


class ContributionSummary(BaseModel):
    """Summary per child (from hafidz_child_summary view)."""

    child_license_id: str
    child_display_name: str
    child_tier: str
    parent_version: str
    total_contributions: int
    incorporated_count: int
    pending_count: int
    first_contribution: Optional[datetime]
    last_contribution: Optional[datetime]

    model_config = {"from_attributes": True}
