"""
Chat router — MiganCore agent conversation endpoints.

Day 6: POST /v1/agents/{id}/chat (basic chat + Postgres persistence)
Day 7: + rate limiting, SSE streaming, memory injection, conversation list
Day 8: + function calling / tool use loop
Day 9: + LangGraph director routing
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from deps.auth import get_current_user
from deps.db import get_db, set_tenant_context
from deps.rate_limit import limiter
from models import User, Agent, Conversation, Message, Tenant
from services.config_loader import get_agent_config, load_soul_md
from services.letta import get_blocks as get_letta_blocks
from services.memory import memory_summary
from services.director import run_director
from services.ollama import OllamaClient, OllamaError
from services.tool_executor import ToolContext, build_ollama_tools_spec
from services.tool_policy import load_tool_policies
from services.vector_memory import index_turn_pair


async def _check_tenant_message_quota(db: AsyncSession, tenant: Tenant) -> None:
    """Check and increment tenant daily message quota.

    Day 11: Enforces tenant.max_messages_per_day.
    Resets counter automatically at UTC midnight.
    """
    now = datetime.now(timezone.utc)
    reset = tenant.messages_day_reset

    # Auto-reset if new day
    if reset is None or reset.date() < now.date():
        tenant.messages_today = 0
        tenant.messages_day_reset = now

    if tenant.messages_today >= tenant.max_messages_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily message limit reached: {tenant.messages_today}/{tenant.max_messages_per_day}. "
                   f"Resets at UTC midnight.",
        )

    tenant.messages_today += 1

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/agents", tags=["chat"])

CONTEXT_WINDOW_MESSAGES = 5
MAX_TOKENS = 1024
MAX_TOOL_ITERATIONS = 5  # Circuit breaker — prevents infinite tool loops


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    agent_id: str
    conversation_id: str
    response: str
    model_used: str
    tool_calls_made: int = 0  # How many tool calls were executed this turn


class ConversationSummary(BaseModel):
    id: str
    title: str | None
    status: str
    message_count: int
    last_message_at: str | None
    started_at: str


# ---------------------------------------------------------------------------
# POST /v1/agents/{agent_id}/chat  — synchronous (blocking) chat
# ---------------------------------------------------------------------------

@router.post("/{agent_id}/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(
    agent_id: str,
    data: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message to an agent and receive a synchronous response.

    Injects: SOUL.md persona + Redis memory summary + conversation history.
    Persists: user + assistant messages to Postgres.
    Rate limited: 30 requests/minute per IP.
    """
    tenant_id = str(current_user.tenant_id)
    await set_tenant_context(db, tenant_id)

    agent = await _get_agent_or_404(db, agent_id, current_user.tenant_id)
    agent_cfg = get_agent_config(agent_id)
    soul_text, model = _load_persona(agent_cfg)
    mem = await memory_summary(tenant_id, agent_id)

    # Day 13: Fetch Letta Tier 3 persona blocks (graceful degradation: {} if unavailable)
    letta_blocks = await get_letta_blocks(agent.letta_agent_id) if agent.letta_agent_id else {}

    system_prompt = _build_system_prompt(agent, soul_text, agent_cfg, mem, letta_blocks)

    conversation, history = await _get_or_create_conversation(
        db, data, agent, current_user
    )

    messages = _build_messages(system_prompt, history, data.message)

    # Build tools spec from agent's declared tools in agents.json
    agent_tools = agent_cfg.get("default_tools", []) if agent_cfg else []

    # Day 11: Load tenant plan + tool policies for safety gates
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one()

    # Day 11: Enforce tenant message quota
    await _check_tenant_message_quota(db, tenant)

    tool_policies = await load_tool_policies(db, tenant_id)

    tool_ctx = ToolContext(
        tenant_id=tenant_id,
        agent_id=agent_id,
        tenant_plan=tenant.plan,
        tool_policies=tool_policies,
    )
    tools_spec = build_ollama_tools_spec(agent_tools)

    # Persist user message before calling Ollama
    user_msg = Message(
        conversation_id=conversation.id,
        tenant_id=current_user.tenant_id,
        role="user",
        content=data.message,
    )
    db.add(user_msg)
    await db.flush()

    # Run LangGraph director (or plain chat if no tools)
    assistant_content, all_tool_calls, reasoning_trace = await run_director(
        model=model,
        messages=messages,
        tools_spec=tools_spec,
        tool_ctx=tool_ctx,
        options={"num_predict": MAX_TOKENS, "temperature": 0},
    )
    logger.info("chat.reasoning_trace", trace=reasoning_trace)

    # Persist assistant message with tool call metadata
    assistant_msg = Message(
        conversation_id=conversation.id,
        tenant_id=current_user.tenant_id,
        role="assistant",
        content=assistant_content,
        tool_calls=all_tool_calls if all_tool_calls else None,
    )
    db.add(assistant_msg)

    conversation.message_count = len(history) + 2
    conversation.last_message_at = datetime.now(timezone.utc)

    await db.commit()

    # Day 12: Background semantic embed — fire-and-forget, never blocks response
    asyncio.create_task(
        index_turn_pair(
            agent_id=agent_id,
            tenant_id=tenant_id,
            user_message=data.message,
            assistant_message=assistant_content,
            session_id=str(conversation.id),
            turn_index=conversation.message_count,
        )
    )

    logger.info(
        "chat.response",
        agent_id=agent_id,
        conversation_id=str(conversation.id),
        response_len=len(assistant_content),
        tool_calls=len(all_tool_calls),
    )

    return ChatResponse(
        agent_id=agent_id,
        conversation_id=str(conversation.id),
        response=assistant_content,
        model_used=model,
        tool_calls_made=len(all_tool_calls),
    )


