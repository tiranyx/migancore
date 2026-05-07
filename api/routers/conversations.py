"""
Conversation management router.

Endpoints for listing and managing conversations across all agents
for the current authenticated user.

Day 7 MVP: list, get (with messages), soft delete.
Day 8+: search, export, feedback signals.
"""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from deps.auth import get_current_user
from deps.db import get_db, set_tenant_context
from models import User, Conversation, Message, PreferencePair

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


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
# GET /v1/conversations — list all user conversations
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
# GET /v1/conversations/{id} — get conversation with messages
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
# DELETE /v1/conversations/{id} — soft delete (archive)
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
# POST /v1/conversations/{id}/messages/{msg_id}/feedback — user feedback signal
# Day 65: User thumbs_up/thumbs_down → stored as preference pair for training flywheel.
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

    Day 65 implementation: minimal flywheel — store signal, refine offline.
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

    if body.rating == "thumbs_up":
        # Positive signal: record but don't create a full preference pair yet
        # (no rejected counterpart available; use for future positive sampling)
        return FeedbackOut(
            ok=True,
            pair_id=None,
            message="Positive feedback recorded. Thank you!",
        )

    # thumbs_down: find the preceding user message as the prompt
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

    # Build rejected text (optionally include user comment as annotation)
    rejected_text = target_msg.content
    if body.comment:
        rejected_text = f"{rejected_text}\n\n[User note: {body.comment}]"

    # Create preference pair: chosen=PENDING (will be filled by teacher API offline)
    pair = PreferencePair(
        prompt=prompt_text,
        chosen="PENDING — awaiting teacher API refinement",
        rejected=rejected_text,
        judge_score=0.0,
        judge_model="user_signal",
        source_method="user_thumbs_down",
        source_message_id=target_msg.id,
    )
    db.add(pair)
    await db.commit()
    await db.refresh(pair)

    return FeedbackOut(
        ok=True,
        pair_id=str(pair.id),
        message="Feedback stored. We'll use this to improve the next training cycle.",
    )
