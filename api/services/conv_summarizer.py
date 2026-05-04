"""
Conversation summarization (Day 45 — Innovation #1).

Sleep-time hierarchical summarization: when conversation history exceeds
~2900 tokens (70% of NUM_CTX=4096), older turns are folded into a structured
JSON summary stored in Redis, while the most recent N turns stay verbatim.

Why "sleep-time":
- Run ASYNC after stream completes — never blocks user response
- Local Qwen 7B does the work (~30-60s CPU) — $0 cost
- The model summarizing its own conversations IS DPO-grade training data
  (research-validated, Letta sleep-time agents pattern Apr 2025)

Design decisions (research-validated):
1. Trigger at ~2900 tokens (70% of num_ctx), NOT 2000 — too aggressive
2. Hierarchical 70/30: older 70% summarized, recent 30% verbatim
3. ALWAYS keep last 4 turns verbatim regardless (recency bias of users)
4. NEVER summarize within tool-call sequence (orphans tool_use_id pairs —
   Day 39 bug class). Only trigger between assistant final-answer turns.
5. Output: structured JSON {decisions, entities, open_questions,
   user_preferences, last_intent} — free text loses 30-40% recoverable facts
6. Storage: Redis with TTL 7d, keyed by (conv_id, version)
7. Bump version on prompt change to atomically invalidate stale summaries

Anti-pattern guarded against (Day 39 lesson #45):
   - role='tool' message anywhere in the to-summarize range → REFUSE
   - Tool sequences are atomic; cannot be summarized without breaking
     ID pairing for downstream tool_result lookups
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx
import structlog

from config import settings

logger = structlog.get_logger()

# ----------------------------------------------------------------------------
# Tunables (research-validated defaults)
# ----------------------------------------------------------------------------
SUMMARY_TRIGGER_TOKENS = 2900         # 70% of num_ctx=4096
SUMMARY_KEEP_TAIL_TURNS = 4           # always-verbatim recent window
SUMMARY_KEEP_TAIL_FRACTION = 0.30     # of total tokens (recency bias)
SUMMARY_VERSION = "v1"                # bump on prompt schema change
SUMMARY_REDIS_TTL_S = 7 * 24 * 3600   # 7 days
CHARS_PER_TOKEN = 3.5                 # mixed Bahasa + English
SUMMARIZER_MODEL = "qwen2.5:7b-instruct-q4_K_M"
SUMMARIZER_TIMEOUT_S = 120.0

CACHE_KEY_PREFIX = "conv:summary:v1"


# ----------------------------------------------------------------------------
# Token estimation (consistent with chat.py)
# ----------------------------------------------------------------------------
def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def total_tokens(messages: list[dict]) -> int:
    return sum(estimate_tokens(m.get("content") or "") for m in messages)


# ----------------------------------------------------------------------------
# Trigger predicate — answers "should we summarize this conversation now?"
# ----------------------------------------------------------------------------
def should_summarize(messages: list[dict]) -> tuple[bool, str]:
    """Decide if a conversation should be summarized.

    Returns (should, reason). Reason is "ok" if yes, else explains skip.
    """
    if len(messages) < 8:
        return False, "too_few_turns"
    tok = total_tokens(messages)
    if tok < SUMMARY_TRIGGER_TOKENS:
        return False, f"under_threshold ({tok}<{SUMMARY_TRIGGER_TOKENS})"
    # Mid-tool-loop guard — refuse if any role='tool' in the segment we'd
    # summarize (everything but last 4 turns)
    head_segment = messages[:-SUMMARY_KEEP_TAIL_TURNS]
    for m in head_segment:
        if m.get("role") == "tool":
            return False, "tool_sequence_in_head_segment"
    # Last message must be assistant final-answer (not tool result)
    if messages and messages[-1].get("role") not in ("assistant", "user"):
        return False, "tail_in_tool_loop"
    return True, "ok"


# ----------------------------------------------------------------------------
# Summarization prompt + parser
# ----------------------------------------------------------------------------
_SUMMARY_PROMPT = """Anda adalah penyusun ringkasan memori percakapan untuk agent AI.

