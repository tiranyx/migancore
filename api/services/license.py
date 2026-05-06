"""
ADO License System — Minting, Validation & Enforcement
Day 61 — Inspired by Ixonomic coin minting pipeline (bank-tiranyx)

Pattern: Ixonomic mints "coins" in batches with SHA-256 identity + HMAC-SHA256 signature.
ADO licenses follow the exact same cryptographic pattern — each license IS a "coin"
representing the right to run an ADO instance.

4-stage pipeline (mirroring Ixonomic's TIBR → NAQQASH → VALIDATUR → BANK):
  1. MANIFES   → license request: client_name, tier, display_name, language_pack
  2. IDENTITAS → assign license_id, compute entropy, generate identity_hash
  3. STEMPEL   → HMAC-SHA256(LICENSE_SECRET_KEY, identity_hash) = signature
  4. SEGEL     → serialize to license.json (ready for embed in Docker image)

Tier naming (parallel to Ixonomic denominations — Nusantara cultural encoding):
  BERLIAN  (Diamond)  → Government/Air-Gapped — perpetual, premium, no phone-home
  EMAS     (Gold)     → Enterprise — unlimited instances, SLA, dedicated support
  PERAK    (Silver)   → Pro — max 5 instances, full MCP, multi-ADO
  PERUNGGU (Bronze)   → Basic — 1 instance, standard tools

State machine (parallel to Ixonomic MINTED → TRANSFERRED → USED → RETURNED):
  ISSUED → ACTIVE → SUSPENDED → REVOKED

Author: Claude Code (Day 61)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS & ENUMS
# ─────────────────────────────────────────────────────────────────────────────

POWERED_BY = "Migancore × PT Tiranyx Digitalis Nusantara"
PRODUCT = "Migancore ADO Engine"

class LicenseTier(str, Enum):
    """ADO license tiers — named with Nusantara cultural encoding (like Ixonomic)."""
    BERLIAN = "BERLIAN"    # Diamond — Government/Air-Gapped, perpetual
    EMAS = "EMAS"          # Gold — Enterprise, unlimited instances
    PERAK = "PERAK"        # Silver — Pro, max 5 instances
    PERUNGGU = "PERUNGGU"  # Bronze — Basic, 1 instance

class LicenseState(str, Enum):
    """License lifecycle state machine."""
    ISSUED = "ISSUED"        # Freshly minted, not yet activated
    ACTIVE = "ACTIVE"        # Running, valid
    SUSPENDED = "SUSPENDED"  # Temporarily disabled (non-payment, review)
    REVOKED = "REVOKED"      # Permanently cancelled

class LicenseMode(str, Enum):
    """Runtime mode determined by license validation result."""
    FULL = "FULL"            # All features available
    READ_ONLY = "READ_ONLY"  # Expired license — read/respond only, no new training
    DEMO = "DEMO"            # No license — limited demo mode (configurable)
    INVALID = "INVALID"      # Tampered or revoked license — refuse to start

# Tier constraints
TIER_CONFIG: dict[LicenseTier, dict] = {
    LicenseTier.BERLIAN:  {"max_instances": 999, "default_months": 120},  # 10 years
    LicenseTier.EMAS:     {"max_instances": 50,  "default_months": 12},
    LicenseTier.PERAK:    {"max_instances": 5,   "default_months": 1},
    LicenseTier.PERUNGGU: {"max_instances": 1,   "default_months": 1},
}

# Grace period after expiry before downgrade to READ_ONLY
EXPIRY_GRACE_DAYS = 7


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2: IDENTITAS — Identity hash generation
# ─────────────────────────────────────────────────────────────────────────────

def _build_identity_hash(
    license_id: str,
    client_name: str,
    tier: str,
    issued_date: str,
    expiry_date: str,
    entropy: str,
) -> str:
    """
    Compute identity_hash = SHA-256(license_id:client_name:tier:issued:expiry:entropy)

    Mirrors Ixonomic's buildCoinIdentity():
    SHA-256(coinId:quranRef:ayahText:entropy:denomination:mintedAtUnix)

    The colon-delimited canonical string prevents field-boundary attacks.
    """
    canonical = ":".join([
        license_id,
        client_name,
        tier,
        issued_date,
        expiry_date,
        entropy,
    ])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3: STEMPEL — HMAC-SHA256 signature
# ─────────────────────────────────────────────────────────────────────────────

def _sign(identity_hash: str, secret_key: str) -> str:
    """
    Compute HMAC-SHA256(secret_key, identity_hash).

    Mirrors Ixonomic's:  HMAC-SHA256(MINT_SECRET_KEY, identityHash)

    The secret_key NEVER leaves the Migancore issuer system.
    The deployed license only carries the identity_hash + signature,
    so validators can verify without the secret.
    """
    return hmac.new(
        secret_key.encode("utf-8"),
        identity_hash.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# MINTER — Stage 1 (MANIFES) + 2 (IDENTITAS) + 3 (STEMPEL) + 4 (SEGEL)
# ─────────────────────────────────────────────────────────────────────────────

def mint_license(
    client_name: str,
    ado_display_name: str,
    tier: LicenseTier,
    language_pack: list[str],
    secret_key: str,
    months: Optional[int] = None,
    product_version: str = "v0.5",
    parent_version: str = "v0.3",
    generation: int = 1,
    lineage_chain: Optional[list[str]] = None,
    knowledge_return_enabled: bool = True,
    knowledge_return_opt_in_types: Optional[list[str]] = None,
) -> dict:
    """
    MANIFES → IDENTITAS → STEMPEL → SEGEL

    Mint a single ADO license (a "coin" in the Ixonomic metaphor).
    Returns a dict ready to be serialized as license.json.

    Now includes:
    - genealogy block: tracks which Migancore version "gave birth" to this ADO,
      generation depth, and full lineage chain (for white-label nested clones)
    - knowledge_return block: opt-in config for "Anak Kembali ke Induk" —
      anonymized domain knowledge flows back to Hafidz Ledger on child death/expiry

    Args:
        client_name:                    Legal company name of the client
        ado_display_name:               White-label name for this ADO (e.g. "SARI", "LEX")
        tier:                           LicenseTier enum
        language_pack:                  List of supported languages ["id", "en", "zh"]
        secret_key:                     LICENSE_SECRET_KEY — NEVER stored in license file
        months:                         Override default license duration
        product_version:                ADO Engine version string
        parent_version:                 Migancore brain version that "gave birth" to this ADO
        generation:                     1 = direct child of Migancore; 2 = reseller white-label
        lineage_chain:                  Full ancestry path, e.g. ["migancore:v0.3"]
        knowledge_return_enabled:       Whether this ADO opts into knowledge contribution
        knowledge_return_opt_in_types:  Which contribution types are enabled

    Returns:
        License dict — write to license.json on client VPS
    """
    tier_config = TIER_CONFIG[tier]
    now = datetime.now(timezone.utc)
    duration_months = months or tier_config["default_months"]
    expiry = now + timedelta(days=30 * duration_months)

    license_id = str(uuid.uuid4())
    entropy = secrets.token_hex(16)  # 128 bits — prevents preimage attacks
    issued_str = now.isoformat()
    expiry_str = expiry.isoformat()

    # IDENTITAS — Stage 2
    identity_hash = _build_identity_hash(
        license_id=license_id,
        client_name=client_name,
        tier=tier.value,
        issued_date=issued_str,
        expiry_date=expiry_str,
        entropy=entropy,
    )

    # STEMPEL — Stage 3
    signature = _sign(identity_hash, secret_key)

    # Genealogy — tracks the parent-child lineage ("silsilah")
    # generation=1 → direct child of Migancore
    # generation=2 → child of a reseller's white-label ADO (nested clone)
    computed_lineage = lineage_chain or [f"migancore:{parent_version}"]
    genealogy = {
        "parent_id":      "migancore",
        "parent_version": parent_version,
        "generation":     generation,
        "lineage_chain":  computed_lineage,
    }

    # Knowledge Return — "Anak Kembali ke Induk" opt-in config
    # Anonymized DPO pairs, tool patterns, domain clusters flow back to Hafidz Ledger
    opt_in_types = knowledge_return_opt_in_types or ["dpo_pair", "tool_pattern"]
    knowledge_return = {
        "enabled":      knowledge_return_enabled,
        "endpoint":     "https://api.migancore.com/hafidz/contribute",
        "opt_in_types": opt_in_types,
        "anonymization": "auto",  # PII stripped inside child ADO before transmission
    }

    # SEGEL — Stage 4
    license_data = {
        "license_id":       license_id,
        "client_name":      client_name,
        "ado_display_name": ado_display_name,
        "issued_by":        "PT Tiranyx Digitalis Nusantara",
        "product":          f"{PRODUCT} {product_version}",
        "powered_by":       POWERED_BY,
        "issued_date":      issued_str,
        "expiry_date":      expiry_str,
        "tier":             tier.value,
        "max_instances":    tier_config["max_instances"],
        "language_pack":    language_pack,
        "state":            LicenseState.ISSUED.value,
        # ─── Genealogy + Knowledge Return (Day 62 addition) ───────────────────
        "genealogy":        genealogy,
        "knowledge_return": knowledge_return,
        # ─── Cryptographic seal ───────────────────────────────────────────────
        "entropy":          entropy,      # Needed for validator to recompute hash
        "identity_hash":    identity_hash,
        "signature":        signature,
    }

    logger.info(
        "license.minted",
        license_id=license_id,
        client=client_name,
        display_name=ado_display_name,
        tier=tier.value,
        expiry=expiry_str,
        generation=generation,
        parent_version=parent_version,
        knowledge_return=knowledge_return_enabled,
    )
    return license_data


def batch_mint(clients: list[dict], secret_key: str) -> list[dict]:
    """
    Batch production — mint multiple licenses in one call.

    Mirrors Ixonomic's mintBatch(denomination, walletId, qty).

    Each client dict must contain: client_name, ado_display_name, tier,
    language_pack, and optionally: months, parent_version, generation,
    lineage_chain, knowledge_return_enabled, knowledge_return_opt_in_types.

    Example:
        clients = [
            {"client_name": "RS Sari Husada", "ado_display_name": "SARI",
             "tier": LicenseTier.PERAK, "language_pack": ["id"],
             "knowledge_return_enabled": True},
            {"client_name": "Lexindo Law", "ado_display_name": "LEX",
             "tier": LicenseTier.PERUNGGU, "language_pack": ["id", "en"],
             "knowledge_return_enabled": False},
        ]
        licenses = batch_mint(clients, SECRET_KEY)
    """
    results = []
    for client in clients:
        try:
            tier = LicenseTier(client["tier"]) if isinstance(client["tier"], str) else client["tier"]
            lic = mint_license(
                client_name=client["client_name"],
                ado_display_name=client["ado_display_name"],
                tier=tier,
                language_pack=client.get("language_pack", ["id"]),
                secret_key=secret_key,
                months=client.get("months"),
                parent_version=client.get("parent_version", "v0.3"),
                generation=client.get("generation", 1),
                lineage_chain=client.get("lineage_chain"),
                knowledge_return_enabled=client.get("knowledge_return_enabled", True),
                knowledge_return_opt_in_types=client.get("knowledge_return_opt_in_types"),
            )
            results.append({"ok": True, "license": lic})
        except Exception as exc:
            results.append({"ok": False, "error": str(exc), "client": client.get("client_name")})
    return results


def save_license(license_data: dict, path: str) -> None:
    """Write license.json to disk (for embedding in Docker image or VPS deployment)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(license_data, f, indent=2, ensure_ascii=False)
    logger.info("license.saved", path=path, license_id=license_data.get("license_id"))


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATOR — Offline-capable (no phone-home)
# ─────────────────────────────────────────────────────────────────────────────

