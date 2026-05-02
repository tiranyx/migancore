"""
Chat router — MiganCore agent conversation endpoint.

Day 6 MVP: POST /v1/agents/{id}/chat
- Loads agent persona from config/agents.json + SOUL.md
- Queries last N messages from Postgres for context
- Calls Ollama with system prompt + history + user message
- Persists conversation and message to database

Day 7 enhancement: inject conversation history into context.
Day 8 enhancement: wire Letta for working memory blocks.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from deps.auth import get_current_user
from deps.db import get_db, set_tenant_context
from models import User, Agent, Conversation, Message
from services.config_loader import get_agent_config, load_soul_md
from services.ollama import OllamaClient, OllamaError

router = APIRouter(prefix="/v1/agents", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    agent_id: str
    conversation_id: str
    response: str
    model_used: str


# Number of previous messages to include in context window
CONTEXT_WINDOW_MESSAGES = 5
# Max tokens for response
MAX_TOKENS = 1024


@router.post("/{agent_id}/chat", response_model=ChatResponse)
async def chat(
    agent_id: str,
    data: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message to an agent and receive a response.

    Loads the agent's persona from config/agents.json and SOUL.md,
    injects recent conversation history, calls Ollama, and persists
    the exchange to Postgres.
    """
    tenant_id = str(current_user.tenant_id)
    await set_tenant_context(db, tenant_id)

    # Validate agent exists and belongs to tenant
    agent_result = await db.execute(
        select(Agent).where(
            Agent.id == uuid.UUID(agent_id),
            Agent.tenant_id == current_user.tenant_id,
        )
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Load agent configuration
    agent_cfg = get_agent_config(agent_id)
    if agent_cfg:
        soul_text = load_soul_md(agent_cfg.get("soul_md_path"))
        model = agent_cfg.get("model_version", "qwen2.5:7b-instruct-q4_K_M")
    else:
        soul_text = load_soul_md(None)
        model = "qwen2.5:7b-instruct-q4_K_M"

    # Build system prompt from SOUL.md + agent persona
    system_prompt = _build_system_prompt(agent, soul_text, agent_cfg)

    # Get or create conversation
    if data.conversation_id:
        conv_result = await db.execute(
            select(Conversation).where(
                Conversation.id == uuid.UUID(data.conversation_id),
                Conversation.tenant_id == current_user.tenant_id,
                Conversation.agent_id == agent.id,
            )
        )
        conversation = conv_result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
    else:
        conversation = Conversation(
            tenant_id=current_user.tenant_id,
            agent_id=agent.id,
            user_id=current_user.id,
            title=data.message[:50] + "..." if len(data.message) > 50 else data.message,
        )
        db.add(conversation)
        await db.flush()

    # Load recent messages for context
    history = await _load_recent_messages(db, conversation.id, limit=CONTEXT_WINDOW_MESSAGES)

    # Build messages payload for Ollama /api/chat
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": data.message})

    # Persist user message
    user_message = Message(
        conversation_id=conversation.id,
        tenant_id=current_user.tenant_id,
        role="user",
        content=data.message,
    )
    db.add(user_message)

    # Call Ollama
    try:
        async with OllamaClient() as client:
            ollama_resp = await client.chat(
                model=model,
                messages=messages,
                options={"num_predict": MAX_TOKENS},
            )
        assistant_content = ollama_resp.get("message", {}).get("content", "").strip()
        if not assistant_content:
            assistant_content = "[No response from model]"
    except OllamaError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ollama error: {exc}",
        )

    # Persist assistant message
    assistant_message = Message(
        conversation_id=conversation.id,
        tenant_id=current_user.tenant_id,
        role="assistant",
        content=assistant_content,
    )
    db.add(assistant_message)

    # Update conversation metadata
    conversation.message_count = len(history) + 2
    conversation.last_message_at = datetime.now(timezone.utc)

    await db.commit()

    return ChatResponse(
        agent_id=agent_id,
        conversation_id=str(conversation.id),
        response=assistant_content,
        model_used=model,
    )


def _build_system_prompt(agent: Agent, soul_text: str, agent_cfg: dict | None) -> str:
    """Construct the system prompt from SOUL.md + agent configuration.

    This is the personality injection layer — what makes Migan-Core
    feel like Migan-Core instead of a generic Qwen response.
    """
    parts = [soul_text.strip()]

    if agent_cfg:
        persona = agent_cfg.get("persona_overrides", {})
        if persona.get("voice"):
            parts.append(f"\nVoice: {persona['voice']}")
        if persona.get("tone"):
            parts.append(f"Tone: {persona['tone']}")
        if persona.get("values"):
            parts.append(f"Values: {', '.join(persona['values'])}")

    parts.append(f"\nYou are currently operating as: {agent.name}")
    parts.append("Always respond in character. Never break the fourth wall.")

    return "\n".join(parts)


async def _load_recent_messages(db: AsyncSession, conversation_id: uuid.UUID, limit: int = 5):
    """Load the most recent messages for a conversation."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    # Return in chronological order
    return list(reversed(messages))
