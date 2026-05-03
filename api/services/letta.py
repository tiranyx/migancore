"""
Letta client — Tier 3 persistent memory (persona blocks).

Architecture:
  - Storage-only: read/write memory blocks directly via REST API
  - NEVER calls /v1/agents/{id}/messages (Qwen2.5-7B not strong enough for Letta tool calls)
  - Three blocks per MiganCore agent:
      persona   — core identity, voice, values (STABLE, rarely changes)
      mission   — current goals and context (can be updated per task)
      knowledge — facts learned about tenant/owner (grows over time, Day 14+)
  - Graceful degradation: all methods return empty/None on Letta failure
  - Singleton httpx.AsyncClient with asyncio.Lock for thread-safe init

Block limits:
  persona   → 2000 chars  (soul_text + overrides, compact)
  mission   → 1000 chars
  knowledge → 4000 chars  (grows with conversation context)

Why multi-block vs single persona block:
  Separates identity (stable) from knowledge (evolves) so partial updates
  don't corrupt core persona. Day 14+ can auto-update knowledge block from
  conversation without touching the persona block.

Research notes (2026-05-03):
  - Letta 0.6.0 listens on port 8283 (NOT 8083 — EXPOSE directive mismatch)
  - LETTA_URL: http://letta:8283 in config.py is correct
  - llm_config + embedding_config required for memgpt_agent creation (avoids 500)
  - PATCH /v1/agents/{id}/memory/block/{label} works correctly
  - GET /memory returns 500 (Letta bug — use GET /memory/block instead)
"""

import asyncio
import json

import httpx
import structlog

from config import settings

logger = structlog.get_logger()

PERSONA_LIMIT = 2000
MISSION_LIMIT = 1000
KNOWLEDGE_LIMIT = 4000

MISSION_DEFAULT = (
    "Mendukung pengguna dalam ekosistem MiganCore ADO.\n"
    "Beroperasi sesuai visi: setiap visi berhak punya organisme digital."
)
KNOWLEDGE_DEFAULT = "Belum ada pengetahuan spesifik yang tersimpan tentang konteks ini."

_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


async def _get_client() -> httpx.AsyncClient | None:
    """Return singleton httpx.AsyncClient for Letta. Returns None if LETTA_PASSWORD not set."""
    global _client
    if not settings.LETTA_PASSWORD:
        return None
    if _client is None:
        async with _client_lock:
            if _client is None:
                _client = httpx.AsyncClient(
                    base_url=settings.LETTA_URL,
                    headers={
                        "Authorization": f"Bearer {settings.LETTA_PASSWORD}",
                        "Content-Type": "application/json",
                    },
                    timeout=httpx.Timeout(15.0),
                )
    return _client


def format_persona_block(
    agent_name: str,
    soul_text: str,
    persona_overrides: dict | None,
) -> str:
    """Build persona block text from soul_text + overrides.

    Structured for clarity: identity header + soul body + character overrides.
    Truncated to fit PERSONA_LIMIT.
    """
    parts = [f"[IDENTITAS]\nNama: {agent_name}\n"]

    overrides = persona_overrides or {}
    if overrides.get("voice"):
        parts.append(f"Voice: {overrides['voice']}")
    if overrides.get("tone"):
        parts.append(f"Tone: {overrides['tone']}")
    if overrides.get("values"):
        values_str = ", ".join(overrides["values"]) if isinstance(overrides["values"], list) else overrides["values"]
        parts.append(f"Values: {values_str}")

    header = "\n".join(parts) + "\n\n[KARAKTER]\n"

    soul_budget = PERSONA_LIMIT - len(header) - 10
    soul_excerpt = soul_text.strip()[:max(soul_budget, 200)]

    return (header + soul_excerpt)[:PERSONA_LIMIT]


