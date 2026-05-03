"""
Fact extractor — Letta knowledge block auto-update (Day 14).

Extracts new facts from each conversation turn and appends them to the
agent's Letta knowledge block. Runs in background via asyncio.create_task.

Architecture:
  - Uses Qwen2.5-0.5B (fast, low RAM) — not the main 7B chat model
  - Fire-and-forget: never blocks HTTP response
  - Date-sectioned format: [YYYY-MM-DD]\\n- fact1\\n- fact2
  - FIFO trimming when approaching KNOWLEDGE_LIMIT (3600 char threshold)
  - Graceful degradation: all errors → silent skip

Why 0.5B not 7B:
  Fact extraction is a structured output task (format: bullet points).
  Small model handles this reliably. Avoids resource contention with
  the 7B model serving concurrent chat requests.

Deduplication:
  Extraction prompt includes the last 500 chars of existing knowledge.
  LLM is instructed to skip facts already present. Not perfect but
  good enough — occasional near-duplication is acceptable.
"""

import asyncio
import re
from datetime import datetime, timezone

import structlog

from services.letta import KNOWLEDGE_DEFAULT, KNOWLEDGE_LIMIT, update_block
from services.ollama import OllamaClient, OllamaError

logger = structlog.get_logger()

EXTRACT_MODEL = "qwen2.5:0.5b"
KNOWLEDGE_TRIM_THRESHOLD = 3600  # Trim oldest section when combined exceeds this

_EXTRACT_PROMPT = (
    "Kamu adalah sistem ekstraksi fakta minimal. "
    "Tugasmu: temukan fakta baru yang SPESIFIK tentang pengguna dari percakapan ini.\n\n"
    "[PENGGUNA]: {user_message}\n"
    "[ASISTEN]: {assistant_response}\n\n"
    "[PENGETAHUAN YANG SUDAH ADA (terbaru)]:\n"
    "{existing_tail}\n\n"
    "ATURAN:\n"
    "1. Hanya fakta SPESIFIK dan BARU — nama, profesi, proyek, preferensi, tujuan, stack\n"
    "2. JANGAN duplikasi dari [PENGETAHUAN YANG SUDAH ADA]\n"
    "3. Jika tidak ada fakta baru → jawab hanya: TIDAK ADA\n"
    "4. Format output: satu fakta per baris, awali dengan '- '\n"
    "5. Maksimal 5 fakta, singkat dan padat\n\n"
    "Fakta baru:"
)

_SECTION_PATTERN = re.compile(r"\n\n(?=\[)")


def _build_extract_messages(
    user_message: str,
    assistant_response: str,
    existing_knowledge: str,
) -> list[dict]:
    existing_tail = existing_knowledge[-500:] if len(existing_knowledge) > 500 else existing_knowledge
    prompt = _EXTRACT_PROMPT.format(
        user_message=user_message[:300],
        assistant_response=assistant_response[:300],
        existing_tail=existing_tail,
    )
    return [{"role": "user", "content": prompt}]


def _trim_knowledge_if_needed(current: str, new_section: str) -> str:
    """Append new_section to current, trimming oldest date sections if over threshold."""
    is_placeholder = KNOWLEDGE_DEFAULT in current or not current.strip()
    combined = new_section if is_placeholder else (current.rstrip() + "\n\n" + new_section)

    if len(combined) <= KNOWLEDGE_TRIM_THRESHOLD:
        return combined

    parts = _SECTION_PATTERN.split(combined)
    while len("\n\n".join(parts)) > KNOWLEDGE_TRIM_THRESHOLD and len(parts) > 1:
        parts.pop(0)

    return ("\n\n".join(parts))[:KNOWLEDGE_LIMIT]


async def extract_facts(
    user_message: str,
    assistant_response: str,
    existing_knowledge: str,
) -> str | None:
    """Call Ollama 0.5B to extract new facts from a conversation turn.

    Returns a bullet-point string (lines starting with '- ') or None if no new facts.
    Never raises — all errors return None.
    """
    messages = _build_extract_messages(user_message, assistant_response, existing_knowledge)

    try:
        async with OllamaClient() as client:
            data = await client.chat(
                model=EXTRACT_MODEL,
                messages=messages,
                options={"num_predict": 200, "temperature": 0},
            )
        raw = data.get("message", {}).get("content", "").strip()

        if not raw or len(raw) < 5 or "TIDAK ADA" in raw.upper():
            return None

        lines = [line.strip() for line in raw.splitlines() if line.strip().startswith("- ")]
        if not lines:
            return None

        return "\n".join(lines)

    except OllamaError as exc:
        logger.warning("fact_extractor.ollama_error", error=str(exc), model=EXTRACT_MODEL)
        return None
    except Exception as exc:
        logger.warning("fact_extractor.extract_error", error=str(exc))
        return None


async def maybe_update_knowledge_block(
    letta_agent_id: str,
    user_message: str,
    assistant_response: str,
    letta_blocks: dict[str, str],
) -> None:
    """Extract facts from a conversation turn and append to Letta knowledge block.

    Called via asyncio.create_task — fire-and-forget, never raises.
    Uses 0.5B model for extraction to avoid resource contention with main 7B model.
    """
    try:
        existing_knowledge = letta_blocks.get("knowledge", KNOWLEDGE_DEFAULT)

        new_facts = await extract_facts(user_message, assistant_response, existing_knowledge)
        if not new_facts:
            logger.debug("fact_extractor.no_new_facts", letta_id=letta_agent_id)
            return

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        new_section = f"[{date_str}]\n{new_facts}"

        updated_knowledge = _trim_knowledge_if_needed(existing_knowledge, new_section)

        success = await update_block(letta_agent_id, "knowledge", updated_knowledge)
        if success:
            logger.info(
                "fact_extractor.knowledge_updated",
                letta_id=letta_agent_id,
                new_facts_count=new_facts.count("\n- ") + 1,
                knowledge_len=len(updated_knowledge),
            )

    except Exception as exc:
        logger.warning("fact_extractor.update_error", error=str(exc), letta_id=letta_agent_id)
