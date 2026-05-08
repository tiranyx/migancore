"""
Pydantic schemas for Agent Cloning API v2 (SP-008).

Clone = Spawn + Auto-generate License.
Child ADO gets a full license.json ready for Docker deployment.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CloneRequest(BaseModel):
    """Request to clone a parent agent into a licensed child ADO."""

    name: str = Field(..., min_length=1, max_length=255, description="Display name for the child agent")
    template_id: str | None = Field(None, max_length=64, description="Personality template to apply")
    persona_overrides: dict | None = Field(None, description="Optional persona field overrides")

    # License parameters
    client_name: str = Field(..., min_length=1, description="Legal company name of the client")
    tier: str = Field(..., description="BERLIAN | EMAS | PERAK | PERUNGGU")
    language_pack: list[str] = Field(default=["id"], description="Language codes")
    months: int | None = Field(None, description="License duration override (default from tier)")
    knowledge_return_enabled: bool = Field(
        default=False,
        description="Enable anonymized knowledge contribution to Hafidz Ledger — explicit opt-in",
    )
    knowledge_return_opt_in_types: list[str] | None = Field(
        None,
        description="Which types: dpo_pair, tool_pattern, domain_cluster, voice_pattern",
    )

    @field_validator("tier")
    @classmethod
    def _validate_tier(cls, v: str) -> str:
        allowed = {"BERLIAN", "EMAS", "PERAK", "PERUNGGU"}
        if v not in allowed:
            raise ValueError(f"tier must be one of {allowed}")
        return v

    @field_validator("knowledge_return_opt_in_types")
    @classmethod
    def _validate_types(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        allowed = {"dpo_pair", "tool_pattern", "domain_cluster", "voice_pattern"}
        invalid = set(v) - allowed
        if invalid:
            raise ValueError(f"Invalid knowledge_return_opt_in_types: {invalid}")
        return v


class LicenseInfo(BaseModel):
    """License data returned for the child ADO."""

    license_id: str
    client_name: str
    ado_display_name: str
    tier: str
    issued_date: str
    expiry_date: str
    state: str
    parent_version: str
    generation: int
    lineage_chain: list[str]
    knowledge_return_enabled: bool
    knowledge_return_opt_in_types: list[str] | None
    identity_hash: str
    signature: str


class CloneResponse(BaseModel):
    """Response for a successful clone operation."""

    ok: bool = True
    agent_id: str
    agent_name: str
    generation: int
    parent_agent_id: str
    license: LicenseInfo
    instruction: str = (
        "Save the license JSON as license.json in the child ADO Docker image. "
        "Set LICENSE_SECRET_KEY env var on the child instance to the validator key. "
        "The child will phone home via Hafidz Ledger when knowledge_return_enabled=true."
    )
