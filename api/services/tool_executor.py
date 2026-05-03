"""
Tool executor — dispatches skill_id to handler functions.

Architecture:
  TOOL_REGISTRY: dict[str, handler_fn]
  ToolContext: carries tenant/agent info for storage-aware tools
  ToolExecutor.execute(): validate → dispatch → return structured result

Handlers:
  web_search   — DuckDuckGo Instant Answers (free, no key)
  memory_write — Redis K-V tier 1 storage
  memory_search — Redis K-V prefix + substring search
  python_repl  — subprocess isolation (process boundary = real sandbox)

Tool calling flow (in chat.py):
  1. Build Ollama tools spec from skills.json
  2. Call Ollama with messages + tools
  3. If response.tool_calls → execute each → inject role:"tool" message
  4. Re-call Ollama (loop max MAX_TOOL_ITERATIONS)
  5. Persist all tool_calls in messages.tool_calls column

Research notes (2026-05-03):
  - Qwen2.5-7B-Instruct supports Ollama native tool calling (stream=false required)
  - Tool result format: {"role": "tool", "content": "<json string>"}
  - DuckDuckGo JSON API: no key, ~20 req/s per IP, good for MVP
  - subprocess gives real process isolation vs exec() which is easily escaped
"""

import asyncio
import json
import subprocess
import urllib.parse
from dataclasses import dataclass
from typing import Any, Callable, Coroutine

import httpx
import structlog

from services.config_loader import load_skills_config
from services.memory import memory_write, memory_list

logger = structlog.get_logger()

MAX_TOOL_ITERATIONS = 5
DDG_ENDPOINT = "https://api.duckduckgo.com/"


# ---------------------------------------------------------------------------
# Context passed to all handlers
# ---------------------------------------------------------------------------

@dataclass
class ToolContext:
    tenant_id: str
    agent_id: str


class ToolExecutionError(Exception):
    """Raised for expected handler errors (bad args, API failure, etc.)."""
    pass


# ---------------------------------------------------------------------------
# Handlers — each returns a JSON-serializable dict
# ---------------------------------------------------------------------------

async def _web_search(args: dict, ctx: ToolContext) -> dict:
    """DuckDuckGo Instant Answers — free, no API key, works server-side."""
    query = args.get("query", "").strip()
    limit = min(int(args.get("limit", 5)), 10)

    if not query:
        raise ToolExecutionError("'query' is required")

    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
        "kl": "id-id",
    })

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get(
                f"{DDG_ENDPOINT}?{params}",
                headers={"User-Agent": "MiganCore/0.3.0"},
                follow_redirects=True,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException as exc:
        raise ToolExecutionError("Web search timed out") from exc
    except Exception as exc:
        raise ToolExecutionError(f"Web search failed: {exc}") from exc

    results: list[dict] = []

    # Direct one-box answer (highest priority)
    if data.get("Answer"):
        results.append({
            "title": "Jawaban Langsung",
            "snippet": data["Answer"],
            "url": "",
            "source": "DuckDuckGo",
        })

    # Abstract (Wikipedia / knowledge graph)
    if data.get("Abstract"):
        results.append({
            "title": data.get("Heading", query),
            "snippet": data["Abstract"],
            "url": data.get("AbstractURL", ""),
            "source": data.get("AbstractSource", ""),
        })

    # Related topics
    for topic in data.get("RelatedTopics", []):
        if len(results) >= limit:
            break
        if isinstance(topic, dict) and topic.get("Text"):
            results.append({
                "title": topic["Text"][:80],
                "snippet": topic["Text"],
                "url": topic.get("FirstURL", ""),
                "source": "DuckDuckGo",
            })

    logger.info("tool.web_search", query=query, results=len(results))
    return {
        "results": results[:limit],
        "query": query,
        "result_count": len(results),
    }


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
    """Search agent memory by key/value substring matching."""
    query = args.get("query", "").strip()
    limit = min(int(args.get("limit", 5)), 20)

    if not query:
        raise ToolExecutionError("'query' is required")

    all_memories = await memory_list(ctx.tenant_id, ctx.agent_id, limit=100)
    query_lower = query.lower()

    matches = [
        {"key": k, "value": v}
        for k, v in all_memories.items()
        if query_lower in k.lower() or query_lower in v.lower()
    ]

    logger.info("tool.memory_search", query=query, matches=len(matches))
    return {
        "results": matches[:limit],
        "query": query,
        "total_in_memory": len(all_memories),
    }


async def _python_repl(args: dict, ctx: ToolContext) -> dict:
    """Execute Python code via subprocess — real process isolation.

    subprocess gives a genuine sandbox boundary vs exec() which is trivially
    escaped via __subclasses__() or __import__. Output capped at 2000 chars.
    """
    code = args.get("code", "").strip()
    timeout = min(int(args.get("timeout", 30)), 30)

    if not code:
        raise ToolExecutionError("'code' is required")

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                subprocess.run,
                ["python", "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
            ),
            timeout=float(timeout) + 2,
        )

        stdout = (result.stdout or "")[:2000]
        stderr = (result.stderr or "")[:500]

        logger.info("tool.python_repl", rc=result.returncode, agent=ctx.agent_id)
        return {
            "output": stdout,
            "error": stderr if stderr else None,
            "return_code": result.returncode,
            "success": result.returncode == 0,
        }

    except asyncio.TimeoutError:
        return {"output": "", "error": f"Timed out after {timeout}s", "success": False, "return_code": -1}
    except FileNotFoundError:
        return {"output": "", "error": "Python interpreter not found", "success": False, "return_code": -1}
    except Exception as exc:
        return {"output": "", "error": str(exc), "success": False, "return_code": -1}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

