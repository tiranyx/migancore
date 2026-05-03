"""
Tool executor — dispatches skill_id to handler functions.

Architecture:
  TOOL_REGISTRY: dict[str, handler_fn]
  ToolContext: carries tenant/agent info for storage-aware tools
  ToolExecutor.execute(): validate → dispatch → return structured result

Handlers:
  web_search     — DuckDuckGo Instant Answers (free, no key)
  memory_write   — Redis K-V tier 1 storage
  memory_search  — Redis K-V prefix + substring search (Qdrant hybrid + Redis fallback)
  python_repl    — subprocess isolation (process boundary = real sandbox)
  generate_image — fal.ai FLUX schnell (Day 24) — needs FAL_KEY env
  read_file      — Read file from /app/workspace/ sandbox (Day 24)
  write_file     — Write file to /app/workspace/ sandbox (Day 24)

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

Day 24 notes (2026-05-04):
  - fal.ai FLUX schnell: POST https://fal.run/fal-ai/flux/schnell, sync response ~3-8s
  - File sandbox: WORKSPACE_DIR=/app/workspace, path traversal blocked via Path.resolve()
  - generate_image timeout: 60s (fal.ai cold start can hit 15-20s occasionally)
"""

import asyncio
import json
import subprocess
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Coroutine

import httpx
import structlog

from config import settings
from services.config_loader import load_skills_config
from services.memory import memory_write, memory_list
from services.tool_policy import ToolPolicyChecker, validate_python_code, PolicyViolation

logger = structlog.get_logger()

MAX_TOOL_ITERATIONS = 5
DDG_ENDPOINT = "https://api.duckduckgo.com/"
FAL_FLUX_ENDPOINT = "https://fal.run/fal-ai/flux/schnell"
FAL_VALID_SIZES = {
    "square_hd", "square", "portrait_4_3", "portrait_16_9",
    "landscape_4_3", "landscape_16_9",
}


# ---------------------------------------------------------------------------
# Context passed to all handlers
# ---------------------------------------------------------------------------

@dataclass
class ToolContext:
    tenant_id: str
    agent_id: str
    tenant_plan: str = "free"
    tool_policies: dict | None = None


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
    """Search agent memory — Qdrant hybrid semantic (Tier 2) with Redis K-V fallback (Tier 1).

    Day 12: Qdrant semantic search first → Redis substring fallback.
    Day 18: search_semantic() is now hybrid (dense + BM42 sparse + RRF).
    Day 20: Added asyncio.wait_for timeout (2.0s) — prevents blocking tool loop
            if Qdrant is slow. Falls through to Redis on timeout.
    """
    query = args.get("query", "").strip()
    limit = min(int(args.get("limit", 5)), 20)

    if not query:
        raise ToolExecutionError("'query' is required")

    # Tier 2: Qdrant hybrid semantic search (dense + BM42 sparse + RRF)
    try:
        from services.vector_memory import search_semantic
        semantic_hits = await asyncio.wait_for(
            search_semantic(ctx.agent_id, query, top_k=limit),
            timeout=2.0,
        )
        if semantic_hits:
            logger.info(
                "tool.memory_search.qdrant",
                query=query,
                matches=len(semantic_hits),
                top_score=semantic_hits[0].get("_retrieval_score", 0) if semantic_hits else 0,
            )
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


async def _python_repl(args: dict, ctx: ToolContext) -> dict:
    """Execute Python code via subprocess — real process isolation.

    subprocess gives a genuine sandbox boundary vs exec() which is trivially
    escaped via __subclasses__() or __import__. Output capped at 2000 chars.

    Day 11: Added import blacklist validation (defense-in-depth).
    """
    code = args.get("code", "").strip()
    timeout = min(int(args.get("timeout", 30)), 30)

    if not code:
        raise ToolExecutionError("'code' is required")

    # Policy layer: block dangerous imports
    try:
        validate_python_code(code)
    except PolicyViolation as exc:
        logger.warning("tool.python_repl.policy_violation", reason=exc.reason, agent=ctx.agent_id)
        raise ToolExecutionError(f"Security policy violation: {exc.reason}") from exc

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


