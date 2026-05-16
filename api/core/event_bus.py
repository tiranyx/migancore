"""
SYARAF — Event Bus (Redis Pub/Sub)
====================================
Async event system for inter-service communication.
All services connect to Redis; this adds pub/sub layer on top.

Usage:
    from core.event_bus import event_bus
    
    # Publish
    await event_bus.publish("mighan:conversation:new", {
        "conversation_id": str(conv_id),
        "tenant_id": str(tenant_id),
        "user_message": message,
    })
    
    # Subscribe (in worker/async task)
    async for event in event_bus.subscribe("mighan:feedback:*"):
        await process_feedback(event)
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Optional

import structlog

logger = structlog.get_logger()

# Channel definitions — canonical source of truth
CHANNELS = {
    # Conversation lifecycle
    "conversation:new": "mighan:conversation:new",
    "conversation:ended": "mighan:conversation:ended",
    
    # Feedback & learning
    "feedback:received": "mighan:feedback:received",
    "training:dataset:updated": "mighan:training:dataset:updated",
    "eval:gate:failed": "mighan:eval:gate:failed",
    
    # Memory & KG
    "memory:updated": "mighan:memory:updated",
    "kg:entity:extracted": "mighan:kg:entity:extracted",
    "kg:relation:extracted": "mighan:kg:relation:extracted",
    
    # Agent lifecycle
    "agent:spawned": "mighan:agent:spawned",
    "agent:terminated": "mighan:agent:terminated",
    
    # Code Lab
    "code:executed": "mighan:code:executed",
    "code:lesson:saved": "mighan:code:lesson:saved",
    
    # Reflection & proposals
    "reflection:created": "mighan:reflection:created",
    "proposal:submitted": "mighan:proposal:submitted",
    "proposal:decided": "mighan:proposal:decided",
    
    # System
    "system:health:check": "mighan:system:health:check",
    "system:alert": "mighan:system:alert",
}


@dataclass
class Event:
    """Canonical event envelope."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    channel: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "unknown"
    tenant_id: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, default=str)

    @classmethod
    def from_json(cls, raw: str | bytes) -> Event:
        data = json.loads(raw) if isinstance(raw, str) else json.loads(raw.decode("utf-8"))
        return cls(**data)


class EventBus:
    """Redis-backed async event bus."""

    def __init__(self):
        self._redis: Any = None
        self._pubsub: Any = None
        self._listeners: dict[str, list[Callable]] = {}
        self._connected = False

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                from config import settings
                self._redis = aioredis.from_url(
                    settings.REDIS_URL,
                    socket_connect_timeout=2,
                    socket_read_timeout=2,
                    decode_responses=False,
                )
                self._connected = True
            except Exception as exc:
                logger.warning("event_bus.redis_connect_failed", error=str(exc))
                self._connected = False
        return self._redis

    async def publish(self, channel: str, payload: dict[str, Any], source: str = "api", tenant_id: Optional[str] = None) -> bool:
        """Publish an event to a channel.
        
        Returns True if published, False if Redis unavailable (logged, not crashed).
        """
        try:
            r = await self._get_redis()
            if r is None:
                logger.debug("event_bus.publish_skipped", channel=channel, reason="redis_unavailable")
                return False

            event = Event(channel=channel, payload=payload, source=source, tenant_id=tenant_id)
            await r.publish(channel, event.to_json())
            logger.info("event_bus.published", channel=channel, event_id=event.id, source=source)
            return True
        except Exception as exc:
            logger.warning("event_bus.publish_failed", channel=channel, error=str(exc))
            return False

    async def subscribe(self, pattern: str) -> AsyncIterator[Event]:
        """Subscribe to events matching a pattern (e.g., 'mighan:feedback:*').
        
        Usage:
            async for event in event_bus.subscribe("mighan:code:*"):
                print(event.payload)
        """
        try:
            import redis.asyncio as aioredis
            from config import settings
            r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2, decode_responses=False)
            pubsub = r.pubsub()
            await pubsub.psubscribe(pattern)
            logger.info("event_bus.subscribed", pattern=pattern)

            async for message in pubsub.listen():
                if message["type"] in ("pmessage", "message"):
                    try:
                        event = Event.from_json(message["data"])
                        yield event
                    except Exception as exc:
                        logger.warning("event_bus.parse_failed", error=str(exc), raw=message.get("data"))
        except Exception as exc:
            logger.error("event_bus.subscribe_failed", pattern=pattern, error=str(exc))
            raise

    async def add_listener(self, channel: str, handler: Callable[[Event], Any]) -> None:
        """Add a persistent listener for a channel.
        
        Listeners run in background via asyncio.create_task().
        """
        if channel not in self._listeners:
            self._listeners[channel] = []
        self._listeners[channel].append(handler)
        
        # Start background consumer if not already running
        asyncio.create_task(self._consume_channel(channel))
        logger.info("event_bus.listener_added", channel=channel)

    async def _consume_channel(self, channel: str) -> None:
        """Background consumer for a channel."""
        try:
            async for event in self.subscribe(channel):
                handlers = self._listeners.get(channel, [])
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            asyncio.create_task(handler(event))
                        else:
                            handler(event)
                    except Exception as exc:
                        logger.error("event_bus.handler_failed", channel=channel, error=str(exc))
        except asyncio.CancelledError:
            logger.info("event_bus.consumer_cancelled", channel=channel)
        except Exception as exc:
            logger.error("event_bus.consumer_failed", channel=channel, error=str(exc))

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    async def conversation_new(self, conversation_id: str, tenant_id: str, user_message: str, **extra) -> bool:
        return await self.publish(
            CHANNELS["conversation:new"],
            {"conversation_id": conversation_id, "tenant_id": tenant_id, "user_message": user_message, **extra},
            tenant_id=tenant_id,
        )

    async def feedback_received(self, feedback_id: str, tenant_id: str, rating: int, **extra) -> bool:
        return await self.publish(
            CHANNELS["feedback:received"],
            {"feedback_id": feedback_id, "tenant_id": tenant_id, "rating": rating, **extra},
            tenant_id=tenant_id,
        )

    async def code_executed(self, execution_id: str, tenant_id: str, success: bool, score: float, **extra) -> bool:
        return await self.publish(
            CHANNELS["code:executed"],
            {"execution_id": execution_id, "tenant_id": tenant_id, "success": success, "score": score, **extra},
            tenant_id=tenant_id,
        )

    async def reflection_created(self, reflection_key: str, content: str, **extra) -> bool:
        return await self.publish(
            CHANNELS["reflection:created"],
            {"reflection_key": reflection_key, "content": content, **extra},
        )

    async def proposal_submitted(self, proposal_id: str, title: str, risk_level: str, **extra) -> bool:
        return await self.publish(
            CHANNELS["proposal:submitted"],
            {"proposal_id": proposal_id, "title": title, "risk_level": risk_level, **extra},
        )

    async def eval_gate_failed(self, test_name: str, score: float, threshold: float, **extra) -> bool:
        return await self.publish(
            CHANNELS["eval:gate:failed"],
            {"test_name": test_name, "score": score, "threshold": threshold, **extra},
        )


# Singleton instance
event_bus = EventBus()
