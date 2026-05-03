"""
Rate limiter dependency — centralized to avoid circular imports.

Day 11: Switched to RedisStorage for multi-worker consistency.
Key function: hybrid — uses X-Tenant-ID header if present, falls back to IP.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from limits.storage import RedisStorage

from config import settings


def _hybrid_key_func(request):
    """Rate limit key: prefer tenant-id header, fallback to remote IP."""
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        return f"tenant:{tenant_id}"
    return get_remote_address(request)


# Redis-backed storage — survives multi-worker deployments
_redis_storage = RedisStorage(settings.REDIS_URL)

limiter = Limiter(
    key_func=_hybrid_key_func,
    storage_uri=settings.REDIS_URL,
)
