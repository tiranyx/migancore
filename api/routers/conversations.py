"""
Conversation management router.

Endpoints for listing and managing conversations across all agents
for the current authenticated user.

Day 7 MVP: list, get (with messages), soft delete.
Day 8+: search, export, feedback signals.
"""

import uuid
from typing import Literal

import structlog

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from deps.auth import get_current_user
from deps.db import get_db, set_tenant_context
from models import User, Conversation, Message, PreferencePair, FeedbackEvent

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])

logger = structlog.get_logger()


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ConversationDetail(BaseModel):
    id: str
    agent_id: str
    title: str | None
    status: str
    message_count: int
    started_at: str
    last_message_at: str | None
    messages: list[MessageOut]


class ConversationListItem(BaseModel):
    id: str
    agent_id: str
    title: str | None
    status: str
    message_count: int
    started_at: str
    last_message_at: str | None


# ---------------------------------------------------------------------------
# GET /v1/conversations â€” list all user conversations
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ConversationListItem])
async def list_conversations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
):
    """List all active conversations for the current user across all agents."""
    await set_tenant_context(db, str(current_user.tenant_id))

    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.tenant_id == current_user.tenant_id,
            Conversation.user_id == current_user.id,
            Conversation.status != "archived",
        )
        .order_by(Conversation.last_message_at.desc().nullslast())
        .limit(limit)
        .offset(offset)
    )
    conversations = result.scalars().all()

    return [
        ConversationListItem(
            id=str(c.id),
            agent_id=str(c.agent_id),
            title=c.title,
            status=c.status,
            message_count=c.message_count,
            started_at=c.started_at.isoformat(),
            last_message_at=c.last_message_at.isoformat() if c.last_message_at else None,
        )
        for c in conversations
    ]


# ---------------------------------------------------------------------------
# GET /v1/conversations/{id} â€” get conversation with messages
# ---------------------------------------------------------------------------