class LicenseValidationResult:
    """Result of license validation with full details."""

    def __init__(
        self,
        mode: LicenseMode,
        reason: str,
        license_id: Optional[str] = None,
        client_name: Optional[str] = None,
        ado_display_name: Optional[str] = None,
        tier: Optional[str] = None,
        expiry_date: Optional[str] = None,
        days_remaining: Optional[int] = None,
    ):
        self.mode = mode
        self.reason = reason
        self.license_id = license_id
        self.client_name = client_name
        self.ado_display_name = ado_display_name
        self.tier = tier
        self.expiry_date = expiry_date
        self.days_remaining = days_remaining

    @property
    def is_operational(self) -> bool:
        """True if ADO can respond to users (FULL or READ_ONLY)."""
        return self.mode in (LicenseMode.FULL, LicenseMode.READ_ONLY, LicenseMode.DEMO)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "reason": self.reason,
            "license_id": self.license_id,
            "client_name": self.client_name,
            "ado_display_name": self.ado_display_name,
            "tier": self.tier,
            "expiry_date": self.expiry_date,
            "days_remaining": self.days_remaining,
            "is_operational": self.is_operational,
        }


def validate_license(
    license_data: dict,
    secret_key: str,
) -> LicenseValidationResult:
    """
    Offline-capable license validation.

    Mirrors Ixonomic's verifyCoinIdentity() — recomputes hash + HMAC without
    contacting any external server.

    Validation steps:
    1. Recompute identity_hash from license fields
    2. Verify HMAC-SHA256 signature (tamper detection)
    3. Check state (REVOKED → INVALID)
    4. Check expiry (with EXPIRY_GRACE_DAYS grace period)
    5. Return LicenseValidationResult

    Args:
        license_data:  Parsed license.json content
        secret_key:    LICENSE_SECRET_KEY (must match key used to mint)

    Returns:
        LicenseValidationResult with mode + details
    """
    # Extract fields
    license_id =    license_data.get("license_id", "")
    client_name =   license_data.get("client_name", "")
    tier =          license_data.get("tier", "")
    issued_date =   license_data.get("issued_date", "")
    expiry_date =   license_data.get("expiry_date", "")
    entropy =       license_data.get("entropy", "")
    stored_hash =   license_data.get("identity_hash", "")
    stored_sig =    license_data.get("signature", "")
    state =         license_data.get("state", "")
    display_name =  license_data.get("ado_display_name", "ADO")

    common_kwargs = dict(
        license_id=license_id,
        client_name=client_name,
        ado_display_name=display_name,
        tier=tier,
        expiry_date=expiry_date,
    )

    # Step 1: Recompute identity hash
    expected_hash = _build_identity_hash(
        license_id=license_id,
        client_name=client_name,
        tier=tier,
        issued_date=issued_date,
        expiry_date=expiry_date,
        entropy=entropy,
    )

    if not hmac.compare_digest(stored_hash, expected_hash):
        logger.error(
            "license.validation.hash_mismatch",
            license_id=license_id,
            reason="identity_hash does not match computed value — tampered",
        )
        return LicenseValidationResult(
            mode=LicenseMode.INVALID,
            reason="identity_hash_tampered",
            **common_kwargs,
        )

    # Step 2: Verify HMAC signature
    expected_sig = _sign(expected_hash, secret_key)
    if not hmac.compare_digest(stored_sig, expected_sig):
        logger.error(
            "license.validation.signature_mismatch",
            license_id=license_id,
            reason="HMAC-SHA256 signature invalid — wrong key or tampered",
        )
        return LicenseValidationResult(
            mode=LicenseMode.INVALID,
            reason="signature_invalid",
            **common_kwargs,
        )

    # Step 3: Check state
    if state == LicenseState.REVOKED.value:
        logger.error("license.validation.revoked", license_id=license_id)
        return LicenseValidationResult(
            mode=LicenseMode.INVALID,
            reason="license_revoked",
            **common_kwargs,
        )

    if state == LicenseState.SUSPENDED.value:
        logger.warning("license.validation.suspended", license_id=license_id)
        return LicenseValidationResult(
            mode=LicenseMode.READ_ONLY,
            reason="license_suspended",
            **common_kwargs,
        )

    # Step 4: Check expiry
    try:
        expiry = datetime.fromisoformat(expiry_date)
        now = datetime.now(timezone.utc)
        # Make expiry timezone-aware if naive
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        days_remaining = (expiry - now).days

        if now > expiry + timedelta(days=EXPIRY_GRACE_DAYS):
            logger.warning(
                "license.validation.expired",
                license_id=license_id,
                expiry=expiry_date,
                days_past=abs(days_remaining),
            )
            return LicenseValidationResult(
                mode=LicenseMode.READ_ONLY,
                reason=f"expired_{abs(days_remaining)}_days_ago",
                days_remaining=days_remaining,
                **common_kwargs,
            )

        if now > expiry:
            # Within grace period
            logger.warning(
                "license.validation.expiring_grace",
                license_id=license_id,
                days_until_read_only=EXPIRY_GRACE_DAYS - abs(days_remaining),
            )
    except (ValueError, TypeError) as exc:
        logger.error("license.validation.expiry_parse_error", error=str(exc))
        return LicenseValidationResult(
            mode=LicenseMode.INVALID,
            reason="expiry_parse_error",
            **common_kwargs,
        )

    # ✅ All checks passed
    logger.info(
        "license.validation.ok",
        license_id=license_id,
        client=client_name,
        display_name=display_name,
        tier=tier,
        days_remaining=days_remaining,
    )
    return LicenseValidationResult(
        mode=LicenseMode.FULL,
        reason="valid",
        days_remaining=days_remaining,
        **common_kwargs,
    )


