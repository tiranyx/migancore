"""
Tool result caching layer (Day 43 — Innovation #2).

Caches idempotent tool calls in Redis (fast, TTL-native) keyed by SHA256 of
(tool_name + sorted args + tool_version). Per-tool TTL prevents stale results.

Why Redis not Qdrant:
- Tool results are key-value, not embedding-search → Redis fits better
- Existing Redis infra (Day 1) — zero new infra
- Native TTL (Qdrant doesn't have TTL — would need cron cleanup)
- Sub-ms read latency vs Qdrant ~10ms

Design:
- Wrap ToolExecutor.execute() — check cache first, miss → call handler → cache
- Per-tool TTL config (volatile=5min, stable=24h, never=disable cache)
- Cache key includes tool_version for safe invalidation on schema change
- Skip caching for tool_calls that mutate state (memory_write, write_file, spawn_agent)

Expected impact:
- Repeat ONAMIX search "AI news today": 1000ms → 5ms (200x)
- Same image analyze: 5000ms → 5ms (1000x — image hash → cached caption stable 24h)
- Synthetic gen calls overlapping with chat: massive savings
"""
from __future__ import annotations

import hashlib
import json
import time

import structlog

from config import settings

logger = structlog.get_logger()


# ----------------------------------------------------------------------------
# Per-tool TTL config (seconds)
#   None  = NEVER cache (mutating tools, creative tools)
#   0     = no expiry
#   N     = TTL seconds
#
# Tool version string is included in cache key — bump when output schema changes
# to atomically invalidate stale entries without manual flush.
# ----------------------------------------------------------------------------
TOOL_CACHE_CONFIG: dict[str, tuple[int | None, str]] = {
    # name              (ttl_seconds, version)
    "web_search":       (300,    "v1"),   # 5 min — search results volatile
    "web_read":         (600,    "v1"),   # 10 min — page content semi-stable
    "http_get":         (300,    "v1"),   # 5 min — generic GET
    "onamix_get":       (600,    "v1"),   # 10 min
    "onamix_search":    (300,    "v1"),   # 5 min
    "onamix_scrape":    (600,    "v1"),   # 10 min
    "analyze_image":    (86400,  "v1"),   # 24h — image hash → caption stable
    # NEVER cache (mutating / creative / per-request unique):
    "memory_write":     (None,   "v1"),
    "memory_search":    (None,   "v1"),   # tenant-scoped, per-call
    "spawn_agent":      (None,   "v1"),
    "write_file":       (None,   "v1"),
    "read_file":        (None,   "v1"),   # workspace mutates
    "python_repl":      (None,   "v1"),   # side effects
    "generate_image":   (None,   "v1"),   # creative variance desired
    "text_to_speech":   (None,   "v1"),   # creative variance
    "export_pdf":       (None,   "v1"),   # one-shot deterministic, but cheap
    "export_slides":    (None,   "v1"),   # same as PDF
}

CACHE_KEY_PREFIX = "tool:cache:v1"


def _is_cacheable(tool_name: str) -> tuple[bool, int | None, str]:
    """Return (cacheable, ttl_seconds, tool_version)."""
    cfg = TOOL_CACHE_CONFIG.get(tool_name)
    if not cfg:
        return False, None, "v0"
    ttl, version = cfg
    if ttl is None:
        return False, None, version
    return True, ttl, version


def _stable_args_json(args: dict) -> str:
    """Deterministic JSON encoding for cache key — sort keys recursively.
    Strips ctx/tenant_id-like fields that vary per call but don't affect output.
    """
    def _clean(obj):
        if isinstance(obj, dict):
            # Drop request-scoped fields that don't affect output
            return {
                k: _clean(v) for k, v in obj.items()
                if k not in ("ctx", "request_id", "tenant_id", "user_id")
            }
        if isinstance(obj, list):
            return [_clean(x) for x in obj]
        return obj
    return json.dumps(_clean(args), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def cache_key(tool_name: str, args: dict, version: str = "v1") -> str:
    """Generate stable cache key: prefix + tool + version + sha256(args)."""
    args_str = _stable_args_json(args)
    digest = hashlib.sha256(args_str.encode("utf-8")).hexdigest()[:24]
    return f"{CACHE_KEY_PREFIX}:{tool_name}:{version}:{digest}"


# ----------------------------------------------------------------------------
# Redis async pool (lazy init, reused across calls)
# ----------------------------------------------------------------------------
_redis_pool = None


async def _redis():
    """Get or init shared Redis async pool."""
    global _redis_pool
    if _redis_pool is None:
        import redis.asyncio as aioredis
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=False,  # we store bytes, decode JSON ourselves
        )
    return _redis_pool


async def get_cached(tool_name: str, args: dict) -> dict | None:
    """Look up cached result. Returns None on miss/error/disabled."""
    cacheable, ttl, version = _is_cacheable(tool_name)
    if not cacheable:
        return None
    try:
        r = await _redis()
        key = cache_key(tool_name, args, version)
        raw = await r.get(key)
        if raw is None:
            return None
        try:
            payload = json.loads(raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw)
        except Exception:
            return None
        # Validate envelope
        if not isinstance(payload, dict) or "result" not in payload:
            return None
        logger.info(
            "tool.cache.hit",
            tool=tool_name,
            key=key.split(":")[-1],
            cached_at=payload.get("cached_at"),
        )
        return payload["result"]
    except Exception as exc:
        logger.warning("tool.cache.get_error", tool=tool_name, error=str(exc))
        return None


async def set_cached(tool_name: str, args: dict, result: dict) -> None:
    """Store result with per-tool TTL. Silent failure (cache is best-effort)."""
    cacheable, ttl, version = _is_cacheable(tool_name)
    if not cacheable or not isinstance(result, dict):
        return
    # Don't cache error results
    if result.get("error") or result.get("success") is False:
        return
    try:
        r = await _redis()
        key = cache_key(tool_name, args, version)
        envelope = {
            "result": result,
            "cached_at": int(time.time()),
            "tool": tool_name,
            "version": version,
        }
        payload = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
        await r.set(key, payload, ex=ttl)
        logger.info(
            "tool.cache.set",
            tool=tool_name,
            key=key.split(":")[-1],
            ttl=ttl,
            bytes=len(payload),
        )
    except Exception as exc:
        logger.warning("tool.cache.set_error", tool=tool_name, error=str(exc))


async def cache_stats() -> dict:
    """Quick stats on cache (size, hit rate optional via separate counters)."""
    try:
        r = await _redis()
        # Approximate: count keys with our prefix (use SCAN, not KEYS, for prod safety)
        count = 0
        async for _ in r.scan_iter(match=f"{CACHE_KEY_PREFIX}:*", count=200):
            count += 1
        return {
            "cache_prefix": CACHE_KEY_PREFIX,
            "approx_entries": count,
            "config_tool_count": sum(1 for cfg in TOOL_CACHE_CONFIG.values() if cfg[0] is not None),
        }
    except Exception as exc:
        return {"error": str(exc)}
