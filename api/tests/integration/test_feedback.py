"""Tests for feedback service — user thumbs → preference pairs."""

import uuid

import pytest

from services.feedback import record_feedback, get_feedback_stats
from models.feedback import FeedbackEvent
from models.preference_pair import PreferencePair


class TestRecordFeedback:
    async def test_thumbs_up_creates_pair(self, db_session):
        msg_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        result = await record_feedback(
            db_session,
            message_id=msg_id,
            tenant_id=tenant_id,
            signal_type="thumb_up",
            rating="thumbs_up",
            prompt_text="What is AI?",
            target_text="AI is artificial intelligence.",
        )

        assert result["status"] == "recorded"
        assert result["feedback_id"] is not None
        assert result["pair_id"] is not None

        # Verify FeedbackEvent
        event = await db_session.get(FeedbackEvent, result["feedback_id"])
        assert event is not None
        assert event.signal_type == "thumb_up"
        assert event.message_id == msg_id
        assert event.preference_pair_id == result["pair_id"]

        # Verify PreferencePair
        pair = await db_session.get(PreferencePair, result["pair_id"])
        assert pair is not None
        assert pair.source_method == "user_thumbs_up"
        assert pair.chosen == "AI is artificial intelligence."
        assert pair.rejected == "__AWAITING_REJECTED__"
        assert pair.judge_score == 1.0

    async def test_thumbs_down_creates_pair(self, db_session):
        msg_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        result = await record_feedback(
            db_session,
            message_id=msg_id,
            tenant_id=tenant_id,
            signal_type="thumb_down",
            rating="thumbs_down",
            comment="Too vague",
            prompt_text="Explain quantum",
            target_text="It's complicated.",
        )

        assert result["status"] == "recorded"

        pair = await db_session.get(PreferencePair, result["pair_id"])
        assert pair.source_method == "user_thumbs_down"
        assert pair.chosen == "__AWAITING_CHOSEN__"
        assert pair.rejected == "It's complicated."
        assert pair.judge_score == 0.0

    async def test_unknown_rating_returns_error(self, db_session):
        result = await record_feedback(
            db_session,
            message_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            signal_type="weird",
            rating="weird",
            prompt_text="",
            target_text="",
        )
        assert result["status"] == "unknown_rating"
        assert result["pair_id"] is None


class TestFeedbackStats:
    async def test_stats_count_correctly(self, db_session):
        tenant_id = uuid.uuid4()

        # Create 2 thumbs_up, 1 thumbs_down
        for _ in range(2):
            await record_feedback(
                db_session,
                message_id=uuid.uuid4(),
                tenant_id=tenant_id,
                signal_type="thumb_up",
                rating="thumbs_up",
                prompt_text="q",
                target_text="a",
            )
        await record_feedback(
            db_session,
            message_id=uuid.uuid4(),
            tenant_id=tenant_id,
            signal_type="thumb_down",
            rating="thumbs_down",
            prompt_text="q",
            target_text="a",
        )

        stats = await get_feedback_stats(db_session, tenant_id)
        assert stats["total"] == 3
        assert stats["thumbs_up"] == 2
        assert stats["thumbs_down"] == 1
