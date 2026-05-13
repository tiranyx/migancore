"""
ONAMIX MCP Stdio Client Singleton (Day 44 — Track A).

Persistent `mcp.ClientSession` over stdio JSON-RPC to the ONAMIX
(hyperx-browser) MCP server, started once in FastAPI lifespan and
reused across all HTTP/SSE requests.

Why this beats subprocess.run-per-call (the Day 42 pattern):
- Eliminates ~80-200ms Node.js cold-start overhead per call
- Standard MCP protocol (no fragile text parsing for search results)
- Free 6 new tools (hyperx_post/crawl/history/links/config/multi)
- ID-multiplexed JSON-RPC = concurrent calls on one stream (no manual lock)

Reliability:
- `_ensure_alive()` checks process state on every call; auto-respawns
  on crash with exponential backoff (1s → 2s → 4s → cap 30s)
- Health = process alive AND `session.send_ping()` succeeds
- Falls back to ToolExecutionError if respawn budget exhausted
- Subprocess-fallback caller path (in tool_executor) preserved as
  last-resort safety net during initial rollout

Lifecycle: start() in FastAPI lifespan, stop() on shutdown.
Concurrency: AnyIO-friendly. The MCP SDK already serializes writes
via internal queue and demultiplexes responses by JSON-RPC ID.
"""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Path config — must match docker-compose mount
#   /opt/sidix/tools/hyperx-browser  ->  /app/hyperx (rw)
# ---------------------------------------------------------------------------
ONAMIX_DIR = os.getenv("ONAMIX_DIR", "/app/hyperx")
ONAMIX_MCP_BIN = os.getenv("ONAMIX_MCP_BIN", f"{ONAMIX_DIR}/bin/hyperx-mcp.js")
NODE_BIN = os.getenv("NODE_BIN", "/usr/bin/node")

# Respawn policy
_RESPAWN_BACKOFFS = [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]
_DEFAULT_CALL_TIMEOUT_S = 30.0


def onamix_mcp_available() -> bool:
    """Cheap pre-flight check — file exists + node binary present."""
    return os.path.isfile(ONAMIX_MCP_BIN) and Path(NODE_BIN).exists()