HandlerFn = Callable[[dict, ToolContext], Coroutine[Any, Any, dict]]

TOOL_REGISTRY: dict[str, HandlerFn] = {
    "web_search": _web_search,
    "memory_write": _memory_write,
    "memory_search": _memory_search,
    "python_repl": _python_repl,
}


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class ToolExecutor:
    """Dispatches tool calls to handlers. All errors are caught and returned."""

    def __init__(self, ctx: ToolContext):
        self.ctx = ctx

    async def execute(self, skill_id: str, arguments: dict) -> dict:
        """Execute a tool and return {"result": ..., "error": ..., "success": bool}."""
        handler = TOOL_REGISTRY.get(skill_id)
        if not handler:
            logger.warning("tool.unknown", skill=skill_id)
            return {
                "result": None,
                "error": f"Unknown tool '{skill_id}'. Available: {list(TOOL_REGISTRY)}",
                "success": False,
            }

        try:
            result = await handler(arguments, self.ctx)
            return {"result": result, "error": None, "success": True}
        except ToolExecutionError as exc:
            logger.warning("tool.validation_error", skill=skill_id, error=str(exc))
            return {"result": None, "error": str(exc), "success": False}
        except Exception as exc:
            logger.error("tool.unexpected", skill=skill_id, error=str(exc))
            return {"result": None, "error": f"Unexpected error: {exc}", "success": False}


def build_ollama_tools_spec(skill_ids: list[str]) -> list[dict]:
    """Convert skill IDs to Ollama tool spec format (OpenAI-compatible).

    Reads schemas from skills.json. Skips unknown or non-MCP skills.
    """
    skills_cfg = load_skills_config()
    skill_map = {s["id"]: s for s in skills_cfg.get("skills", [])}

    tools = []
    for sid in skill_ids:
        skill = skill_map.get(sid)
        if not skill:
            continue
        if not skill.get("mcp_compatible", False):
            continue
        tools.append({
            "type": "function",
            "function": {
                "name": skill["id"],
                "description": skill["description"],
                "parameters": skill.get("schema", {"type": "object", "properties": {}}),
            },
        })
    return tools
