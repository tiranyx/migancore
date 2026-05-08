"""Tests for the ADO License System.

Tests cover: minting, validation, tier constraints, batch operations,
offline validation, expiry handling, and knowledge return config.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

# Import the license module directly (no external deps except stdlib)
from services.license import (
    LicenseTier,
    LicenseState,
    LicenseMode,
    TIER_CONFIG,
    EXPIRY_GRACE_DAYS,
    mint_license,
    batch_mint,
    validate_license,
    load_and_validate,
    _build_identity_hash,
    _sign,
)


class TestLicenseTierConfig:
    """Test tier configuration constants."""

    def test_berlian_has_highest_max_instances(self):
        assert TIER_CONFIG[LicenseTier.BERLIAN]["max_instances"] == 999

    def test_perunggu_has_lowest_max_instances(self):
        assert TIER_CONFIG[LicenseTier.PERUNGGU]["max_instances"] == 1

    def test_berlian_default_duration_is_120_months(self):
        assert TIER_CONFIG[LicenseTier.BERLIAN]["default_months"] == 120

    def test_perak_default_duration_is_1_month(self):
        assert TIER_CONFIG[LicenseTier.PERAK]["default_months"] == 1


class TestIdentityHash:
    """Test cryptographic identity hash generation."""

    def test_build_identity_hash_is_deterministic(self):
        h1 = _build_identity_hash("id1", "client", "PERAK", "2024-01-01", "2024-02-01", "entropy123")
        h2 = _build_identity_hash("id1", "client", "PERAK", "2024-01-01", "2024-02-01", "entropy123")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_build_identity_hash_changes_with_field(self):
        h1 = _build_identity_hash("id1", "client", "PERAK", "2024-01-01", "2024-02-01", "entropy123")
        h2 = _build_identity_hash("id1", "client", "EMAS", "2024-01-01", "2024-02-01", "entropy123")
        assert h1 != h2

    def test_build_identity_hash_changes_with_entropy(self):
        h1 = _build_identity_hash("id1", "client", "PERAK", "2024-01-01", "2024-02-01", "entropy123")
        h2 = _build_identity_hash("id1", "client", "PERAK", "2024-01-01", "2024-02-01", "entropy456")
        assert h1 != h2


class TestSign:
    """Test HMAC-SHA256 signature generation."""

    def test_sign_is_deterministic(self):
        sig1 = _sign("abc123", "secret")
        sig2 = _sign("abc123", "secret")
        assert sig1 == sig2
        assert len(sig1) == 64  # SHA-256 hex

    def test_sign_changes_with_secret(self):
        sig1 = _sign("abc123", "secret1")
        sig2 = _sign("abc123", "secret2")
        assert sig1 != sig2

    def test_sign_changes_with_identity_hash(self):
        sig1 = _sign("abc123", "secret")
        sig2 = _sign("def456", "secret")
        assert sig1 != sig2


class TestMintLicense:
    """Test license minting (creation)."""

    def test_mint_returns_required_fields(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        assert "license_id" in lic
        assert "client_name" in lic
        assert "ado_display_name" in lic
        assert "signature" in lic
        assert "identity_hash" in lic
        assert "entropy" in lic

    def test_mint_generates_valid_uuid(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        # Should be a valid UUID
        uuid.UUID(lic["license_id"])

    def test_mint_sets_correct_tier(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.EMAS,
            language_pack=["id"],
            secret_key=secret_key,
        )
        assert lic["tier"] == "EMAS"
        assert lic["max_instances"] == 50

    def test_mint_sets_expiry_in_future(self, secret_key):
        now = datetime.now(timezone.utc)
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        expiry = datetime.fromisoformat(lic["expiry_date"])
        assert expiry > now

    def test_mint_berlian_expiry_is_10_years(self, secret_key):
        lic = mint_license(
            client_name="Gov Client",
            ado_display_name="GOV",
            tier=LicenseTier.BERLIAN,
            language_pack=["id"],
            secret_key=secret_key,
        )
        issued = datetime.fromisoformat(lic["issued_date"])
        expiry = datetime.fromisoformat(lic["expiry_date"])
        delta = expiry - issued
        # 120 months = 3600 days (approx 9.86 years, not exactly 10)
        assert delta.days >= 3600 - 1  # ~10 years in months

    def test_mint_includes_genealogy(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
            parent_version="v0.3",
            generation=1,
        )
        assert lic["genealogy"]["parent_version"] == "v0.3"
        assert lic["genealogy"]["generation"] == 1
        assert "migancore:v0.3" in lic["genealogy"]["lineage_chain"]

    def test_mint_knowledge_return_default_false(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        assert lic["knowledge_return"]["enabled"] is False

    def test_mint_knowledge_return_opt_in(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
            knowledge_return_enabled=True,
        )
        assert lic["knowledge_return"]["enabled"] is True
        assert "dpo_pair" in lic["knowledge_return"]["opt_in_types"]

    def test_mint_state_is_issued(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        assert lic["state"] == LicenseState.ISSUED.value

    def test_mint_different_calls_produce_different_ids(self, secret_key):
        lic1 = mint_license(
            client_name="A", ado_display_name="A", tier=LicenseTier.PERAK,
            language_pack=["id"], secret_key=secret_key,
        )
        lic2 = mint_license(
            client_name="B", ado_display_name="B", tier=LicenseTier.PERAK,
            language_pack=["id"], secret_key=secret_key,
        )
        assert lic1["license_id"] != lic2["license_id"]


class TestValidateLicense:
    """Test license validation (offline, no phone-home)."""

    def test_valid_license_passes(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        result = validate_license(lic, secret_key)
        assert result.mode == LicenseMode.FULL
        assert result.reason == "valid"
        assert result.is_operational is True

    def test_tampered_hash_fails(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        lic["identity_hash"] = "tampered" * 8
        result = validate_license(lic, secret_key)
        assert result.mode == LicenseMode.INVALID
        assert result.reason == "identity_hash_tampered"

    def test_tampered_signature_fails(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        lic["signature"] = "tampered" * 8
        result = validate_license(lic, secret_key)
        assert result.mode == LicenseMode.INVALID
        assert result.reason == "signature_invalid"

    def test_wrong_secret_key_fails(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        result = validate_license(lic, "wrong-secret-key-32-chars!!!")
        assert result.mode == LicenseMode.INVALID
        assert result.reason == "signature_invalid"

    def test_revoked_license_fails(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        lic["state"] = LicenseState.REVOKED.value
        result = validate_license(lic, secret_key)
        assert result.mode == LicenseMode.INVALID
        assert result.reason == "license_revoked"

    def test_suspended_license_is_read_only(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        lic["state"] = LicenseState.SUSPENDED.value
        result = validate_license(lic, secret_key)
        assert result.mode == LicenseMode.READ_ONLY
        assert result.reason == "license_suspended"

    def test_expired_license_within_grace_period(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        # Set expiry to yesterday, then recompute hash + signature
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        lic["expiry_date"] = yesterday.isoformat()
        lic["identity_hash"] = _build_identity_hash(
            lic["license_id"], lic["client_name"], lic["tier"],
            lic["issued_date"], lic["expiry_date"], lic["entropy"]
        )
        lic["signature"] = _sign(lic["identity_hash"], secret_key)
        result = validate_license(lic, secret_key)
        # Should still be FULL (within grace period)
        assert result.mode == LicenseMode.FULL
        assert "grace" in result.reason or "valid" in result.reason

    def test_expired_license_beyond_grace_period(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        # Set expiry to well past grace period, then recompute hash + signature
        way_back = datetime.now(timezone.utc) - timedelta(days=EXPIRY_GRACE_DAYS + 5)
        lic["expiry_date"] = way_back.isoformat()
        lic["identity_hash"] = _build_identity_hash(
            lic["license_id"], lic["client_name"], lic["tier"],
            lic["issued_date"], lic["expiry_date"], lic["entropy"]
        )
        lic["signature"] = _sign(lic["identity_hash"], secret_key)
        result = validate_license(lic, secret_key)
        assert result.mode == LicenseMode.READ_ONLY
        assert "expired" in result.reason

    def test_valid_license_has_days_remaining(self, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        result = validate_license(lic, secret_key)
        assert result.days_remaining is not None
        assert result.days_remaining > 0


class TestLoadAndValidate:
    """Test loading license from disk and validating."""

    def test_missing_file_demo_mode(self, tmp_path, secret_key):
        missing_path = str(tmp_path / "nonexistent.json")
        result = load_and_validate(missing_path, secret_key, demo_mode_allowed=True)
        assert result.mode == LicenseMode.DEMO

    def test_missing_file_no_demo(self, tmp_path, secret_key):
        missing_path = str(tmp_path / "nonexistent.json")
        result = load_and_validate(missing_path, secret_key, demo_mode_allowed=False)
        assert result.mode == LicenseMode.INVALID

    def test_valid_file(self, tmp_path, secret_key):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key=secret_key,
        )
        path = tmp_path / "license.json"
        path.write_text(json.dumps(lic))
        result = load_and_validate(str(path), secret_key, demo_mode_allowed=True)
        assert result.mode == LicenseMode.FULL

    def test_no_secret_key_fallback_demo(self, tmp_path):
        lic = mint_license(
            client_name="Test Corp",
            ado_display_name="TEST",
            tier=LicenseTier.PERAK,
            language_pack=["id"],
            secret_key="some-key",
        )
        path = tmp_path / "license.json"
        path.write_text(json.dumps(lic))
        result = load_and_validate(str(path), "", demo_mode_allowed=True)
        assert result.mode == LicenseMode.DEMO


class TestBatchMint:
    """Test batch license minting."""

    def test_batch_mint_multiple(self, secret_key):
        clients = [
            {"client_name": "A", "ado_display_name": "ADO-A", "tier": "PERAK", "language_pack": ["id"]},
            {"client_name": "B", "ado_display_name": "ADO-B", "tier": "EMAS", "language_pack": ["id", "en"]},
        ]
        results = batch_mint(clients, secret_key)
        assert len(results) == 2
        assert results[0]["ok"] is True
        assert results[1]["ok"] is True
        assert results[0]["license"]["tier"] == "PERAK"
        assert results[1]["license"]["tier"] == "EMAS"

    def test_batch_mint_different_ids(self, secret_key):
        clients = [
            {"client_name": "A", "ado_display_name": "ADO-A", "tier": "PERAK", "language_pack": ["id"]},
            {"client_name": "B", "ado_display_name": "ADO-B", "tier": "PERAK", "language_pack": ["id"]},
        ]
        results = batch_mint(clients, secret_key)
        id1 = results[0]["license"]["license_id"]
        id2 = results[1]["license"]["license_id"]
        assert id1 != id2

    def test_batch_mint_with_knowledge_return(self, secret_key):
        clients = [
            {"client_name": "A", "ado_display_name": "ADO-A", "tier": "PERAK",
             "language_pack": ["id"], "knowledge_return_enabled": True},
        ]
        results = batch_mint(clients, secret_key)
        assert results[0]["license"]["knowledge_return"]["enabled"] is True

    def test_batch_mint_invalid_tier_skipped(self, secret_key):
        clients = [
            {"client_name": "A", "ado_display_name": "ADO-A", "tier": "INVALID", "language_pack": ["id"]},
        ]
        results = batch_mint(clients, secret_key)
        assert results[0]["ok"] is False


class TestLicenseModeOperational:
    """Test LicenseValidationResult.is_operational property."""

    def test_full_is_operational(self):
        from services.license import LicenseValidationResult
        r = LicenseValidationResult(mode=LicenseMode.FULL, reason="test")
        assert r.is_operational is True

    def test_read_only_is_operational(self):
        from services.license import LicenseValidationResult
        r = LicenseValidationResult(mode=LicenseMode.READ_ONLY, reason="test")
        assert r.is_operational is True

    def test_demo_is_operational(self):
        from services.license import LicenseValidationResult
        r = LicenseValidationResult(mode=LicenseMode.DEMO, reason="test")
        assert r.is_operational is True

    def test_invalid_is_not_operational(self):
        from services.license import LicenseValidationResult
        r = LicenseValidationResult(mode=LicenseMode.INVALID, reason="test")
        assert r.is_operational is False