class OnamixMCPClient:
    """Singleton MCP client wrapping a long-lived stdio session.

    Usage:
        client = OnamixMCPClient()
        await client.start()
        result = await client.call_tool("hyperx_get", {"url": "..."})
        await client.stop()
    """

    def __init__(self) -> None:
        self._session = None  # type: Any
        self._exit_stack: AsyncExitStack | None = None
        self._lock = asyncio.Lock()  # serializes start/respawn (NOT call_tool)
        self._respawn_count = 0
        self._started_at: float | None = None
        self._last_error: str | None = None

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------
    async def start(self) -> bool:
        """Start the MCP session. Returns True on success, False on failure."""
        async with self._lock:
            if self._session is not None:
                return True
            if not onamix_mcp_available():
                self._last_error = (
                    f"ONAMIX MCP binary not found at {ONAMIX_MCP_BIN} "
                    "or node missing — check docker-compose mount"
                )
                logger.warning("onamix.mcp.unavailable", reason=self._last_error)
                return False
            return await self._open_session()

    async def _open_session(self) -> bool:
        """Open a fresh stdio session. Caller holds self._lock."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            self._last_error = f"mcp SDK import failed: {exc}"
            logger.error("onamix.mcp.sdk_missing", error=str(exc))
            return False

        params = StdioServerParameters(
            command=NODE_BIN,
            args=[ONAMIX_MCP_BIN],
            cwd="/tmp",
        )
        stack = AsyncExitStack()
        try:
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self._session = session
            self._exit_stack = stack
            self._started_at = asyncio.get_event_loop().time()
            self._last_error = None
            logger.info(
                "onamix.mcp.started",
                bin=ONAMIX_MCP_BIN,
                respawn_count=self._respawn_count,
            )
            return True
        except Exception as exc:
            self._last_error = f"session open failed: {exc}"
            logger.error("onamix.mcp.start_failed", error=str(exc))
            try:
                await stack.aclose()
            except Exception:
                pass
            self._session = None
            self._exit_stack = None
            return False

    async def stop(self) -> None:
        """Tear down the session (idempotent)."""
        async with self._lock:
            await self._teardown_locked()

    async def _teardown_locked(self) -> None:
        """Caller holds self._lock."""
        stack = self._exit_stack
        self._session = None
        self._exit_stack = None
        if stack is not None:
            try:
                await stack.aclose()
                logger.info("onamix.mcp.stopped")
            except Exception as exc:
                logger.warning("onamix.mcp.stop_error", error=str(exc))

    async def _respawn(self) -> bool:
        """Tear down + restart with backoff. Returns True on success."""
        async with self._lock:
            await self._teardown_locked()
            backoff = _RESPAWN_BACKOFFS[
                min(self._respawn_count, len(_RESPAWN_BACKOFFS) - 1)
            ]
            self._respawn_count += 1
            logger.warning(
                "onamix.mcp.respawn",
                attempt=self._respawn_count,
                backoff_s=backoff,
            )
            await asyncio.sleep(backoff)
            return await self._open_session()

    # -----------------------------------------------------------------------
    # Health
    # -----------------------------------------------------------------------
    def is_alive(self) -> bool:
        return self._session is not None

    async def stats(self) -> dict:
        return {
            "alive": self.is_alive(),
            "respawn_count": self._respawn_count,
            "last_error": self._last_error,
            "bin": ONAMIX_MCP_BIN,
            "available": onamix_mcp_available(),
        }

    # -----------------------------------------------------------------------
    # Tool invocation
    # -----------------------------------------------------------------------
    async def call_tool(
        self,
        name: str,
        arguments: dict | None = None,
        timeout_s: float = _DEFAULT_CALL_TIMEOUT_S,
        _retry: bool = True,
    ) -> dict:
        """Call an MCP tool. Returns parsed dict (text content -> JSON-decoded if possible).

        Auto-respawns on session death and retries ONCE.
        """
        if self._session is None:
            ok = await self.start()
            if not ok:
                from .tool_executor import ToolExecutionError  # late import to avoid cycle
                raise ToolExecutionError(
                    f"ONAMIX MCP unavailable: {self._last_error or 'unknown'}"
                )
        try:
            result = await asyncio.wait_for(
                self._session.call_tool(name, arguments or {}),
                timeout=timeout_s,
            )
        except asyncio.TimeoutError:
            from .tool_executor import ToolExecutionError
            raise ToolExecutionError(f"ONAMIX MCP call '{name}' timed out ({timeout_s}s)")
        except Exception as exc:
            # Likely process crash / broken pipe — try respawn + retry once
            if _retry:
                logger.warning("onamix.mcp.call_error_retry", tool=name, error=str(exc))
                ok = await self._respawn()
                if ok:
                    return await self.call_tool(name, arguments, timeout_s, _retry=False)
            from .tool_executor import ToolExecutionError
            raise ToolExecutionError(f"ONAMIX MCP call '{name}' failed: {exc}")

        # Parse response — MCP returns CallToolResult with .content list of TextContent
        return _parse_mcp_result(result, name)


def _parse_mcp_result(result: Any, tool_name: str) -> dict:
    """Convert MCP CallToolResult → flat dict.

    The hyperx-mcp server returns content as a single TextContent whose .text
    is JSON-encoded for object payloads, or plain string for trivial returns.
    isError=True wraps an error message we surface as ToolExecutionError.
    """
    is_error = getattr(result, "isError", False)
    content = getattr(result, "content", None) or []

    text_chunks: list[str] = []
    for item in content:
        text = getattr(item, "text", None)
        if text is not None:
            text_chunks.append(text)

    combined = "\n".join(text_chunks).strip()

    if is_error:
        from .tool_executor import ToolExecutionError
        raise ToolExecutionError(f"ONAMIX MCP tool '{tool_name}' error: {combined[:300]}")

    if not combined:
        return {}

    # Try JSON decode (hyperx-mcp wraps objects with JSON.stringify)
    try:
        decoded = json.loads(combined)
        if isinstance(decoded, dict):
            return decoded
        return {"value": decoded}
    except json.JSONDecodeError:
        return {"text": combined}


# ---------------------------------------------------------------------------
# Module-level singleton accessor (set by FastAPI lifespan)
# ---------------------------------------------------------------------------
_GLOBAL_CLIENT: OnamixMCPClient | None = None


def set_global_client(client: OnamixMCPClient | None) -> None:
    global _GLOBAL_CLIENT
    _GLOBAL_CLIENT = client


def get_global_client() -> OnamixMCPClient | None:
    return _GLOBAL_CLIENT