@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    message_limit: int = 50,
):
    """Get a conversation with its full message history."""
    await set_tenant_context(db, str(current_user.tenant_id))

    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == uuid.UUID(conversation_id),
            Conversation.tenant_id == current_user.tenant_id,
            Conversation.user_id == current_user.id,
            Conversation.status != "archived",
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .limit(message_limit)
    )
    messages = msg_result.scalars().all()

    return ConversationDetail(
        id=str(conversation.id),
        agent_id=str(conversation.agent_id),
        title=conversation.title,
        status=conversation.status,
        message_count=conversation.message_count,
        started_at=conversation.started_at.isoformat(),
        last_message_at=conversation.last_message_at.isoformat() if conversation.last_message_at else None,
        messages=[
            MessageOut(
                id=str(m.id),
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
    )


# ---------------------------------------------------------------------------
# DELETE /v1/conversations/{id} â€” soft delete (archive)
# ---------------------------------------------------------------------------

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete a conversation (sets status to 'archived')."""
    await set_tenant_context(db, str(current_user.tenant_id))

    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == uuid.UUID(conversation_id),
            Conversation.tenant_id == current_user.tenant_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    conversation.status = "archived"
    await db.commit()


# ---------------------------------------------------------------------------
# POST /v1/conversations/{id}/messages/{msg_id}/feedback â€” user feedback signal
# Day 65: User thumbs_up/thumbs_down â†’ stored as preference pair for training flywheel.
# ---------------------------------------------------------------------------

class FeedbackIn(BaseModel):
    rating: Literal["thumbs_up", "thumbs_down"]
    comment: str | None = None  # Optional free-text note from user


class FeedbackOut(BaseModel):
    ok: bool
    pair_id: str | None = None
    message: str


@router.post(
    "/{conversation_id}/messages/{message_id}/feedback",
    response_model=FeedbackOut,
    status_code=status.HTTP_200_OK,
)
async def submit_message_feedback(
    conversation_id: str,
    message_id: str,
    body: FeedbackIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit thumbs_up or thumbs_down feedback on an assistant message.

    thumbs_down: stores a (prompt, rejected, chosen=PENDING) preference pair.
        The synthetic pipeline will later generate a better 'chosen' response
        using a teacher API (Gemini) to complete the DPO pair.

    thumbs_up: stores a positive signal. Used for validation sampling;
        does not create a preference pair immediately (no rejected available).

    Day 65 implementation: minimal flywheel â€” store signal, refine offline.
    """
    await set_tenant_context(db, str(current_user.tenant_id))

    # 1. Verify the conversation belongs to this user
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == uuid.UUID(conversation_id),
            Conversation.tenant_id == current_user.tenant_id,
            Conversation.user_id == current_user.id,
            Conversation.status != "archived",
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    # 2. Fetch the target message (must be assistant role)
    msg_result = await db.execute(
        select(Message).where(
            Message.id == uuid.UUID(message_id),
            Message.conversation_id == conversation.id,
        )
    )
    target_msg = msg_result.scalar_one_or_none()
    if not target_msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if target_msg.role != "assistant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback is only accepted on assistant messages",
        )

    # Find the preceding user message as the prompt (used for both thumbs_up and thumbs_down)
    prev_msgs_result = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.created_at < target_msg.created_at,
            Message.role == "user",
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    prev_user_msg = prev_msgs_result.scalar_one_or_none()
    prompt_text = prev_user_msg.content if prev_user_msg else "[context unavailable]"

    from services.feedback import record_feedback

    result = await record_feedback(
        db,
        message_id=target_msg.id,
        tenant_id=current_user.tenant_id,
        signal_type="thumb_up" if body.rating == "thumbs_up" else "thumb_down",
        rating=body.rating,
        comment=body.comment,
        prompt_text=prompt_text,
        target_text=target_msg.content,
    )

    # Caller-managed transaction: commit the feedback + pair insert
    await db.commit()

    logger.info(
        "feedback.submitted",
        rating=body.rating,
        message_id=str(target_msg.id),
        conversation_id=conversation_id,
        tenant_id=str(current_user.tenant_id),
        pair_id=str(result["pair_id"]) if result.get("pair_id") else None,
    )

    return FeedbackOut(
        ok=True,
        pair_id=str(result["pair_id"]) if result["pair_id"] else None,
        message="Feedback recorded. Thank you!" if body.rating == "thumbs_up" else "Feedback stored. We'll use this to improve.",
    )


# ---------------------------------------------------------------------------
# GET /v1/conversations/feedback/stats â€” tenant feedback overview
# ---------------------------------------------------------------------------

class FeedbackStatsOut(BaseModel):
    total: int
    thumbs_up: int
    thumbs_down: int
    awaiting_processing: int
    awaiting_chosen: int      # thumb_down pairs waiting for teacher
    awaiting_rejected: int    # thumb_up pairs waiting for synthetic
    completed_pairs: int      # pairs ready for training
    kto_signals_this_week: int


@router.get("/feedback/stats", response_model=FeedbackStatsOut)
async def feedback_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return feedback statistics for the current tenant."""
    from sqlalchemy import func
    from services.feedback import get_feedback_stats

    base_stats = await get_feedback_stats(db, current_user.tenant_id)

    # Count awaiting/completed pairs
    awaiting_chosen = await db.scalar(
        select(func.count()).where(
            PreferencePair.chosen.like("__AWAITING_CHOSEN__%"),
        )
    )
    awaiting_rejected = await db.scalar(
        select(func.count()).where(
            PreferencePair.rejected.like("__AWAITING_REJECTED__%"),
        )
    )
    total_pairs = await db.scalar(select(func.count()).select_from(PreferencePair))
    completed_pairs = (total_pairs or 0) - (awaiting_chosen or 0) - (awaiting_rejected or 0)

    # KTO signals this week (user feedback events)
    from datetime import datetime, timezone, timedelta
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    kto_signals = await db.scalar(
        select(func.count()).where(
            FeedbackEvent.tenant_id == current_user.tenant_id,
            FeedbackEvent.source == "user",
            FeedbackEvent.created_at >= week_ago,
        )
    )

    return FeedbackStatsOut(
        total=base_stats["total"],
        thumbs_up=base_stats["thumbs_up"],
        thumbs_down=base_stats["thumbs_down"],
        awaiting_processing=base_stats["awaiting_processing"],
        awaiting_chosen=awaiting_chosen or 0,
        awaiting_rejected=awaiting_rejected or 0,
        completed_pairs=max(0, completed_pairs),
        kto_signals_this_week=kto_signals or 0,
    )