# ─────────────────────────────────────────────────────────────────────────────
# LICENSE LOADER — Read from disk, validate, return mode
# ─────────────────────────────────────────────────────────────────────────────

def load_and_validate(
    license_path: str,
    secret_key: Optional[str],
    demo_mode_allowed: bool = True,
) -> LicenseValidationResult:
    """
    Load license.json from disk and validate.

    This is what runs at ADO startup (called from main.py lifespan).

    If no license file and demo_mode_allowed=True → DEMO mode
    (limited features, for evaluation/beta instances like app.migancore.com)

    Args:
        license_path:        Path to license.json
        secret_key:          LICENSE_SECRET_KEY env var
        demo_mode_allowed:   Allow running without license (demo/beta instances)
    """
    path = Path(license_path)

    # No license file
    if not path.exists():
        if demo_mode_allowed:
            logger.info(
                "license.demo_mode",
                path=license_path,
                reason="no license file found — running in demo mode",
            )
            return LicenseValidationResult(
                mode=LicenseMode.DEMO,
                reason="no_license_file",
                ado_display_name="Migan",
            )
        else:
            logger.error("license.missing", path=license_path)
            return LicenseValidationResult(
                mode=LicenseMode.INVALID,
                reason="license_file_not_found",
            )

    # No secret key
    if not secret_key:
        logger.warning(
            "license.no_secret_key",
            reason="LICENSE_SECRET_KEY not set — cannot validate signature, running as demo",
        )
        if demo_mode_allowed:
            return LicenseValidationResult(
                mode=LicenseMode.DEMO,
                reason="no_secret_key",
                ado_display_name="Migan",
            )
        return LicenseValidationResult(
            mode=LicenseMode.INVALID,
            reason="no_secret_key",
        )

    # Parse license file
    try:
        with open(path, encoding="utf-8") as f:
            license_data = json.load(f)
    except json.JSONDecodeError as exc:
        logger.error("license.parse_error", error=str(exc))
        return LicenseValidationResult(
            mode=LicenseMode.INVALID,
            reason=f"json_parse_error: {exc}",
        )

    return validate_license(license_data, secret_key)


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL STATE — singleton loaded at startup
# ─────────────────────────────────────────────────────────────────────────────

_current_license: Optional[LicenseValidationResult] = None


def get_current_license() -> Optional[LicenseValidationResult]:
    """Get the license result loaded at startup."""
    return _current_license


def set_current_license(result: LicenseValidationResult) -> None:
    """Called from main.py lifespan to set the validated license."""
    global _current_license
    _current_license = result


def get_ado_display_name() -> str:
    """Return the white-label display name from license, or 'Migan' as fallback."""
    if _current_license and _current_license.ado_display_name:
        return _current_license.ado_display_name
    return "Migan"


def require_full_mode(operation: str = "operation") -> bool:
    """
    Returns True if ADO is in FULL mode (can train, sync, etc).
    Logs a warning for READ_ONLY and DEMO modes.
    Used to gate training-related endpoints.
    """
    if _current_license is None:
        return True  # No license loaded yet (startup) — allow
    if _current_license.mode == LicenseMode.FULL:
        return True
    logger.warning(
        "license.operation_restricted",
        operation=operation,
        mode=_current_license.mode.value,
        reason=_current_license.reason,
    )
    return False
