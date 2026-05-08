"""Unit tests for Hafidz Ledger — Child Mortality Protocol.

Tests logic without database dependency.
"""

import pytest

from services.hafidz_mortality import DEATH_REASONS


class TestDeathReasons:
    def test_all_reasons_have_human_description(self):
        for key, desc in DEATH_REASONS.items():
            assert isinstance(key, str)
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_license_expired_reason_exists(self):
        assert "license_expired" in DEATH_REASONS

    def test_license_revoked_reason_exists(self):
        assert "license_revoked" in DEATH_REASONS

    def test_instance_destroyed_reason_exists(self):
        assert "instance_destroyed" in DEATH_REASONS

    def test_instance_crashed_reason_exists(self):
        assert "instance_crashed" in DEATH_REASONS

    def test_knowledge_harvested_reason_exists(self):
        assert "knowledge_harvested" in DEATH_REASONS


class TestCloneRequestPhilosophy:
    """Verify CloneRequest schema encodes ADO standing-alone philosophy."""

    def test_name_is_white_label(self):
        from schemas.clone import CloneRequest
        # name field description should mention white-label
        assert "white-label" in CloneRequest.model_fields["name"].description.lower()

    def test_license_fields_immutable(self):
        from schemas.clone import CloneRequest
        # tier description should mention immutable
        assert "immutable" in CloneRequest.model_fields["tier"].description.lower()

    def test_mortality_tracking_default_true(self):
        from schemas.clone import CloneRequest
        req = CloneRequest(
            name="SARI",
            client_name="PT Sari Husada",
            tier="PERAK",
        )
        assert req.mortality_tracking is True
