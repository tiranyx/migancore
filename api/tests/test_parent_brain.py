"""Unit tests for Parent Brain — knowledge accumulation & distribution.

Tests logic without database dependency.
"""

import pytest

from services.parent_brain import SEGMENT_TYPES, _build_segment_name


class TestSegmentTypes:
    def test_all_types_are_strings(self):
        for t in SEGMENT_TYPES:
            assert isinstance(t, str)
            assert len(t) > 0

    def test_skill_type_exists(self):
        assert "skill" in SEGMENT_TYPES

    def test_dpo_pair_type_exists(self):
        assert "dpo_pair" in SEGMENT_TYPES

    def test_tool_pattern_type_exists(self):
        assert "tool_pattern" in SEGMENT_TYPES

    def test_voice_pattern_type_exists(self):
        assert "voice_pattern" in SEGMENT_TYPES

    def test_domain_knowledge_type_exists(self):
        assert "domain_knowledge" in SEGMENT_TYPES


class TestBuildSegmentName:
    def test_uses_name_hint_if_present(self):
        from models.hafidz import HafidzContribution
        contrib = HafidzContribution(
            child_license_id="lic-1",
            child_display_name="Test Child",
            child_tier="PERAK",
            parent_version="v0.3",
            contribution_type="dpo_pair",
            contribution_hash="a" * 64,
            anonymized_payload={"name": "Custom Skill Name"},
        )
        name = _build_segment_name(contrib)
        assert name == "Custom Skill Name"

    def test_fallback_for_dpo_pair(self):
        from models.hafidz import HafidzContribution
        contrib = HafidzContribution(
            child_license_id="lic-1",
            child_display_name="Test Child",
            child_tier="PERAK",
            parent_version="v0.3",
            contribution_type="dpo_pair",
            contribution_hash="a" * 64,
            anonymized_payload={},
        )
        name = _build_segment_name(contrib)
        assert "Training Example" in name
        assert "Test Child" in name

    def test_fallback_for_tool_pattern(self):
        from models.hafidz import HafidzContribution
        contrib = HafidzContribution(
            child_license_id="lic-1",
            child_display_name="Tool Child",
            child_tier="PERAK",
            parent_version="v0.3",
            contribution_type="tool_pattern",
            contribution_hash="b" * 64,
            anonymized_payload={},
        )
        name = _build_segment_name(contrib)
        assert "Tool Usage Pattern" in name
        assert "Tool Child" in name

    def test_unknown_type_fallback(self):
        from models.hafidz import HafidzContribution
        contrib = HafidzContribution(
            child_license_id="lic-1",
            child_display_name="Unknown Child",
            child_tier="PERAK",
            parent_version="v0.3",
            contribution_type="weird_type",
            contribution_hash="c" * 64,
            anonymized_payload={},
        )
        name = _build_segment_name(contrib)
        assert "Knowledge" in name
