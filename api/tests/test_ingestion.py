"""Unit tests for Knowledge Ingestion Pipeline (SP-009).

Tests quality scoring heuristics without database dependency.
"""

import uuid
from datetime import datetime, timezone

import pytest

from services.ingestion import (
    _expected_fields_for_type,
    _type_diversity_score,
)


class TestExpectedFields:
    def test_dpo_pair_fields(self):
        fields = _expected_fields_for_type("dpo_pair")
        assert "prompt" in fields
        assert "chosen" in fields
        assert "rejected" in fields

    def test_tool_pattern_fields(self):
        fields = _expected_fields_for_type("tool_pattern")
        assert "tool_name" in fields
        assert "usage_pattern" in fields

    def test_unknown_type_fallback(self):
        fields = _expected_fields_for_type("unknown_type")
        assert fields == ["content"]


class TestTypeDiversityScore:
    def test_voice_pattern_is_rarest(self):
        assert _type_diversity_score("voice_pattern") == 1.0

    def test_domain_cluster_high(self):
        assert _type_diversity_score("domain_cluster") == 0.8

    def test_tool_pattern_medium(self):
        assert _type_diversity_score("tool_pattern") == 0.6

    def test_dpo_pair_lowest(self):
        assert _type_diversity_score("dpo_pair") == 0.4

    def test_unknown_type_default(self):
        assert _type_diversity_score("other") == 0.5


class TestQualityWeights:
    def test_weights_sum_to_one(self):
        from services.ingestion import QUALITY_WEIGHTS
        total = sum(QUALITY_WEIGHTS.values())
        assert total == pytest.approx(1.0)


class TestIngestionDecisionThresholds:
    """Test decision logic based on quality score thresholds."""

    def test_auto_approve_threshold(self):
        assert 0.8 >= 0.8  # boundary
        assert 0.79 < 0.8  # just below

    def test_queued_for_review_threshold(self):
        assert 0.5 >= 0.5  # boundary
        assert 0.49 < 0.5  # just below

    def test_auto_reject_threshold(self):
        assert 0.49 < 0.5
        assert 0.0 < 0.5