async def ensure_letta_agent(
    migancore_agent_id: str,
    agent_name: str,
    soul_text: str,
    persona_overrides: dict | None,
    existing_letta_id: str | None,
) -> str | None:
    """Get or create a Letta agent for a MiganCore agent.

    Returns letta_agent_id (str) on success, None on failure.
    Idempotent: if existing_letta_id is valid, returns it unchanged.
    """
    client = await _get_client()
    if client is None:
        logger.warning("letta.disabled", reason="LETTA_PASSWORD not configured")
        return None

    # 1. Check if existing Letta agent is still alive
    if existing_letta_id:
        try:
            resp = await client.get(f"/v1/agents/{existing_letta_id}")
            if resp.status_code == 200:
                logger.debug("letta.agent_exists", letta_id=existing_letta_id, migancore_id=migancore_agent_id)
                return existing_letta_id
        except Exception:
            pass

    # 2. Create new Letta agent with three memory blocks
    persona_text = format_persona_block(agent_name, soul_text, persona_overrides)

    payload = {
        "name": f"migancore_{migancore_agent_id}",
        "description": f"MiganCore agent: {agent_name}",
        "agent_type": "memgpt_agent",
        "llm_config": {
            "model": settings.DEFAULT_MODEL,
            "model_endpoint_type": "ollama",
            "model_endpoint": settings.OLLAMA_URL,
            "context_window": 8192,
        },
        "embedding_config": {
            "embedding_endpoint_type": "hugging_face",
            "embedding_model": "letta/letta-free",
            "embedding_dim": 1024,
            "embedding_chunk_size": 300,
        },
        "memory_blocks": [
            {"label": "persona", "value": persona_text, "limit": PERSONA_LIMIT},
            {"label": "mission", "value": MISSION_DEFAULT, "limit": MISSION_LIMIT},
            {"label": "knowledge", "value": KNOWLEDGE_DEFAULT, "limit": KNOWLEDGE_LIMIT},
        ],
        "tools": [],
        "metadata_": {
            "migancore_agent_id": migancore_agent_id,
            "created_by": "migancore-api",
        },
    }

    try:
        resp = await client.post("/v1/agents/", content=json.dumps(payload))
        if resp.status_code in (200, 201):
            data = resp.json()
            letta_id = data.get("id")
            logger.info(
                "letta.agent_created",
                letta_id=letta_id,
                migancore_id=migancore_agent_id,
                name=agent_name,
            )
            return letta_id
        logger.warning(
            "letta.create_failed",
            status=resp.status_code,
            body=resp.text[:300],
            migancore_id=migancore_agent_id,
        )
        return None
    except Exception as exc:
        logger.warning("letta.create_error", error=str(exc), migancore_id=migancore_agent_id)
        return None


async def get_blocks(letta_agent_id: str) -> dict[str, str]:
    """Fetch all memory blocks for a Letta agent.

    Returns dict[label → value]. Returns {} on any error (graceful degradation).
    Uses /memory/block (not /memory — that endpoint has a Letta 0.6.0 bug).
    """
    client = await _get_client()
    if client is None or not letta_agent_id:
        return {}
    try:
        resp = await client.get(f"/v1/agents/{letta_agent_id}/memory/block")
        if resp.status_code == 200:
            blocks = resp.json()
            result = {b["label"]: b["value"] for b in blocks if b.get("label") and b.get("value") is not None}
            logger.debug("letta.blocks_fetched", letta_id=letta_agent_id, labels=list(result.keys()))
            return result
        logger.warning("letta.blocks_fetch_failed", status=resp.status_code, letta_id=letta_agent_id)
        return {}
    except Exception as exc:
        logger.warning("letta.blocks_error", error=str(exc), letta_id=letta_agent_id)
        return {}


async def update_block(letta_agent_id: str, label: str, value: str) -> bool:
    """Update a specific memory block by label.

    Returns True on success, False on failure. Never raises.
    """
    client = await _get_client()
    if client is None or not letta_agent_id:
        return False
    try:
        limits = {"persona": PERSONA_LIMIT, "mission": MISSION_LIMIT, "knowledge": KNOWLEDGE_LIMIT}
        limit = limits.get(label, 5000)
        payload = json.dumps({"value": value[:limit], "limit": limit})
        resp = await client.patch(
            f"/v1/agents/{letta_agent_id}/memory/block/{label}",
            content=payload,
        )
        if resp.status_code == 200:
            logger.info("letta.block_updated", letta_id=letta_agent_id, label=label)
            return True
        logger.warning(
            "letta.block_update_failed",
            status=resp.status_code,
            letta_id=letta_agent_id,
            label=label,
        )
        return False
    except Exception as exc:
        logger.warning("letta.block_update_error", error=str(exc), letta_id=letta_agent_id, label=label)
        return False
