"""Base organ — ToolContext, ToolExecutionError, ToolExecutor.

This is the vascular system that connects all tool organs.
"""

import json
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class ToolContext:
    tenant_id: str
    agent_id: str
    tenant_plan: str = "free"
    tool_policies: dict | None = None


class ToolExecutionError(Exception):
    """Raised for expected handler errors (bad args, API failure, etc.)."""
    pass


class ToolExecutor:
    """Dispatch skill_id to handler via a lazy-loaded registry.

    The registry is built on first use so that all organ modules have
    finished importing (avoiding circular imports).
    """

    _registry: dict[str, Any] = {}
    _loaded: bool = False

    def __init__(self, ctx: ToolContext):
        self.ctx = ctx
        if not ToolExecutor._loaded:
            ToolExecutor._registry = self._build_registry()
            ToolExecutor._loaded = True

    @staticmethod
    def _build_registry() -> dict[str, Any]:
        """Import organs and collect their handlers."""
        registry: dict[str, Any] = {}

        # Import each organ module; each registers its handlers into REGISTRY.
        # We do this lazily to avoid circular imports at module load time.
        try:
            from . import web, memory, code, media, files, onamix, exports
            registry.update(web.HANDLERS)
            registry.update(memory.HANDLERS)
            registry.update(code.HANDLERS)
            registry.update(media.HANDLERS)
            registry.update(files.HANDLERS)
            registry.update(onamix.HANDLERS)
            registry.update(exports.HANDLERS)
        except Exception as exc:
            logger.warning("tools.registry_load_failed", error=str(exc))

        return registry

    async def execute(self, skill_id: str, arguments: dict) -> dict:
        """Validate → dispatch → return structured result."""
        handler = ToolExecutor._registry.get(skill_id)
        if handler is None:
            # Fallback: cognitive tools loaded from external modules
            from services.tools_cognitive import COGNITIVE_TOOLS
            from services.tools_advanced import ADVANCED_TOOLS
            handler = {**COGNITIVE_TOOLS, **ADVANCED_TOOLS}.get(skill_id)

        if handler is None:
            return {
                "success": False,
                "error": f"Unknown skill: {skill_id}",
                "result": None,
            }

        try:
            result = await handler(arguments, self.ctx)
            if not isinstance(result, dict):
                result = {"result": result}
            return {"success": True, "error": None, "result": result}
        except ToolExecutionError as exc:
            logger.warning("tool.execution_error", skill=skill_id, error=str(exc))
            return {"success": False, "error": str(exc), "result": None}
        except Exception as exc:
            logger.exception("tool.unexpected_error", skill=skill_id)
            return {"success": False, "error": f"Internal error: {exc}", "result": None}
