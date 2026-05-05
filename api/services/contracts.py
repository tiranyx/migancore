"""
Design by Contract for LLM Agents (Day 47 — meta-pattern).

Single module that addresses 4 historical bug classes via runtime invariant
assertions instead of silent state drift:

| Day | Bug | Contract that catches it |
|-----|-----|--------------------------|
|  39 | asyncio.create_task swallowed exception → silent for 2 days | safe_task() wrapper logs + counts failures |
|  44 | container kill killed background task → 14h silent stall    | TaskRegistry watchdog logs alive-count every 60s |
|  45 | auto-resume condition wrong → fix didn't fire on first deploy | (state-machine guards in caller — out of scope here) |
|  46 | agents.json drift from skills.json → brain saw deprecated tool only | validate_tool_registry() at boot — fail-loud |

Research basis (Day 47 agent synthesis):
- Letta v0.6 docs: TaskGroup migration for exception propagation
- Pydantic AI: output contracts on every LLM boundary
- Instructor library: validation+retry pattern
- OpenTelemetry GenAI semantic conventions Jan 2026

Design principle: **fail loud, not silent.** A noisy log on every drift is
strictly better than a silent failure that takes 14h to discover.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Coroutine

import structlog

logger = structlog.get_logger()


# ============================================================================
# 1. BOOT-TIME CONTRACT VALIDATION (catches Day 46 tool-registration drift)
# ============================================================================

class ContractViolation(Exception):
    """Raised when a runtime invariant is broken. Boot-time violations should
    fail-loud (log error + crash), not be swallowed."""


def validate_tool_registry(
    tool_handlers: dict,
    agents_config: dict,
    skills_config: dict,
) -> dict:
    """Validate consistency across the 3 sources of truth for tools:

    1. `TOOL_HANDLERS` dict in tool_executor.py — what the EXECUTOR can dispatch
    2. `agents.json` `default_tools` per agent — what each AGENT can SEE
    3. `skills.json` schemas — what the LLM knows about (descriptions, args)

    Returns dict of warnings/errors. Caller decides whether to crash or log.

    Drift modes detected:
    - Tool referenced in agent.default_tools but missing from TOOL_HANDLERS
      → AI will see schema, try to call, get "no handler" error
    - Tool referenced in agent.default_tools but missing from skills.json
      → tool spec build will silently skip it (Day 46 bug class)
    - Tool registered in TOOL_HANDLERS but no agent has it
      → dead code, harmless but wasteful
    - Skill schema describes a tool not registered
      → orphan schema, MCP listing will lie about capabilities
    - Skill description references DEPRECATED tool that doesn't exist anywhere
      → brain confusion, empty-output bug class (Day 46)
    """
    handler_names = set(tool_handlers.keys())
    skill_ids = {s["id"] for s in skills_config.get("skills", [])}
    agent_tool_refs: dict[str, set[str]] = {}
    for agent in agents_config.get("agents", []):
        agent_tool_refs[agent["id"]] = set(agent.get("default_tools", []))

    errors: list[str] = []
    warnings: list[str] = []

    # Per-agent checks
    for agent_id, tools in agent_tool_refs.items():
        # Tools assigned to agent but no handler exists
        missing_handler = tools - handler_names
        if missing_handler:
            errors.append(
                f"agent '{agent_id}' references tool(s) with NO handler in "
                f"TOOL_HANDLERS: {sorted(missing_handler)}"
            )
        # Tools assigned to agent but no skill schema (LLM won't know args)
        missing_schema = tools - skill_ids
        if missing_schema:
            errors.append(
                f"agent '{agent_id}' references tool(s) with NO schema in "
                f"skills.json: {sorted(missing_schema)}"
            )

    # Orphan checks
    all_assigned = set().union(*agent_tool_refs.values()) if agent_tool_refs else set()
    orphan_handlers = handler_names - all_assigned
    if orphan_handlers:
        warnings.append(
            f"TOOL_HANDLERS registered but no agent uses them: {sorted(orphan_handlers)}"
        )
    orphan_schemas = skill_ids - handler_names
    if orphan_schemas:
        warnings.append(
            f"skills.json describes tool(s) with NO handler (LLM will hallucinate): "
            f"{sorted(orphan_schemas)}"
        )

    # Day 46 — DEPRECATED reference detector: any skill description that
    # mentions "use X instead" where X is not a real handler
    import re
    for skill in skills_config.get("skills", []):
        desc = (skill.get("description") or "")
        # Match patterns like "use foo_bar instead" or "use `foo_bar`"
        for m in re.finditer(r"use\s+`?([a-z_][a-z_0-9]*)`?\s+instead", desc, re.I):
            referenced = m.group(1).lower()
            if referenced not in handler_names:
                errors.append(
                    f"skill '{skill['id']}' description tells LLM to "
                    f"'use {referenced} instead' but {referenced} is NOT in TOOL_HANDLERS "
                    f"(Day 46 bug class — brain confusion → empty output)"
                )

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "handlers": len(handler_names),
            "schemas": len(skill_ids),
            "agents": len(agent_tool_refs),
            "tools_per_agent": {k: len(v) for k, v in agent_tool_refs.items()},
        },
    }


# ============================================================================
# 2. SAFE TASK WRAPPER + REGISTRY (catches Day 39 + Day 44 silent task death)
# ============================================================================

class TaskRegistry:
    """Global registry of long-lived async tasks. Watchdog checks alive-count
    every 60s and logs anomalies. Tasks register themselves via safe_task()."""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self._failures: dict[str, int] = {}  # name → cumulative failure count
        self._created_at: dict[str, float] = {}

    def register(self, name: str, task: asyncio.Task) -> None:
        # If a previous task with same name exists, keep the old failure count
        self._tasks[name] = task
        self._created_at[name] = time.time()
        self._failures.setdefault(name, 0)

    def unregister(self, name: str) -> None:
        self._tasks.pop(name, None)
        self._created_at.pop(name, None)

    def record_failure(self, name: str) -> None:
        self._failures[name] = self._failures.get(name, 0) + 1

    def stats(self) -> dict:
        alive = sum(1 for t in self._tasks.values() if not t.done())
        dead = len(self._tasks) - alive
        return {
            "registered": len(self._tasks),
            "alive": alive,
            "dead_in_registry": dead,
            "failures_total": sum(self._failures.values()),
            "by_name": {
                k: {
                    "alive": not v.done() if v else False,
                    "failures": self._failures.get(k, 0),
                    "age_s": int(time.time() - self._created_at.get(k, time.time())),
                }
                for k, v in self._tasks.items()
            },
        }


_REGISTRY = TaskRegistry()


def get_registry() -> TaskRegistry:
    return _REGISTRY


def safe_task(
    coro: Coroutine,
    name: str,
    *,
    register: bool = True,
) -> asyncio.Task:
    """Wrap a coroutine in a try/except that LOGS failures instead of swallowing.

    Replaces bare `asyncio.create_task(some_coro())` which silently drops
    exceptions if no .add_done_callback handles them — Day 39 bug class.

    If `register=True`, the task is added to the global TaskRegistry where the
    watchdog can detect silent death between scheduled and effective runs.
    """
    async def _wrapped():
        try:
            return await coro
        except asyncio.CancelledError:
            logger.info("safe_task.cancelled", name=name)
            raise
        except Exception as exc:
            _REGISTRY.record_failure(name)
            logger.error(
                "safe_task.failed",
                name=name,
                error=str(exc),
                exc_info=True,
            )
            # Don't re-raise — task failure should not bring down the loop

    task = asyncio.create_task(_wrapped(), name=name)
    if register:
        _REGISTRY.register(name, task)
        task.add_done_callback(lambda t: _REGISTRY.unregister(name))
    return task


async def watchdog_loop(interval_s: float = 60.0) -> None:
    """Background coroutine: every `interval_s` seconds, log TaskRegistry stats.

    Catches:
    - Slow leak of dead tasks (registered but completed, never unregistered)
    - Failure-rate spikes
    - Long-running zombie tasks (age_s growing while not making progress)

    Started by lifespan; cancelled on shutdown.
    """
    logger.info("contracts.watchdog.started", interval_s=interval_s)
    while True:
        try:
            await asyncio.sleep(interval_s)
            stats = _REGISTRY.stats()
            logger.info(
                "contracts.watchdog.tick",
                alive=stats["alive"],
                registered=stats["registered"],
                dead_in_registry=stats["dead_in_registry"],
                failures_total=stats["failures_total"],
            )
            # Anomaly: any tasks dead but still in registry (callback failed?)
            if stats["dead_in_registry"] > 0:
                logger.warning(
                    "contracts.watchdog.dead_tasks_in_registry",
                    detail=stats["by_name"],
                )
        except asyncio.CancelledError:
            logger.info("contracts.watchdog.stopped")
            return
        except Exception as exc:
            logger.error("contracts.watchdog.error", error=str(exc))


# ============================================================================
# 3. OUTPUT CONTRACTS (catches Day 46 empty-response bug class)
# ============================================================================

class EmptyLLMResponse(ContractViolation):
    """LLM returned empty content AND no tool calls — degenerate state."""


def assert_llm_response_meaningful(
    content: str | None,
    tool_calls: list | None,
    *,
    where: str = "unknown",
) -> bool:
    """Returns True if response is meaningful (has content OR tool calls).
    Returns False if degenerate. Caller decides retry strategy.

    NOT a hard exception by default — degenerate responses ARE expected
    occasionally (network blips, tool registration drift, etc.). This just
    surfaces them via structured log so we see them in monitoring.
    """
    has_content = bool((content or "").strip())
    has_calls = bool(tool_calls)
    if not (has_content or has_calls):
        logger.warning(
            "contracts.empty_llm_response",
            where=where,
            content_len=len(content or ""),
            tool_calls_count=len(tool_calls or []),
        )
        return False
    return True


# ============================================================================
# Public API for lifespan startup wiring
# ============================================================================

def boot_check_and_log() -> dict:
    """Run all boot-time contracts. Returns the validate_tool_registry result.

    Logs:
      contracts.boot.ok      — all checks passed
      contracts.boot.warning — orphans/dead-code (non-fatal)
      contracts.boot.error   — drift detected (LLM-visible bug)

    Caller (lifespan) decides whether to crash on errors. We default to
    LOG-LOUDLY-but-CONTINUE so an upgrade isn't blocked by a single drift
    issue, but the operator sees it immediately.
    """
    try:
        # Day 47 fix: actual export is TOOL_REGISTRY, not TOOL_HANDLERS.
        # Caught immediately on first deploy by contracts.boot.crashed log
        # — perfect demo of the meta-pattern's value (silent assumption broken
        # by reality, contract assertion surfaced it in <1s instead of next bug).
        from .tool_executor import TOOL_REGISTRY
        from .config_loader import load_agents_config, load_skills_config
        result = validate_tool_registry(
            TOOL_REGISTRY,
            load_agents_config(),
            load_skills_config(),
        )
    except Exception as exc:
        logger.error("contracts.boot.crashed", error=str(exc), exc_info=True)
        return {"ok": False, "errors": [str(exc)], "warnings": [], "stats": {}}

    if result["ok"]:
        logger.info(
            "contracts.boot.ok",
            handlers=result["stats"]["handlers"],
            schemas=result["stats"]["schemas"],
            agents=result["stats"]["agents"],
            tools_per_agent=result["stats"]["tools_per_agent"],
        )
    for err in result["errors"]:
        logger.error("contracts.boot.error", detail=err)
    for warn in result["warnings"]:
        logger.warning("contracts.boot.warning", detail=warn)
    return result
