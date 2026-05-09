"""Tests for feedback service â€” user thumbs â†’ preference pairs."""

import uuid

import pytest
from sqlalchemy import text

from services.feedback import record_feedback, get_feedback_stats
from deps.db import set_tenant_context
from models.feedback import FeedbackEvent
from models.preference_pair import PreferencePair


async def _create_dummy_message(session, tenant_id: uuid.UUID) -> uuid.UUID:
    """Create a minimal tenant â†’ agent â†’ conversation â†’ message chain for FK validity."""
    from sqlalchemy import select
    from models.agent import Agent
    from models.conversation import Conversation
    from models.message import Message
    from models.tenant import Tenant

    # Set RLS context to the target tenant so inserts pass policy.
    await session.execute(
        text("SELECT set_config('app.current_tenant', :tid, false)"),
        {"tid": str(tenant_id)},
    )

    # Idempotent: only create tenant if it doesn't already exist.
    result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    if result.scalar_one_or_none() is None:
        tenant_slug = f"test-tenant-{uuid.uuid4().hex[:8]}"
        tenant = Tenant(id=tenant_id, name="Test Tenant", slug=tenant_slug)
        session.add(tenant)
        await session.flush()

    agent = Agent(tenant_id=tenant_id, name="Test Agent", slug="test-agent")
    session.add(agent)
    await session.flush()

    conv = Conversation(tenant_id=tenant_id, agent_id=agent.id, title="Test")
    session.add(conv)
    await session.flush()

    msg = Message(
        conversation_id=conv.id,
        tenant_id=tenant_id,
        role="user",
        content="hello",
    )
    session.add(msg)
    await session.flush()

    return msg.id


class TestRecordFeedback:
    async def test_thumbs_up_creates_pair(self, db_session):
        tenant_id = uuid.uuid4()
        msg_id = await _create_dummy_message(db_session, tenant_id)

        result = await record_feedback(
            db_session,
            message_id=msg_id,
            tenant_id=tenant_id,
            signal_type="thumb_up",
            rating="thumbs_up",
            prompt_text="What is AI?",
            target_text="AI is artificial intelligence.",
        )
        await db_session.commit()

        assert result["status"] == "recorded"
        assert result["feedback_id"] is not None
        assert result["pair_id"] is not None

        # Verify FeedbackEvent (caller-managed commit)
        await set_tenant_context(db_session, str(tenant_id))
        event = await db_session.get(FeedbackEvent, result["feedback_id"])
        assert event is not None
        assert event.signal_type == "thumb_up"
        assert event.message_id == msg_id
        assert event.preference_pair_id == result["pair_id"]

        # Verify PreferencePair
        await set_tenant_context(db_session, str(tenant_id))
        pair = await db_session.get(PreferencePair, result["pair_id"])
        assert pair is not None
        assert pair.source_method == "user_thumbs_up"
        assert pair.chosen == "AI is artificial intelligence."
        assert pair.rejected == "__AWAITING_REJECTED__"
        assert pair.judge_score == 1.0

    async def test_thumbs_down_creates_pair(self, db_session):
        tenant_id = uuid.uuid4()
        msg_id = await _create_dummy_message(db_session, tenant_id)

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
        await db_session.commit()

        assert result["status"] == "recorded"

        await set_tenant_context(db_session, str(tenant_id))
        pair = await db_session.get(PreferencePair, result["pair_id"])
        assert pair.source_method == "user_thumbs_down"
        assert pair.chosen == "__AWAITING_CHOSEN__"
        assert pair.rejected == "It's complicated."
        assert pair.judge_score == 0.0

    async def test_unknown_rating_returns_error(self, db_session):
        tenant_id = uuid.uuid4()
        msg_id = await _create_dummy_message(db_session, tenant_id)

        result = await record_feedback(
            db_session,
            message_id=msg_id,
            tenant_id=tenant_id,
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

        # Create 2 thumbs_up, 1 thumbs_down (each needs a real message FK)
        for _ in range(2):
            msg_id = await _create_dummy_message(db_session, tenant_id)
            await record_feedback(
                db_session,
                message_id=msg_id,
                tenant_id=tenant_id,
                signal_type="thumb_up",
                rating="thumbs_up",
                prompt_text="q",
                target_text="a",
            )
            await db_session.commit()
        msg_id = await _create_dummy_message(db_session, tenant_id)
        await record_feedback(
            db_session,
            message_id=msg_id,
            tenant_id=tenant_id,
            signal_type="thumb_down",
            rating="thumbs_down",
            prompt_text="q",
            target_text="a",
        )
        await db_session.commit()

        stats = await get_feedback_stats(db_session, tenant_id)
        assert stats["total"] == 3
        assert stats["thumbs_up"] == 2
        assert stats["thumbs_down"] == 1
