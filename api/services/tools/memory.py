"""Memory organ — Tier-1 Redis K-V and Tier-2 Qdrant hybrid search."""

import asyncio
from typing import Any

import structlog

from services.memory import memory_write, memory_list
from .base import ToolContext, ToolExecutionError

logger = structlog.get_logger()


async def _memory_write(args: dict, ctx: ToolContext) -> dict:
    """Write a key-value pair to agent's Redis memory (Tier 1)."""
    key = args.get("key", "").strip()
    value = args.get("value", "").strip()
    namespace = args.get("namespace", "default").strip() or "default"

    if not key:
        raise ToolExecutionError("'key' is required")
    if not value:
        raise ToolExecutionError("'value' is required")

    await memory_write(ctx.tenant_id, ctx.agent_id, key, value, namespace)
    logger.info("tool.memory_write", key=key, ns=namespace, agent=ctx.agent_id)
    return {"status": "written", "key": key, "namespace": namespace}


async def _memory_search(args: dict, ctx: ToolContext) -> dict:
    """Search agent memory — Qdrant hybrid semantic (Tier 2) with Redis K-V fallback (Tier 1)."""
    query = args.get("query", "").strip()
    limit = min(int(args.get("limit", 5)), 20)

    if not query:
        raise ToolExecutionError("'query' is required")

    # Tier 2: Qdrant hybrid semantic search
    try:
        from services.vector_memory import search_semantic
        semantic_hits = await asyncio.wait_for(
            search_semantic(ctx.agent_id, query, top_k=limit),
            timeout=2.0,
        )
        if semantic_hits:
            logger.info("tool.memory_search.qdrant", query=query, matches=len(semantic_hits))
            return {
                "results": [
                    {
                        "user_message": r.get("user_message", ""),
                        "assistant_message": r.get("assistant_message", ""),
                        "session_id": r.get("session_id"),
                        "turn_index": r.get("turn_index"),
                        "timestamp": r.get("timestamp"),
                        "score": r.get("_retrieval_score"),
                    }
                    for r in semantic_hits
                ],
                "query": query,
                "source": "qdrant_hybrid",
            }
    except asyncio.TimeoutError:
        logger.warning("tool.memory_search.qdrant_timeout", query=query, timeout_s=2.0)
    except Exception as exc:
        logger.warning("tool.memory_search.qdrant_error", error=str(exc))

    # Tier 1 fallback: Redis K-V substring search
    all_memories = await memory_list(ctx.tenant_id, ctx.agent_id, limit=100)
    query_lower = query.lower()
    matches = [
        {"key": k, "value": v}
        for k, v in all_memories.items()
        if query_lower in k.lower() or query_lower in v.lower()
    ]
    logger.info("tool.memory_search.redis", query=query, matches=len(matches))
    return {
        "results": matches[:limit],
        "query": query,
        "total_in_memory": len(all_memories),
        "source": "redis_kv",
    }


HANDLERS: dict[str, Any] = {
    "memory_write": _memory_write,
    "memory_search": _memory_search,
}