# ---------------------------------------------------------------------------
# POST /v1/agents/{agent_id}/chat/stream  — SSE streaming chat
# ---------------------------------------------------------------------------

@router.post("/{agent_id}/chat/stream")
@limiter.limit("20/minute")
async def chat_stream(
    agent_id: str,
    data: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Stream agent response via Server-Sent Events.

    SSE event format:
      data: {"type": "start",  "conversation_id": "..."}
      data: {"type": "chunk",  "content": "hello "}
      data: {"type": "chunk",  "content": "world"}
      data: {"type": "done",   "conversation_id": "..."}
      data: {"type": "error",  "message": "..."}

    Pre-flight DB ops (agent validation, conversation create, history load)
    complete BEFORE streaming starts so errors return proper HTTP status codes.
    Assistant message is persisted via asyncio.create_task after stream ends.
    """
    tenant_id = str(current_user.tenant_id)

    # Phase 1: Pre-flight — all DB ops, session closed before streaming
    from models.base import AsyncSessionLocal
    if AsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized",
        )

    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, tenant_id)

        agent = await _get_agent_or_404(db, agent_id, current_user.tenant_id)
        agent_cfg = get_agent_config(agent_id)
        soul_text, model = _load_persona(agent_cfg)
        mem = await memory_summary(tenant_id, agent_id)
        system_prompt = _build_system_prompt(agent, soul_text, agent_cfg, mem)

        conversation, history = await _get_or_create_conversation(
            db, data, agent, current_user
        )
        conversation_id = conversation.id

        # Persist user message immediately (before streaming)
        user_msg = Message(
            conversation_id=conversation_id,
            tenant_id=current_user.tenant_id,
            role="user",
            content=data.message,
        )
        db.add(user_msg)
        await db.commit()
    # DB session closes here — before streaming starts

    messages = _build_messages(
        system_prompt,
        history,  # history loaded before session closed
        data.message,
    )

    # Phase 2: SSE generator
    async def generate():
        yield _sse({"type": "start", "conversation_id": str(conversation_id)})

        full_response: list[str] = []
        try:
            async for chunk, done in OllamaClient().chat_stream(
                model=model,
                messages=messages,
                options={"num_predict": MAX_TOKENS},
            ):
                if chunk:
                    full_response.append(chunk)
                    yield _sse({"type": "chunk", "content": chunk})
                if done:
                    break

            full_text = "".join(full_response)
            yield _sse({"type": "done", "conversation_id": str(conversation_id)})

            # Persist assistant message in background (non-blocking)
            asyncio.create_task(
                _persist_assistant_message(
                    conversation_id=conversation_id,
                    tenant_id=tenant_id,
                    content=full_text,
                    message_count=len(history) + 2,
                )
            )

        except OllamaError as exc:
            logger.error("chat.stream.ollama_error", error=str(exc))
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# GET /v1/agents/{agent_id}/conversations  — list conversations for agent
# ---------------------------------------------------------------------------

@router.get("/{agent_id}/conversations", response_model=list[ConversationSummary])
async def list_agent_conversations(
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
):
    """List conversations for a specific agent, scoped to current user."""
    tenant_id = str(current_user.tenant_id)
    await set_tenant_context(db, tenant_id)

    await _get_agent_or_404(db, agent_id, current_user.tenant_id)

    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.agent_id == uuid.UUID(agent_id),
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
        ConversationSummary(
            id=str(c.id),
            title=c.title,
            status=c.status,
            message_count=c.message_count,
            last_message_at=c.last_message_at.isoformat() if c.last_message_at else None,
            started_at=c.started_at.isoformat(),
        )
        for c in conversations
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_agent_or_404(
    db: AsyncSession,
    agent_id: str,
    tenant_id: uuid.UUID,
) -> Agent:
    result = await db.execute(
        select(Agent).where(
            Agent.id == uuid.UUID(agent_id),
            Agent.tenant_id == tenant_id,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return agent


def _load_persona(agent_cfg: dict | None) -> tuple[str, str]:
    """Return (soul_text, model) from agent config."""
    if agent_cfg:
        return (
            load_soul_md(agent_cfg.get("soul_md_path")),
            agent_cfg.get("model_version", settings.DEFAULT_MODEL),
        )
    return load_soul_md(None), settings.DEFAULT_MODEL


def _build_system_prompt(
    agent: Agent,
    soul_text: str,
    agent_cfg: dict | None,
    memory_summary_text: str,
    letta_blocks: dict | None = None,
) -> str:
    """Construct system prompt: Letta blocks (Tier 3) > SOUL.md (Tier 0) + memory.

    Day 13: If letta_blocks has a 'persona' block, it replaces soul_text as the
    identity foundation — the Letta block is the evolved, persistent version.
    mission and knowledge blocks are injected as additional context sections.
    Falls back to soul_text + overrides if Letta is unavailable.
    """
    blocks = letta_blocks or {}

    # Tier 3: Letta persona block overrides soul_text (it IS the evolved soul)
    if blocks.get("persona"):
        parts = [blocks["persona"]]
    else:
        # Tier 0 fallback: static SOUL.md + agent config overrides
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

    # Inject Letta mission block (active goal context)
    if blocks.get("mission"):
        parts.append(f"\n[MISI AKTIF]\n{blocks['mission']}")

    # Inject Letta knowledge block (learned facts about owner/context)
    knowledge = blocks.get("knowledge", "")
    if knowledge and "Belum ada pengetahuan" not in knowledge:
        parts.append(f"\n[KONTEKS DIKETAHUI]\n{knowledge}")

    # Tier 1: Redis memory summary (recent K-V facts)
    if memory_summary_text:
        parts.append(f"\n{memory_summary_text}")

    return "\n".join(parts)


async def _get_or_create_conversation(
    db: AsyncSession,
    data: ChatRequest,
    agent: Agent,
    current_user: User,
) -> tuple[Conversation, list[Message]]:
    """Get existing conversation or create a new one. Returns (conv, history)."""
    if data.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == uuid.UUID(data.conversation_id),
                Conversation.tenant_id == current_user.tenant_id,
                Conversation.agent_id == agent.id,
            )
        )
        conversation = result.scalar_one_or_none()
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

    history = await _load_recent_messages(
        db, conversation.id, limit=CONTEXT_WINDOW_MESSAGES
    )
    return conversation, history


async def _load_recent_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    limit: int = 5,
) -> list[Message]:
    """Load last N messages in chronological order."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    return list(reversed(messages))


def _build_messages(
    system_prompt: str,
    history: list[Message],
    user_message: str,
) -> list[dict]:
    """Build Ollama messages list from system prompt + history + new message."""
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})
    return messages


async def _persist_assistant_message(
    conversation_id: uuid.UUID,
    tenant_id: str,
    content: str,
    message_count: int,
) -> None:
    """Persist assistant message after SSE streaming completes.

    Runs as asyncio.create_task — failures are logged but not raised.
    """
    if AsyncSessionLocal is None:
        return
    try:
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tenant_id)

            assistant_msg = Message(
                conversation_id=conversation_id,
                tenant_id=uuid.UUID(tenant_id),
                role="assistant",
                content=content,
            )
            db.add(assistant_msg)

            await db.execute(
                text(
                    "UPDATE conversations SET message_count = :mc, last_message_at = NOW() "
                    "WHERE id = :conv_id"
                ),
                {"mc": message_count, "conv_id": conversation_id},
            )
            await db.commit()
    except Exception as exc:
        logger.error("chat.persist_assistant.failed", error=str(exc), conversation_id=str(conversation_id))


def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
