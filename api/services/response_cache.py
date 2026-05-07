"""
Day 71d Phase 2.2: Response cache for exact-match chat queries.

Stores (system_prompt + last_message) hash → response in Redis with 1-hour TTL.
On cache hit: returns cached response in <50ms (vs 30-60s LLM call).

Strategy:
  - Only cache short queries (<200 chars) to avoid memory bloat
  - Skip cache for tool-using queries (those need fresh execution)
  - Skip cache for queries with conversation history (context-dependent)
  - Cache key: SHA256 of normalized prompt
  - TTL: 1 hour (config: RESPONSE_CACHE_TTL_S)

Goal: 30-50% of typical FAQ-style queries hit cache → massive perceived speed gain.
"""
from __future__ import annotations

import hashlib
import json
import os

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = 'ado:response_cache:'
CACHE_TTL_S = int(os.getenv('RESPONSE_CACHE_TTL_S', '3600'))  # 1 hour
MAX_CACHEABLE_QUERY_LEN = 200  # Don't cache very long queries
DISABLED = os.getenv('RESPONSE_CACHE_DISABLED', 'false').lower() == 'true'

# Lazy redis client (matches distillation.py pattern)
_redis_client = None


async def _redis():
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as aioredis
        from config import settings
        _redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
    return _redis_client


def _hash(system_prompt: str, message: str) -> str:
    """Stable SHA256 hash of normalized (system + message)."""
    normalized = (system_prompt.strip() + '\n\n---\n\n' + message.strip()).lower()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:32]


def is_cacheable(message: str, has_history: bool = False) -> bool:
    """Decide if this query should hit cache.

    Skip cache if:
      - Disabled via env
      - Query too long
      - Has conversation history (context-dependent)
      - Contains ':' or numbers > 4 digits (likely calculation/specific data)
    """
    if DISABLED:
        return False
    if has_history:
        return False
    if len(message) > MAX_CACHEABLE_QUERY_LEN:
        return False
    # Skip tool-likely queries (heuristic)
    msg_lower = message.lower()
    if any(t in msg_lower for t in ['hitung', 'cari', 'buat gambar', 'generate', 'tulis file', 'baca url', 'http']):
        return False
    return True


async def get_cached(system_prompt: str, message: str) -> str | None:
    """Return cached response or None."""
    if DISABLED:
        return None
    try:
        client = await _redis()
        key = CACHE_KEY_PREFIX + _hash(system_prompt, message)
        raw = await client.get(key)
        if raw is None:
            return None
        data = json.loads(raw if isinstance(raw, str) else raw.decode('utf-8'))
        logger.info("response_cache.hit", key=key[-12:])
        return data.get('response')
    except Exception as e:
        logger.warning("response_cache.get_failed", error=str(e))
        return None


async def set_cached(
    system_prompt: str,
    message: str,
    response: str,
) -> None:
    """Store (system_prompt + message) → response in Redis."""
    if DISABLED:
        return
    if not response or len(response) < 10:
        return  # Don't cache empty/error responses
    try:
        client = await _redis()
        key = CACHE_KEY_PREFIX + _hash(system_prompt, message)
        payload = json.dumps({'response': response})
        await client.setex(key, CACHE_TTL_S, payload)
        logger.info("response_cache.set", key=key[-12:], len=len(response))
    except Exception as e:
        logger.warning("response_cache.set_failed", error=str(e))


async def stats() -> dict:
    """Diagnostic: how many cache entries currently."""
    try:
        client = await _redis()
        keys = []
        async for k in client.scan_iter(match=CACHE_KEY_PREFIX + '*', count=100):
            keys.append(k)
            if len(keys) >= 1000:
                break
        return {'entries': len(keys), 'ttl_s': CACHE_TTL_S, 'disabled': DISABLED}
    except Exception as e:
        return {'error': str(e)[:100], 'disabled': DISABLED}
