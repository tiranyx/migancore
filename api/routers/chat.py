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

# Strong references to keep background tasks alive until completion.
# asyncio.create_task() returns a weak-ref — tasks without a live reference
# can be GC'd mid-execution (raises GeneratorExit, closes httpx connections).
_background_tasks: set[asyncio.Task] = set()

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
from services.cai_pipeline import run_cai_pipeline
from services.fact_extractor import maybe_update_knowledge_block
from services.vector_memory import index_turn_pair
from services.vector_retrieval import retrieve_episodic_context, format_episodic_context


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

# Context window management (Day 20)
MAX_HISTORY_LOAD = 10          # Messages fetched from DB (trimmed further below)
MAX_HISTORY_TOKENS = 1500      # Token budget for history passed to Ollama
MAX_MSG_CONTENT_CHARS = 800    # Per-message content cap — prevents tool outputs flooding context
CHARS_PER_TOKEN = 3.5          # Estimate: Bahasa Indonesia + English mixed content
NUM_CTX = 4096                 # Explicit Ollama context window — do NOT rely on Ollama default (2048)
MAX_TOKENS = 1024              # num_predict: max response length tokens
MAX_TOOL_ITERATIONS = 5        # Circuit breaker — prevents infinite tool loops


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

    # Day 16: Retrieve semantically relevant past turns from Qdrant episodic memory.
    # Synchronous (needed before prompt build), timeout-guarded (1.5s → [] on failure).
    # Returns [] on first chat (collection empty) or Qdrant unavailable — safe default.
    episodic_results = await retrieve_episodic_context(agent_id=agent_id, query=data.message)
    episodic_context = format_episodic_context(episodic_results)

    system_prompt = _build_system_prompt(agent, soul_text, agent_cfg, mem, letta_blocks, episodic_context)

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
        options={"num_predict": MAX_TOKENS, "temperature": 0, "num_ctx": NUM_CTX},
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

    # Day 12: Background semantic embed — store ref to prevent GC mid-execution
    _t = asyncio.create_task(
        index_turn_pair(
            agent_id=agent_id,
            tenant_id=tenant_id,
            user_message=data.message,
            assistant_message=assistant_content,
            session_id=str(conversation.id),
            turn_index=conversation.message_count,
        )
    )
    _background_tasks.add(_t)
    _t.add_done_callback(_background_tasks.discard)

    # Day 14: Background knowledge extraction — updates Letta knowledge block with new facts
    if agent.letta_agent_id:
        _t = asyncio.create_task(
            maybe_update_knowledge_block(
                letta_agent_id=agent.letta_agent_id,
                user_message=data.message,
                assistant_response=assistant_content,
                letta_blocks=letta_blocks,
            )
        )
        _background_tasks.add(_t)
        _t.add_done_callback(_background_tasks.discard)

    # Day 15: Background CAI critique-revise — generates preference pairs for DPO training
    _t = asyncio.create_task(
        run_cai_pipeline(
            user_message=data.message,
            assistant_response=assistant_content,
            source_message_id=assistant_msg.id,
        )
    )
    _background_tasks.add(_t)
    _t.add_done_callback(_background_tasks.discard)

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

    # Phase 2: SSE generator with heartbeat (Day 25)
    # Heartbeat prevents nginx/Cloudflare from closing connection during long
    # Ollama processing periods (CPU-only inference can take 30-60s on 7B model).
    # Pattern: race each iterator.__anext__() against 15s timeout — on timeout,
    # emit a ping event (frontend ignores it) and continue waiting for real chunk.
    HEARTBEAT_INTERVAL = 15.0

    async def generate():
        yield _sse({"type": "start", "conversation_id": str(conversation_id)})

        full_response: list[str] = []
        stream_iter = OllamaClient().chat_stream(
            model=model,
            messages=messages,
            options={"num_predict": MAX_TOKENS, "num_ctx": NUM_CTX},
        ).__aiter__()

        chunk_count = 0
        try:
            while True:
                try:
                    chunk, done = await asyncio.wait_for(
                        stream_iter.__anext__(),
                        timeout=HEARTBEAT_INTERVAL,
                    )
                except asyncio.TimeoutError:
                    # 15s of Ollama silence — keep connection alive
                    yield _sse({"type": "ping"})
                    continue
                except StopAsyncIteration:
                    break

                if chunk:
                    full_response.append(chunk)
                    chunk_count += 1
                    yield _sse({"type": "chunk", "content": chunk})
                if done:
                    break

            full_text = "".join(full_response)
            yield _sse({"type": "done", "conversation_id": str(conversation_id)})
            logger.info("chat.stream.done", chunks=chunk_count, len=len(full_text))

            # Persist assistant message in background — store ref to prevent GC
            _t = asyncio.create_task(
                _persist_assistant_message(
                    conversation_id=conversation_id,
                    tenant_id=tenant_id,
                    content=full_text,
                    message_count=len(history) + 2,
                )
            )
            _background_tasks.add(_t)
            _t.add_done_callback(_background_tasks.discard)

        except asyncio.CancelledError:
            # Day 36: client disconnected (Stop button or browser close)
            # The httpx context manager in OllamaClient.chat_stream will close
            # the underlying connection to Ollama, which signals it to abort generation.
            logger.info("chat.stream.cancelled_by_client", chunks_so_far=chunk_count)
            # Persist what we have so user doesn't lose work
            if full_response:
                full_text = "".join(full_response)
                _t = asyncio.create_task(
                    _persist_assistant_message(
                        conversation_id=conversation_id,
                        tenant_id=tenant_id,
                        content=full_text + "\n\n[stopped by user]",
                        message_count=len(history) + 2,
                    )
                )
                _background_tasks.add(_t)
                _t.add_done_callback(_background_tasks.discard)
            raise  # propagate so framework handles cleanup
        except OllamaError as exc:
            logger.error("chat.stream.ollama_error", error=str(exc))
            yield _sse({"type": "error", "message": str(exc)})
        except Exception as exc:
            logger.error("chat.stream.unexpected", error=str(exc), exc_info=True)
            yield _sse({"type": "error", "message": f"Stream error: {exc}"})

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
    episodic_context: str = "",
) -> str:
    """Construct system prompt: Letta blocks (Tier 3) > SOUL.md (Tier 0) + memory.

    Day 13: If letta_blocks has a 'persona' block, it replaces soul_text as the
    identity foundation — the Letta block is the evolved, persistent version.
    mission and knowledge blocks are injected as additional context sections.
    Falls back to soul_text + overrides if Letta is unavailable.

    Day 16: episodic_context (Qdrant semantic retrieval) injected LAST — closest
    to the user message = highest attention weight for 7B models. Sorted by
    relevance (not recency) to exploit primacy attention bias.

    System prompt injection order:
      1. Persona (Letta Tier 3 or SOUL.md Tier 0)
      2. Mission (Letta)
      3. Knowledge (Letta, learned facts)
      4. Memory summary (Redis Tier 1, K-V facts)
      5. Episodic context (Qdrant Tier 2, semantically relevant past turns) ← Day 16
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

    # Tool usage mandate — injected early so it overrides persona resistance.
    # Without this, 7B models often describe actions instead of calling tools.
    # Day 25: more explicit intent-mapping to overcome qwen2.5-7B bias toward
    # python pseudocode for create/save/generate verbs.
    parts.append(
        "\n[TOOL USAGE — MANDATORY]\n"
        "You have access to tools (function calls). When the user's request matches a tool's "
        "capability, you MUST invoke the tool via function-calling — NEVER write code that "
        "appears to call a tool, NEVER describe what the tool would do, NEVER instruct the user "
        "to perform the action manually.\n"
        "\n"
        "Intent → Tool mapping (use when matched):\n"
        "  - create/write/save/generate a FILE → write_file\n"
        "  - read/open/view/show/check FILE content → read_file\n"
        "  - generate/create/make an IMAGE/picture/visual → generate_image\n"
        "  - search the web / look up current info → web_search\n"
        "  - remember/save a fact → memory_write\n"
        "  - recall/find past facts → memory_search\n"
        "  - run/execute Python code (computation only) → python_repl\n"
        "\n"
        "If a tool call fails (policy block, error), report the failure briefly and offer a "
        "plain-text alternative. Do NOT silently fall back to describing the action."
    )

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

    # Day 16: Tier 2 Qdrant episodic context — injected LAST for maximum attention
    # Empty string = no-op (first chat, Qdrant unavailable, or no relevant turns found)
    if episodic_context:
        parts.append(f"\n{episodic_context}")

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
        db, conversation.id, limit=MAX_HISTORY_LOAD
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


def _estimate_tokens(text: str) -> int:
    """Estimate token count for mixed Bahasa Indonesia + English text.

    Uses char/token ratio of 3.5 — conservative estimate that works for
    Bahasa Indonesia (denser than English) + English mixed content.
    Actual token count may vary ±20% but is good enough for budget trimming.
    """
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def _trim_history_to_budget(history_dicts: list[dict]) -> list[dict]:
    """Trim message history to fit within MAX_HISTORY_TOKENS budget.

    Day 20: Two-pass trimming strategy:
      Pass 1 — Per-message cap: truncate content > MAX_MSG_CONTENT_CHARS.
               Prevents tool outputs (3000+ chars) from monopolizing context.
               Appends "…[disingkat]" so model knows content was cut.
      Pass 2 — Token budget: drop oldest messages until total ≤ MAX_HISTORY_TOKENS.
               Always drops from oldest end — preserves most recent context.

    Returns trimmed list (may be shorter than input).
    Logs when trimming occurs for context calibration.
    """
    # Pass 1: Per-message content cap
    capped = []
    for msg in history_dicts:
        content = msg["content"]
        if len(content) > MAX_MSG_CONTENT_CHARS:
            content = content[:MAX_MSG_CONTENT_CHARS] + "…[disingkat]"
        capped.append({**msg, "content": content})

    # Pass 2: Token budget — drop oldest until under budget
    total_tokens = sum(_estimate_tokens(m["content"]) for m in capped)
    original_count = len(capped)

    while capped and total_tokens > MAX_HISTORY_TOKENS:
        removed = capped.pop(0)
        total_tokens -= _estimate_tokens(removed["content"])

    dropped = original_count - len(capped)
    if dropped > 0:
        logger.info(
            "chat.history_trimmed",
            original=original_count,
            kept=len(capped),
            dropped=dropped,
            estimated_tokens=total_tokens,
        )

    return capped


def _build_messages(
    system_prompt: str,
    history: list[Message],
    user_message: str,
) -> list[dict]:
    """Build Ollama messages list from system prompt + history + new message.

    Day 20: Applies token-budget trimming before building message list.
    Each history message is capped at MAX_MSG_CONTENT_CHARS, then oldest
    messages are dropped until total history ≤ MAX_HISTORY_TOKENS.
    This prevents context overflow on Ollama (NUM_CTX=4096).
    """
    history_dicts = [{"role": msg.role, "content": msg.content} for msg in history]
    trimmed = _trim_history_to_budget(history_dicts)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(trimmed)
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

    Day 38 bug fix: AsyncSessionLocal was previously only imported inside
    the stream handler (line 293 local scope), causing NameError here when
    the background task tried to reference it. Side-effect: ALL assistant
    messages from streaming chats since Day 36 silently failed to persist,
    breaking conversation continuity (every "follow-up" chat started cold
    because history loader saw user messages but no AI replies).
    Fix: import inside this function so it's resolved at call time.
    """
    from models.base import AsyncSessionLocal as _ASL
    if _ASL is None:
        logger.warning("chat.persist_assistant.no_session_factory", conversation_id=str(conversation_id))
        return
    try:
        async with _ASL() as db:
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
            logger.info(
                "chat.persist_assistant.ok",
                conversation_id=str(conversation_id),
                content_len=len(content),
                message_count=message_count,
            )
    except Exception as exc:
        logger.error(
            "chat.persist_assistant.failed",
            error=str(exc),
            conversation_id=str(conversation_id),
        )


def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