Tugas: Ringkas SEGMENT percakapan berikut menjadi JSON terstruktur untuk
disimpan sebagai memori episodik. Pertahankan: nama, angka, keputusan, file
path, intent. Buang: basa-basi, salam, repetisi.

Output HANYA JSON valid, tanpa fence ```, sesuai schema ini:
{
  "decisions": ["<keputusan konkret yang dibuat>"],
  "entities": [
    {"name": "<nama>", "type": "<person|file|tool|concept>", "facts": ["<fakta>"]}
  ],
  "open_questions": ["<pertanyaan belum terjawab>"],
  "user_preferences": ["<sinyal style/format/tone user>"],
  "last_intent": "<apa yang user coba capai di akhir segment>"
}

Jika tidak ada item untuk suatu kategori, pakai array kosong [] atau "" untuk last_intent.

SEGMENT PERCAKAPAN:
{conversation}

JSON:"""


def _format_segment_for_prompt(messages: list[dict]) -> str:
    """Format messages as readable conversation text for the summarizer."""
    lines = []
    for m in messages:
        role = m.get("role", "unknown").upper()
        content = (m.get("content") or "").strip()
        if not content:
            continue
        # Cap each message at 2000 chars to keep prompt under control
        if len(content) > 2000:
            content = content[:2000] + "…[disingkat]"
        lines.append(f"{role}: {content}")
    return "\n\n".join(lines)


async def _call_qwen_summarizer(prompt: str) -> str:
    """Invoke local Qwen via Ollama /api/generate. Returns raw text response."""
    payload = {
        "model": SUMMARIZER_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 800,   # summary stays compact
            "num_ctx": 4096,
        },
    }
    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/generate"
    async with httpx.AsyncClient(timeout=SUMMARIZER_TIMEOUT_S) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    return (data.get("response") or "").strip()


def _parse_json_loosely(text: str) -> dict:
    """Parse summarizer output. Handles common LLM JSON issues:
    - markdown fence wrapping (```json ... ```)
    - leading/trailing prose
    - empty response
    Returns empty dict on parse failure (caller should treat as no summary).
    """
    if not text:
        return {}
    # Strip code fences
    s = text.strip()
    if s.startswith("```"):
        # Drop first and last fence line
        lines = s.split("\n")
        if len(lines) >= 3:
            s = "\n".join(lines[1:-1]).strip()
        else:
            s = s.strip("`").strip()
    # Find first { and last } to extract JSON object
    i, j = s.find("{"), s.rfind("}")
    if i == -1 or j == -1 or j <= i:
        return {}
    candidate = s[i:j + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {}


# ----------------------------------------------------------------------------
# Public summarization API
# ----------------------------------------------------------------------------
async def summarize_segment(messages: list[dict]) -> dict:
    """Summarize a list of messages. Returns parsed JSON dict (may be empty
    on failure — caller decides whether to fall back to drop-oldest)."""
    if not messages:
        return {}
    conversation = _format_segment_for_prompt(messages)
    if not conversation:
        return {}
    prompt = _SUMMARY_PROMPT.replace("{conversation}", conversation)
    t0 = time.perf_counter()
    try:
        raw = await _call_qwen_summarizer(prompt)
    except Exception as exc:
        logger.warning("conv_summarizer.call_failed", error=str(exc))
        return {}
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    parsed = _parse_json_loosely(raw)
    logger.info(
        "conv_summarizer.done",
        elapsed_ms=elapsed_ms,
        msg_count=len(messages),
        parsed_keys=list(parsed.keys()) if parsed else [],
        raw_len=len(raw),
    )
    return parsed


# ----------------------------------------------------------------------------
# Redis storage (best-effort, silent failures — cache is optional)
# ----------------------------------------------------------------------------
_redis_pool = None


async def _redis():
    global _redis_pool
    if _redis_pool is None:
        import redis.asyncio as aioredis
        _redis_pool = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    return _redis_pool


def _summary_key(conv_id: str) -> str:
    return f"{CACHE_KEY_PREFIX}:{conv_id}"


async def get_cached_summary(conv_id: str) -> dict | None:
    """Returns {"summary": <dict>, "head_message_count": int, "cached_at": int}
    or None if no cached summary."""
    try:
        r = await _redis()
        raw = await r.get(_summary_key(conv_id))
        if not raw:
            return None
        return json.loads(raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw)
    except Exception as exc:
        logger.warning("conv_summarizer.cache_get_error", conv_id=conv_id, error=str(exc))
        return None


async def set_cached_summary(
    conv_id: str,
    summary: dict,
    head_message_count: int,
) -> None:
    """Persist a summary covering the FIRST head_message_count messages."""
    if not summary:
        return
    envelope = {
        "summary": summary,
        "head_message_count": head_message_count,
        "cached_at": int(time.time()),
        "version": SUMMARY_VERSION,
    }
    try:
        r = await _redis()
        payload = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
        await r.set(_summary_key(conv_id), payload, ex=SUMMARY_REDIS_TTL_S)
        logger.info(
            "conv_summarizer.cache_set",
            conv_id=conv_id,
            head_count=head_message_count,
            bytes=len(payload),
        )
    except Exception as exc:
        logger.warning("conv_summarizer.cache_set_error", conv_id=conv_id, error=str(exc))


# ----------------------------------------------------------------------------
# Helpers for chat.py integration
# ----------------------------------------------------------------------------
def format_summary_as_system_message(summary: dict) -> dict:
    """Render a summary dict as a synthetic system message that the LLM
    can read as 'previous conversation context'."""
    if not summary:
        return {}
    # Compact JSON inline — model parses well, saves tokens vs pretty-printed
    body = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
    return {
        "role": "system",
        "content": (
            "[KONTEKS PERCAKAPAN SEBELUMNYA — sudah diringkas dari turn lama. "
            "Pertahankan continuity tapi JANGAN ulang pengantar/salam.]\n"
            f"{body}"
        ),
    }


async def trigger_background_summarization(
    conv_id: str,
    messages: list[dict],
) -> bool:
    """Schedule async summarization if conditions met. Non-blocking.

    Returns True if a task was scheduled, False if skipped.
    Called from chat.py post-stream-completion (alongside _persist_assistant_message).
    """
    if not conv_id:
        return False
    should, reason = should_summarize(messages)
    if not should:
        logger.debug("conv_summarizer.skip", conv_id=conv_id, reason=reason)
        return False

    # Decide cut point: keep tail = max(SUMMARY_KEEP_TAIL_TURNS, 30% of msgs)
    tail_count = max(SUMMARY_KEEP_TAIL_TURNS, int(len(messages) * SUMMARY_KEEP_TAIL_FRACTION))
    head_count = len(messages) - tail_count
    if head_count < 4:
        return False
    head_segment = messages[:head_count]

    async def _task():
        try:
            summary = await summarize_segment(head_segment)
            if summary:
                await set_cached_summary(conv_id, summary, head_count)
            else:
                logger.info(
                    "conv_summarizer.no_summary_produced",
                    conv_id=conv_id,
                    head_count=head_count,
                )
        except Exception as exc:
            logger.warning(
                "conv_summarizer.bg_task_error",
                conv_id=conv_id,
                error=str(exc),
            )

    asyncio.create_task(_task(), name=f"conv_summarize_{conv_id[:8]}")
    logger.info(
        "conv_summarizer.scheduled",
        conv_id=conv_id,
        head_count=head_count,
        tail_count=tail_count,
        total_tokens=total_tokens(messages),
    )
    return True