async def _generate_image(args: dict, ctx: ToolContext) -> dict:
    """Generate an image via fal.ai FLUX schnell.

    Day 24: fal.ai REST API — sync endpoint, ~3-8s per image.
    Model: fal-ai/flux/schnell — 4 inference steps, fast, cheap (~$0.003/image).
    Requires FAL_KEY environment variable.

    Returns image URL (hosted on fal.media CDN, persistent).
    """
    prompt = args.get("prompt", "").strip()
    if not prompt:
        raise ToolExecutionError("'prompt' is required")

    image_size = args.get("image_size", "landscape_4_3").strip()
    if image_size not in FAL_VALID_SIZES:
        image_size = "landscape_4_3"

    num_images = max(1, min(int(args.get("num_images", 1)), 4))

    fal_key = settings.FAL_KEY
    if not fal_key:
        raise ToolExecutionError(
            "Image generation is not configured (FAL_KEY missing). "
            "Contact admin to enable this tool."
        )

    payload = {
        "prompt": prompt,
        "image_size": image_size,
        "num_inference_steps": 4,
        "num_images": num_images,
        "enable_safety_checker": True,
    }

    logger.info("tool.generate_image.start", prompt=prompt[:80], size=image_size, n=num_images)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            resp = await client.post(
                FAL_FLUX_ENDPOINT,
                json=payload,
                headers={
                    "Authorization": f"Key {fal_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        raise ToolExecutionError("Image generation timed out (60s). Try again.")
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:200]
        raise ToolExecutionError(f"fal.ai API error {exc.response.status_code}: {body}") from exc
    except Exception as exc:
        raise ToolExecutionError(f"Image generation failed: {exc}") from exc

    images = data.get("images", [])
    if not images:
        raise ToolExecutionError("fal.ai returned no images. Try a different prompt.")

    result_images = [
        {
            "url": img.get("url", ""),
            "width": img.get("width"),
            "height": img.get("height"),
        }
        for img in images
    ]

    inference_time = data.get("timings", {}).get("inference")
    seed = data.get("seed")

    logger.info(
        "tool.generate_image.done",
        images=len(result_images),
        url=result_images[0]["url"][:60] if result_images else "",
        inference_s=inference_time,
    )

    return {
        "images": result_images,
        "prompt": prompt,
        "model": "fal-ai/flux/schnell",
        "seed": seed,
        "inference_time_s": round(inference_time, 2) if inference_time else None,
        # Convenience shortcut for single-image requests
        "url": result_images[0]["url"] if result_images else None,
    }


def _resolve_workspace_path(user_path: str) -> Path:
    """Resolve a user-supplied path relative to WORKSPACE_DIR.

    Prevents path traversal attacks by ensuring the resolved path stays
    within WORKSPACE_DIR. Raises ToolExecutionError for invalid paths.
    """
    workspace = Path(settings.WORKSPACE_DIR).resolve()
    # Strip leading slashes/dots to force relative interpretation
    clean = user_path.lstrip("/").lstrip(".")
    if not clean:
        raise ToolExecutionError("'path' must not be empty or root")

    target = (workspace / clean).resolve()

    # Strict containment check
    try:
        target.relative_to(workspace)
    except ValueError:
        raise ToolExecutionError(
            f"Path traversal blocked: '{user_path}' is outside workspace"
        )

    return target


async def _read_file(args: dict, ctx: ToolContext) -> dict:
    """Read a file from the agent's sandboxed workspace (/app/workspace/).

    Day 24: File system access for coding/agentic workflows.
    All paths are relative to WORKSPACE_DIR — no escaping the sandbox.
    Max file size: 50KB (larger files truncated with a notice).
    """
    user_path = args.get("path", "").strip()
    if not user_path:
        raise ToolExecutionError("'path' is required")

    try:
        target = _resolve_workspace_path(user_path)
    except ToolExecutionError:
        raise
    except Exception as exc:
        raise ToolExecutionError(f"Invalid path: {exc}") from exc

    if not target.exists():
        raise ToolExecutionError(f"File not found: {user_path}")
    if target.is_dir():
        # List directory contents instead
        entries = sorted(str(p.relative_to(target.parent)) for p in target.iterdir())
        return {
            "type": "directory",
            "path": user_path,
            "entries": entries[:100],
        }

    MAX_BYTES = 50_000
    try:
        raw = target.read_bytes()
        truncated = len(raw) > MAX_BYTES
        content = raw[:MAX_BYTES].decode("utf-8", errors="replace")

        logger.info("tool.read_file", path=user_path, size=len(raw), agent=ctx.agent_id)
        return {
            "content": content,
            "path": user_path,
            "size_bytes": len(raw),
            "truncated": truncated,
            "truncated_at": MAX_BYTES if truncated else None,
        }
    except Exception as exc:
        raise ToolExecutionError(f"Cannot read file: {exc}") from exc


async def _write_file(args: dict, ctx: ToolContext) -> dict:
    """Write content to a file in the agent's sandboxed workspace (/app/workspace/).

    Day 24: File system write for coding/agentic workflows.
    Creates parent directories automatically. Max content: 200KB.
    """
    user_path = args.get("path", "").strip()
    content = args.get("content", "")

    if not user_path:
        raise ToolExecutionError("'path' is required")
    if content is None:
        raise ToolExecutionError("'content' is required")

    MAX_CONTENT = 200_000
    if len(content) > MAX_CONTENT:
        raise ToolExecutionError(
            f"Content too large ({len(content)} chars). Max: {MAX_CONTENT} chars."
        )

    try:
        target = _resolve_workspace_path(user_path)
    except ToolExecutionError:
        raise
    except Exception as exc:
        raise ToolExecutionError(f"Invalid path: {exc}") from exc

    try:
        # Ensure workspace and parent dirs exist
        workspace = Path(settings.WORKSPACE_DIR)
        workspace.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)

        target.write_text(content, encoding="utf-8")
        logger.info("tool.write_file", path=user_path, size=len(content), agent=ctx.agent_id)

        return {
            "status": "written",
            "path": user_path,
            "size_bytes": len(content.encode("utf-8")),
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        raise ToolExecutionError(f"Cannot write file: {exc}") from exc


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

HandlerFn = Callable[[dict, ToolContext], Coroutine[Any, Any, dict]]

TOOL_REGISTRY: dict[str, HandlerFn] = {
    "web_search": _web_search,
    "memory_write": _memory_write,
    "memory_search": _memory_search,
    "python_repl": _python_repl,
    # Day 24 — Tool Expansion
    "generate_image": _generate_image,
    "read_file": _read_file,
    "write_file": _write_file,
}


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class ToolExecutor:
    """Dispatches tool calls to handlers. All errors are caught and returned.

    Day 11: Added policy enforcement layer before handler dispatch.
    """

    def __init__(self, ctx: ToolContext):
        self.ctx = ctx
        self._checker: ToolPolicyChecker | None = None
        if ctx.tool_policies is not None:
            self._checker = ToolPolicyChecker(
                tenant_plan=ctx.tenant_plan,
                tenant_id=ctx.tenant_id,
                tool_policies=ctx.tool_policies,
            )

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

        # Day 11: Policy enforcement
        if self._checker is not None:
            try:
                await self._checker.check(skill_id)
            except PolicyViolation as exc:
                logger.warning(
                    "tool.policy_blocked",
                    skill=skill_id,
                    violation=exc.violation_type,
                    reason=exc.reason,
                    tenant=self.ctx.tenant_id,
                )
                return {
                    "result": None,
                    "error": f"Policy blocked: {exc.reason}",
                    "success": False,
                    "policy_violation": exc.violation_type,
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
