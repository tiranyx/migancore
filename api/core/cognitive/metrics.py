"""
Mode Metrics — Observability for Thinking Modes
================================================
Track mode detection accuracy, override rate, latency.

Lightweight: stores in Redis with TTL (7 days).
No PostgreSQL dependency for fast writes.

Usage:
    from core.cognitive.metrics import mode_metrics
    
    mode_metrics.record_detection("coding", 0.85, user_input="...")
    mode_metrics.record_override("coding", "inovatif", reason="user_explicit")
    
    stats = mode_metrics.get_stats(hours=24)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from typing import Any, Optional

import structlog

from config import settings

logger = structlog.get_logger()

REDIS_KEY_PREFIX = "mighan:metrics:mode"
DETECTIONS_KEY = f"{REDIS_KEY_PREFIX}:detections"
OVERRIDES_KEY = f"{REDIS_KEY_PREFIX}:overrides"
LATENCY_KEY = f"{REDIS_KEY_PREFIX}:latency"

# TTL: 7 days
METRICS_TTL_SECONDS = 7 * 24 * 3600


@dataclass
class DetectionEvent:
    ts: float
    mode: str
    confidence: float
    input_len: int
    has_history: bool


@dataclass
class OverrideEvent:
    ts: float
    detected_mode: str
    actual_mode: str
    reason: str  # "user_explicit", "feedback_incorrect", "context_switch"


class ModeMetrics:
    """Track thinking mode detection metrics in Redis."""

    def __init__(self):
        self._redis: Any | None = None

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                )
            except Exception as exc:
                logger.warning("mode_metrics.redis_unavailable", error=str(exc))
                return None
        return self._redis

    async def record_detection(
        self,
        mode: str,
        confidence: float,
        user_input: str = "",
        has_history: bool = False,
    ) -> None:
        """Record a mode detection event."""
        try:
            r = await self._get_redis()
            if r is None:
                return

            event = DetectionEvent(
                ts=time.time(),
                mode=mode,
                confidence=confidence,
                input_len=len(user_input),
                has_history=has_history,
            )
            await r.lpush(DETECTIONS_KEY, json.dumps(asdict(event)))
            await r.ltrim(DETECTIONS_KEY, 0, 9999)  # Keep last 10k
            await r.expire(DETECTIONS_KEY, METRICS_TTL_SECONDS)
        except Exception as exc:
            logger.debug("mode_metrics.record_detection_error", error=str(exc))

    async def record_override(
        self,
        detected_mode: str,
        actual_mode: str,
        reason: str = "user_explicit",
    ) -> None:
        """Record when user overrides the detected mode."""
        try:
            r = await self._get_redis()
            if r is None:
                return

            event = OverrideEvent(
                ts=time.time(),
                detected_mode=detected_mode,
                actual_mode=actual_mode,
                reason=reason,
            )
            await r.lpush(OVERRIDES_KEY, json.dumps(asdict(event)))
            await r.ltrim(OVERRIDES_KEY, 0, 999)
            await r.expire(OVERRIDES_KEY, METRICS_TTL_SECONDS)
        except Exception as exc:
            logger.debug("mode_metrics.record_override_error", error=str(exc))

    async def record_latency(self, latency_ms: float) -> None:
        """Record mode detection latency."""
        try:
            r = await self._get_redis()
            if r is None:
                return
            await r.lpush(LATENCY_KEY, str(latency_ms))
            await r.ltrim(LATENCY_KEY, 0, 9999)
            await r.expire(LATENCY_KEY, METRICS_TTL_SECONDS)
        except Exception as exc:
            logger.debug("mode_metrics.record_latency_error", error=str(exc))

    async def get_stats(self, hours: int = 24) -> dict[str, Any]:
        """Get aggregated stats for the last N hours."""
        try:
            r = await self._get_redis()
            if r is None:
                return {"error": "Redis unavailable", "detections": 0}

            cutoff = time.time() - (hours * 3600)

            # Get detections
            detections_raw = await r.lrange(DETECTIONS_KEY, 0, -1)
            detections = [json.loads(d) for d in detections_raw if d]
            detections = [d for d in detections if d.get("ts", 0) > cutoff]

            # Get overrides
            overrides_raw = await r.lrange(OVERRIDES_KEY, 0, -1)
            overrides = [json.loads(o) for o in overrides_raw if o]
            overrides = [o for o in overrides if o.get("ts", 0) > cutoff]

            # Get latency
            latency_raw = await r.lrange(LATENCY_KEY, 0, -1)
            latencies = [float(l) for l in latency_raw if l]

            # Aggregate
            mode_counts: dict[str, int] = {}
            confidence_sum = 0.0
            confidence_count = 0
            history_count = 0

            for d in detections:
                mode_counts[d["mode"]] = mode_counts.get(d["mode"], 0) + 1
                confidence_sum += d.get("confidence", 0)
                confidence_count += 1
                if d.get("has_history"):
                    history_count += 1

            # Override analysis
            override_by_detected: dict[str, int] = {}
            override_by_reason: dict[str, int] = {}
            for o in overrides:
                dm = o.get("detected_mode", "unknown")
                override_by_detected[dm] = override_by_detected.get(dm, 0) + 1
                reason = o.get("reason", "unknown")
                override_by_reason[reason] = override_by_reason.get(reason, 0) + 1

            # Latency stats
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 20 else avg_latency

            return {
                "period_hours": hours,
                "total_detections": len(detections),
                "mode_distribution": mode_counts,
                "avg_confidence": round(confidence_sum / confidence_count, 3) if confidence_count else 0,
                "with_history_ratio": round(history_count / len(detections), 3) if detections else 0,
                "total_overrides": len(overrides),
                "override_rate": round(len(overrides) / len(detections), 4) if detections else 0,
                "override_by_detected": override_by_detected,
                "override_by_reason": override_by_reason,
                "latency_ms": {
                    "avg": round(avg_latency, 3),
                    "p95": round(p95_latency, 3),
                    "count": len(latencies),
                },
            }
        except Exception as exc:
            logger.error("mode_metrics.get_stats_error", error=str(exc))
            return {"error": str(exc), "detections": 0}


mode_metrics = ModeMetrics()
