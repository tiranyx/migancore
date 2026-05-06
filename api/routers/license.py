"""
ADO License Router — Day 61
License management endpoints: status check, mint (internal), info (public).

Endpoints:
  GET  /license/info    → Public: display_name, tier, days_remaining (no secrets)
  GET  /license/status  → Admin: full validation result
  POST /license/mint    → Internal: generate a new license (x-internal-key protected)
  POST /license/batch   → Internal: batch mint multiple licenses
"""

from __future__ import annotations

import json
import os
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from services.license import (
    LicenseTier,
    LicenseMode,
    batch_mint,
    get_current_license,
    get_ado_display_name,
    mint_license,
    save_license,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/license", tags=["license"])


# ─────────────────────────────────────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────────────────────────────────────

def _require_admin(x_admin_key: Optional[str] = Header(None, alias="x-admin-key")) -> None:
    """Require X-Admin-Key header matching ADMIN_SECRET_KEY env var."""
    from config import settings
    admin_key = getattr(settings, "ADMIN_SECRET_KEY", "")
    if not admin_key or x_admin_key != admin_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


def _require_internal(x_internal_key: Optional[str] = Header(None, alias="x-internal-key")) -> None:
    """
    Require X-Internal-Key header (for license minting — mirrors Ixonomic).
    Only the Migancore platform server knows this key.
    """
    internal_key = os.environ.get("LICENSE_INTERNAL_KEY", "")
    if not internal_key or x_internal_key != internal_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Internal access required — this endpoint is Migancore platform only",
        )


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENDPOINT — safe to expose to any authenticated user
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/info")
async def get_license_info() -> dict:
    """
    Public license info — display_name, tier, status.
    No secrets. Safe for frontend to call.
    """
    lic = get_current_license()
    if lic is None:
        return {
            "ado_display_name": get_ado_display_name(),
            "mode": "LOADING",
            "powered_by": "Migancore × PT Tiranyx Digitalis Nusantara",
        }

    # Redact sensitive fields — only expose what's safe for client-side display
    return {
        "ado_display_name":  lic.ado_display_name or get_ado_display_name(),
        "mode":              lic.mode.value,
        "tier":              lic.tier,
        "days_remaining":    lic.days_remaining,
        "expiry_date":       lic.expiry_date,
        "is_operational":    lic.is_operational,
        "powered_by":        "Migancore × PT Tiranyx Digitalis Nusantara",
    }


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN ENDPOINT — full status including reason and license_id
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/status", dependencies=[Depends(_require_admin)])
async def get_license_status() -> dict:
    """
    Full license validation result — admin only.
    Includes license_id, client_name, mode, reason.
    """
    lic = get_current_license()
    if lic is None:
        return {"status": "not_loaded", "detail": "license not validated yet"}
    return lic.to_dict()


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL MINTING ENDPOINTS — Migancore platform only (x-internal-key)
# ─────────────────────────────────────────────────────────────────────────────

class MintRequest(BaseModel):
    client_name: str = Field(..., description="Legal company name of client")
    ado_display_name: str = Field(..., description="White-label name (e.g. SARI, LEX)")
    tier: str = Field(..., description="BERLIAN | EMAS | PERAK | PERUNGGU")
    language_pack: list[str] = Field(default=["id"], description="Language codes")
    months: Optional[int] = Field(None, description="Override default duration")
    save_path: Optional[str] = Field(None, description="If set, save license.json to this path")
    # Genealogy — "silsilah" of the ADO child (Day 62: Anak Kembali ke Induk)
    parent_version: str = Field(default="v0.3", description="Migancore brain version that mints this ADO")
    generation: int = Field(default=1, description="1=direct child of Migancore, 2=nested white-label reseller")
    lineage_chain: Optional[list[str]] = Field(None, description="Full lineage path; auto-computed if omitted")
    # Knowledge return — opt-in to 'Anak Kembali ke Induk' federated learning
    knowledge_return_enabled: bool = Field(default=True, description="Enable anonymized knowledge contribution to Hafidz Ledger")
    knowledge_return_opt_in_types: Optional[list[str]] = Field(None, description="Which types: dpo_pair, tool_pattern, domain_cluster")


class BatchMintRequest(BaseModel):
    clients: list[MintRequest]


@router.post("/mint", dependencies=[Depends(_require_internal)])
async def mint_single(req: MintRequest) -> dict:
    """
    Mint a single ADO license.

    Mirrors Ixonomic's POST /internal/mint.
    Protected by x-internal-key — only Migancore platform server can call this.

    Returns the complete license dict ready to embed in a Docker image.
    """
    secret_key = os.environ.get("LICENSE_SECRET_KEY", "")
    if not secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LICENSE_SECRET_KEY not configured on issuing server",
        )

    try:
        tier = LicenseTier(req.tier)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {req.tier}. Must be one of {[t.value for t in LicenseTier]}",
        )

    license_data = mint_license(
        client_name=req.client_name,
        ado_display_name=req.ado_display_name,
        tier=tier,
        language_pack=req.language_pack,
        secret_key=secret_key,
        months=req.months,
        parent_version=req.parent_version,
        generation=req.generation,
        lineage_chain=req.lineage_chain,
        knowledge_return_enabled=req.knowledge_return_enabled,
        knowledge_return_opt_in_types=req.knowledge_return_opt_in_types,
    )

    if req.save_path:
        try:
            save_license(license_data, req.save_path)
        except Exception as exc:
            logger.warning("license.save_failed", path=req.save_path, error=str(exc))

    return {
        "ok": True,
        "license": license_data,
        "instruction": (
            "Save this JSON as license.json in the ADO Docker image at $LICENSE_PATH. "
            "Set LICENSE_SECRET_KEY env var on the ADO instance to the validator key. "
            "The entropy and identity_hash fields are required for offline validation."
        ),
    }


@router.post("/batch", dependencies=[Depends(_require_internal)])
async def mint_batch_endpoint(req: BatchMintRequest) -> dict:
    """
    Batch mint — issue multiple licenses at once.

    Mirrors Ixonomic's mintBatch(denomination, walletId, qty).
    Useful for reseller program: one API call → 10+ client licenses.
    """
    secret_key = os.environ.get("LICENSE_SECRET_KEY", "")
    if not secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LICENSE_SECRET_KEY not configured",
        )

    clients_list = [c.model_dump() for c in req.clients]
    results = batch_mint(clients_list, secret_key)

    ok_count = sum(1 for r in results if r.get("ok"))
    fail_count = len(results) - ok_count

    return {
        "total": len(results),
        "ok": ok_count,
        "failed": fail_count,
        "results": results,
    }
