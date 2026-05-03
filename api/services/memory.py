"""
Redis-backed key-value memory service — Tier 1 memory for agents.

Architecture:
  Tier 1 (this file): Redis K-V, 30-day TTL, instant read/write
  Tier 2 (Day 12): Qdrant semantic vector search
  Tier 3 (Day 11): Letta working memory blocks + persona persistence

Key pattern: mem:{tenant_id}:{agent_id}:{namespace}:{key}
"""

import redis.asyncio as aioredis

from config import settings

import asyncio

# Singleton connection pool — shared across all requests
_pool: aioredis.ConnectionPool | None = None
_pool_lock = asyncio.Lock()
_MAX_MEMORY_ITEMS = 20  # Max items returned in summary


async def _get_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = aioredis.ConnectionPool.from_url(
                    settings.REDIS_URL,
                    max_connections=10,
                    decode_responses=True,
                )
    return _pool


async def _redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=await _get_pool())


def _key(tenant_id: str, agent_id: str, namespace: str, key: str) -> str:
    return f"mem:{tenant_id}:{agent_id}:{namespace}:{key}"


async def memory_write(
    tenant_id: str,
    agent_id: str,
    key: str,
    value: str,
    namespace: str = "default",
    ttl_days: int = 30,
) -> None:
    """Write a key-value pair to agent memory."""
    r = await _redis()
    await r.set(
        _key(tenant_id, agent_id, namespace, key),
        value,
        ex=ttl_days * 86400,
    )


async def memory_read(
    tenant_id: str,
    agent_id: str,
    key: str,
    namespace: str = "default",
) -> str | None:
    """Read a single value from agent memory."""
    r = await _redis()
    return await r.get(_key(tenant_id, agent_id, namespace, key))


async def memory_delete(
    tenant_id: str,
    agent_id: str,
    key: str,
    namespace: str = "default",
) -> None:
    """Delete a key from agent memory."""
    r = await _redis()
    await r.delete(_key(tenant_id, agent_id, namespace, key))


async def memory_list(
    tenant_id: str,
    agent_id: str,
    namespace: str = "default",
    limit: int = _MAX_MEMORY_ITEMS,
) -> dict[str, str]:
    """List all memory entries for an agent namespace.

    Uses SCAN (non-blocking) instead of KEYS. Returns at most `limit` entries.
    """
    r = await _redis()
    pattern = f"mem:{tenant_id}:{agent_id}:{namespace}:*"
    prefix_len = len(f"mem:{tenant_id}:{agent_id}:{namespace}:")

    collected: list[str] = []
    cursor = 0
    while True:
        cursor, found = await r.scan(cursor, match=pattern, count=100)
        collected.extend(found)
        if cursor == 0 or len(collected) >= limit:
            break

    collected = collected[:limit]
    if not collected:
        return {}

    values = await r.mget(*collected)
    return {
        k[prefix_len:]: v
        for k, v in zip(collected, values)
        if v is not None
    }


async def memory_summary(
    tenant_id: str,
    agent_id: str,
    namespace: str = "default",
    max_items: int = 10,
) -> str:
    """Return a formatted memory summary for system prompt injection.

    Returns empty string if no memories exist (no token waste).
    """
    memories = await memory_list(tenant_id, agent_id, namespace, limit=max_items)
    if not memories:
        return ""

    lines = ["[Yang Aku Ingat tentang Kamu]"]
    for k, v in list(memories.items())[:max_items]:
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)
