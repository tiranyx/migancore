"""Integration tests for Hafidz Ledger endpoints.

Requires: PostgreSQL running at TEST_DATABASE_URL (default: localhost:5432)
Skipped automatically if DB is unreachable.
"""

import os
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


def _db_reachable() -> bool:
    """Check if test database is reachable."""
    import asyncio

    from sqlalchemy.ext.asyncio import create_async_engine

    url = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://ado:test@localhost:5432/ado_test")
    engine = create_async_engine(url)

    async def check():
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
        finally:
            await engine.dispose()

    return asyncio.run(check())


@pytest.mark.skipif(not _db_reachable(), reason="Test PostgreSQL not reachable")
class TestHafidzIntegration:
    """Full CRUD flow for Hafidz contributions against real DB."""

    async def test_create_contribution(self, db_session):
        """Insert a contribution and verify it exists."""
        from models.hafidz import HafidzContribution

        contrib = HafidzContribution(
            child_license_id="lic-test-001",
            child_display_name="Test Child",
            child_tier="PERAK",
            parent_version="v0.3",
            contribution_type="dpo_pair",
            contribution_hash="a" * 64,
            anonymized_payload={"question": "test", "answer": "ok"},
        )
        db_session.add(contrib)
        await db_session.flush()

        assert contrib.id is not None
        assert contrib.status == "pending"
        assert contrib.received_at is not None

    async def test_contribution_hash_uniqueness(self, db_session):
        """Duplicate hash should raise IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        from models.hafidz import HafidzContribution

        hash_val = "b" * 64

        c1 = HafidzContribution(
            child_license_id="lic-1",
            child_display_name="Child 1",
            child_tier="PERAK",
            parent_version="v0.3",
            contribution_type="tool_pattern",
            contribution_hash=hash_val,
            anonymized_payload={},
        )
        db_session.add(c1)
        await db_session.flush()

        c2 = HafidzContribution(
            child_license_id="lic-2",
            child_display_name="Child 2",
            child_tier="EMAS",
            parent_version="v0.3",
            contribution_type="domain_cluster",
            contribution_hash=hash_val,
            anonymized_payload={},
        )
        db_session.add(c2)

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_review_contribution(self, db_session):
        """Update status via review flow."""
        from models.hafidz import HafidzContribution

        contrib = HafidzContribution(
            child_license_id="lic-review",
            child_display_name="Review Child",
            child_tier="BERLIAN",
            parent_version="v0.3",
            contribution_type="voice_pattern",
            contribution_hash="c" * 64,
            anonymized_payload={},
        )
        db_session.add(contrib)
        await db_session.flush()

        contrib.status = "incorporated"
        contrib.quality_score = 0.92
        contrib.incorporated_cycle = 7
        contrib.incorporated_at = datetime.now(timezone.utc)
        await db_session.flush()

        # Re-query to verify persistence
        result = await db_session.get(HafidzContribution, contrib.id)
        assert result.status == "incorporated"
        assert result.quality_score == pytest.approx(0.92)
        assert result.incorporated_cycle == 7
