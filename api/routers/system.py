"""
Day 71d Phase 2.1: /v1/system/* — telemetry + diagnostic endpoints.

Public:
  GET /v1/system/status  — basic health + tool count + brain version (no auth)
  GET /v1/system/metrics — latency p50/p95, cache stats, tool relevance status (no auth)
"""
from __future__ import annotations

from collections import deque
from time import time

from fastapi import APIRouter

router = APIRouter(prefix="/v1/system", tags=["system"])

# ---------- in-memory latency tracker (last 200 calls) ----------
_latency_window: deque[tuple[str, float]] = deque(maxlen=200)


def record_latency(route: str, elapsed_s: float) -> None:
    """Append (route, elapsed_s, timestamp) to rolling window. Called from chat router."""
    _latency_window.append((route, elapsed_s))


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = max(0, min(len(s) - 1, int(len(s) * pct / 100)))
    return s[idx]


@router.get("/status")
async def system_status() -> dict:
    """Lightweight status: brain alive, tool count, basic versions."""
    from config import settings
    try:
        from services.tool_relevance import is_ready as tr_ready, stats as tr_stats
    except ImportError:
        tr_ready = lambda: False
        tr_stats = lambda: {}

    return {
        "status": "operational",
        "brain": {
            "model": getattr(settings, 'OLLAMA_DEFAULT_MODEL', 'migancore:0.7c'),
            "available_tools": 29,
        },
        "tool_relevance": {
            "ready": tr_ready() if callable(tr_ready) else False,
            **(tr_stats() if callable(tr_stats) else {}),
        },
        "version": "0.5.16",
        "build_day": "Day 71d",
    }


@router.get("/metrics")
async def system_metrics() -> dict:
    """Performance metrics: latency p50/p95 by route, cache stats."""
    from config import settings

    by_route: dict[str, list[float]] = {}
    for route, elapsed in _latency_window:
        by_route.setdefault(route, []).append(elapsed)

    routes_metrics = {}
    for route, lats in by_route.items():
        routes_metrics[route] = {
            "count": len(lats),
            "p50": round(_percentile(lats, 50), 2),
            "p95": round(_percentile(lats, 95), 2),
            "p99": round(_percentile(lats, 99), 2),
            "avg": round(sum(lats) / len(lats), 2),
            "max": round(max(lats), 2),
        }

    # Response cache stats
    cache_stats = {}
    try:
        from services.response_cache import stats as cache_stats_fn
        cache_stats = await cache_stats_fn()
    except Exception as e:
        cache_stats = {"error": str(e)[:100]}

    # Tool relevance
    tr = {}
    try:
        from services.tool_relevance import stats as tr_stats
        tr = tr_stats()
    except Exception:
        pass

    return {
        "timestamp_unix": int(time()),
        "samples_window": len(_latency_window),
        "routes": routes_metrics,
        "response_cache": cache_stats,
        "tool_relevance": tr,
    }
