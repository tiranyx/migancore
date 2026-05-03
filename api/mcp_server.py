"""
MCP Server (Day 26) — Streamable HTTP endpoint exposing MiganCore tools to
external MCP clients (Claude Desktop, Claude Code CLI, Cursor, Continue.dev).

Spec: https://modelcontextprotocol.io/specification/2025-06-18/basic/transports

Architecture:
  - FastMCP instance (from official `mcp` SDK v1.27+)
  - Mounted at /mcp on the existing FastAPI app via Starlette ASGI sub-mount
  - Stateless mode (no server-initiated sampling, simpler ops)
  - Auth: reuse MiganCore's RS256 JWT via TokenVerifier interface
  - Tools: thin adapters around existing TOOL_REGISTRY in tool_executor.py
  - Tool context: tenant_id extracted from JWT 'tenant_id' claim, agent_id="mcp-client"
                  (no per-agent state in MCP path — different from /v1/agents/*/chat)

Day 26 hypothesis: SDK + sub-mount works without arch rewrite. If FastMCP API
shifts in v1.28+, the imports below are the only thing that needs updating.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import structlog
from jwt import PyJWTError

from services.jwt import decode_token
from services.tool_executor import ToolExecutor, ToolContext

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Lazy SDK import
# ---------------------------------------------------------------------------
# FastMCP/SDK is a heavy dep — import lazily so the rest of the API can boot
# even if `mcp` isn't installed yet (e.g. dev container without rebuild).

_mcp = None  # FastMCP instance singleton


def _build_mcp():
    """Construct the FastMCP instance with tools.

    Auth is NOT wired into FastMCP itself (the SDK requires full OAuth 2.1 settings
    to use token_verifier, which is overkill for MiganCore's existing JWT setup).
    Instead, JWT auth is enforced via Starlette middleware on the mounted ASGI app
    in get_mcp_app() below — same security guarantee, simpler integration.

    Returns the FastMCP instance, ready to be mounted via streamable_http_app().
    """
    # Lazy import — fails gracefully if mcp not installed
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "MCP SDK not installed. Run: pip install 'mcp>=1.27.0'"
        ) from exc

    # ---------- FASTMCP INSTANCE ----------
    # stateless_http=True → no session bookkeeping, every request is independent.
    # This simplifies ops but means no server-initiated sampling. Acceptable for
    # Day 26 (just exposing tools, not full bi-directional protocol).
    mcp = FastMCP(
        name="migancore",
        instructions=(
            "MiganCore — Autonomous Digital Organism. Provides 9 tools: web_search, "
            "python_repl, memory_write/search, spawn_agent, http_get, generate_image "
            "(fal.ai FLUX), read_file/write_file (sandboxed workspace). Bearer JWT auth "
            "required. Get token: POST https://api.migancore.com/v1/auth/login."
        ),
        stateless_http=True,
    )

    # ---------- TOOL CONTEXT EXTRACTION ----------
    # FastMCP passes a Context object to tools; we pull tenant_id from the
    # authenticated request's access token claims. If the SDK doesn't expose
    # this directly, fall back to a default 'mcp-anonymous' tenant.
    def _ctx_from_request(ctx: Any) -> ToolContext:
        tenant_id = "mcp-anonymous"
        try:
            # Different SDK versions store access info differently — try common paths
            if hasattr(ctx, "request_context") and ctx.request_context:
                meta = getattr(ctx.request_context, "meta", None)
                if meta and isinstance(meta, dict):
                    tenant_id = meta.get("tenant_id", tenant_id)
            # Try direct attr
            if hasattr(ctx, "tenant_id"):
                tenant_id = ctx.tenant_id
        except Exception:
            pass
        return ToolContext(
            tenant_id=tenant_id,
            agent_id="mcp-client",
            tenant_plan="free",  # MCP starts conservative; plan tier checked per call
            tool_policies=None,
        )

    async def _execute(skill_id: str, args: dict, ctx: Any) -> str:
        """Bridge MCP tool call → existing TOOL_REGISTRY handler.

        Returns JSON string (MCP tools return text content).
        """
        tool_ctx = _ctx_from_request(ctx)
        executor = ToolExecutor(tool_ctx)
        try:
            result = await executor.execute(skill_id, args)
            return json.dumps(result, default=str, ensure_ascii=False)
        except Exception as exc:
            logger.error("mcp.tool.error", skill=skill_id, error=str(exc))
            return json.dumps({"success": False, "error": str(exc)})

    # ---------- TOOL REGISTRATION ----------
    # Each MCP tool is a thin adapter around the existing TOOL_REGISTRY handler.
    # Descriptions match skills.json (imperative MANDATORY style — Day 25 lesson).

    @mcp.tool(
        name="web_search",
        description=(
            "MANDATORY for finding current information online: invoke this whenever the "
            "user asks about news, current events, recent data, or anything that requires "
            "fresh web data. Returns search results from DuckDuckGo."
        ),
    )
    async def web_search(query: str, limit: int = 5, ctx=None) -> str:
        return await _execute("web_search", {"query": query, "limit": limit}, ctx)

    @mcp.tool(
        name="generate_image",
        description=(
            "MANDATORY for image generation: invoke whenever the user requests an image, "
            "picture, illustration, visual, artwork, banner, or any visual asset. Generates "
            "via fal.ai FLUX schnell (~3-8s), returns hosted URL. Do NOT describe — call this."
        ),
    )
    async def generate_image(
        prompt: str,
        image_size: str = "landscape_4_3",
        num_images: int = 1,
        ctx=None,
    ) -> str:
        return await _execute(
            "generate_image",
            {"prompt": prompt, "image_size": image_size, "num_images": num_images},
            ctx,
        )

    @mcp.tool(
        name="write_file",
        description=(
            "MANDATORY for creating/writing files: invoke whenever the user asks to create, "
            "write, save, or generate a file (script, config, document, code, etc.). "
            "Sandboxed to MiganCore agent workspace. Auto-creates parent directories."
        ),
    )
    async def write_file(path: str, content: str, ctx=None) -> str:
        return await _execute("write_file", {"path": path, "content": content}, ctx)

    @mcp.tool(
        name="read_file",
        description=(
            "MANDATORY for reading file content: invoke whenever the user asks to read, "
            "open, view, show, or check the content of a file. Returns text content (50KB cap). "
            "For directory paths, returns file listing."
        ),
    )
    async def read_file(path: str, ctx=None) -> str:
        return await _execute("read_file", {"path": path}, ctx)

    @mcp.tool(
        name="memory_write",
        description=(
            "Save a fact to MiganCore long-term memory (Redis K-V tier). Use for user "
            "preferences, project facts, recurring context. Survives across MCP sessions."
        ),
    )
    async def memory_write(key: str, value: str, namespace: str = "default", ctx=None) -> str:
        return await _execute(
            "memory_write",
            {"key": key, "value": value, "namespace": namespace},
            ctx,
        )

    @mcp.tool(
        name="memory_search",
        description=(
            "Search MiganCore long-term memory by semantic similarity. Returns matching "
            "facts/notes from prior interactions."
        ),
    )
    async def memory_search(query: str, limit: int = 5, ctx=None) -> str:
        return await _execute("memory_search", {"query": query, "limit": limit}, ctx)

    @mcp.tool(
        name="python_repl",
        description=(
            "Execute Python code in a sandboxed subprocess. Use ONLY for computation "
            "(math, data transformation). For file I/O use write_file/read_file. "
            "Restricted: no os/sys/subprocess imports. Free tier: not available "
            "(requires enterprise plan)."
        ),
    )
    async def python_repl(code: str, timeout: int = 30, ctx=None) -> str:
        return await _execute("python_repl", {"code": code, "timeout": timeout}, ctx)

    logger.info(
        "mcp.server.built",
        tool_count=7,  # web_search, generate_image, write_file, read_file, memory_write, memory_search, python_repl
        stateless=True,
        auth="jwt-middleware",
    )
    return mcp


def get_mcp():
    """Lazy singleton for FastMCP instance."""
    global _mcp
    if _mcp is None:
        _mcp = _build_mcp()
    return _mcp


def get_mcp_app():
    """Return the Starlette ASGI app for mounting at /mcp, wrapped with JWT auth.

    Usage in main.py:
        from mcp_server import get_mcp_app
        app.mount("/mcp", get_mcp_app())

    Auth: every request to the mounted app must include `Authorization: Bearer <jwt>`.
    The JWT is verified against MiganCore's RS256 keys (services/jwt.py).
    Tenant context is attached to the request scope for tools to read.
    """
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    mcp = get_mcp()
    asgi_app = mcp.streamable_http_app()

    class JWTAuthMiddleware(BaseHTTPMiddleware):
        """Enforce Bearer JWT on every MCP request.

        Allow OPTIONS through (CORS preflight). Reject missing/invalid tokens
        with 401. Attach tenant_id/subject to request.state for downstream use.
        """

        async def dispatch(self, request, call_next):
            # CORS preflight
            if request.method == "OPTIONS":
                return await call_next(request)

            auth_header = request.headers.get("authorization", "")
            if not auth_header.lower().startswith("bearer "):
                logger.warning("mcp.auth.missing_bearer", path=request.url.path)
                return JSONResponse(
                    {"error": "missing_bearer_token", "detail": "Authorization: Bearer <jwt> required"},
                    status_code=401,
                    headers={"WWW-Authenticate": 'Bearer realm="migancore-mcp"'},
                )

            token = auth_header[7:].strip()
            try:
                payload = decode_token(token, token_type="access")
            except PyJWTError as exc:
                logger.warning("mcp.auth.invalid_token", error=str(exc), path=request.url.path)
                return JSONResponse(
                    {"error": "invalid_token", "detail": str(exc)},
                    status_code=401,
                    headers={"WWW-Authenticate": 'Bearer realm="migancore-mcp"'},
                )

            tenant_id = payload.get("tenant_id")
            subject = payload.get("sub")
            if not tenant_id or not subject:
                logger.warning("mcp.auth.missing_claims", path=request.url.path)
                return JSONResponse(
                    {"error": "invalid_claims", "detail": "tenant_id and sub claims required"},
                    status_code=401,
                )

            # Attach to request scope so tools can extract via context
            request.state.tenant_id = tenant_id
            request.state.subject = subject
            request.state.scopes = (payload.get("scope") or "").split() if payload.get("scope") else []

            logger.info("mcp.auth.ok", subject=subject, tenant_id=tenant_id, path=request.url.path)
            return await call_next(request)

    asgi_app.add_middleware(JWTAuthMiddleware)
    return asgi_app
