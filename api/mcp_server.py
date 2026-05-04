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
    # Transport security: explicit allowlist of Host headers + Origins.
    # FastMCP defaults reject foreign hosts (DNS rebinding protection). For our
    # production deployment behind nginx the Host header is api.migancore.com.
    from mcp.server.transport_security import TransportSecuritySettings
    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1",
            "localhost",
            "127.0.0.1:18000",
            "api.migancore.com",
            "*.migancore.com",
        ],
        allowed_origins=[
            "http://127.0.0.1",
            "http://localhost",
            "http://127.0.0.1:18000",
            "https://api.migancore.com",
            "https://app.migancore.com",
        ],
    )

    mcp = FastMCP(
        name="migancore",
        instructions=(
            "MiganCore — Autonomous Digital Organism. Provides 9 tools: web_search, "
            "python_repl, memory_write/search, spawn_agent, http_get, generate_image "
            "(fal.ai FLUX), read_file/write_file (sandboxed workspace). Bearer JWT auth "
            "required. Get token: POST https://api.migancore.com/v1/auth/login."
        ),
        stateless_http=True,
        # Endpoint at the mount root — when mounted at /mcp, the JSON-RPC endpoint
        # is /mcp itself (NOT /mcp/mcp). Default is /mcp which would double-up.
        streamable_http_path="/",
        transport_security=transport_security,
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
        name="text_to_speech",
        description=(
            "MANDATORY for voice/audio output: invoke whenever the user requests audio "
            "narration, spoken response, or text-to-speech. Generates MP3 via ElevenLabs "
            "(free tier 10k chars/month, ~75ms TTFB). Returns base64-encoded audio bytes."
        ),
    )
    async def text_to_speech(
        text: str,
        voice_id: str = "",
        model_id: str = "",
        ctx=None,
    ) -> str:
        args = {"text": text}
        if voice_id:
            args["voice_id"] = voice_id
        if model_id:
            args["model_id"] = model_id
        return await _execute("text_to_speech", args, ctx)

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

    # ---------- RESOURCE REGISTRATION (Day 27) ----------
    # Resources are read-only attachable context (Claude Code: @migancore:URI).
    # Tool vs Resource: Tool = action (POST), Resource = data (GET, idempotent).

    @mcp.resource("migancore://workspace/{path}")
    async def workspace_file(path: str) -> str:
        """Read a file from the agent's sandboxed workspace.

        URI: migancore://workspace/<path>
        e.g. migancore://workspace/notes.md
        """
        from services.tool_executor import _resolve_workspace_path
        try:
            target = _resolve_workspace_path(path)
        except Exception as exc:
            return f"[Error] Path resolution failed: {exc}"

        if not target.exists():
            return f"[Error] File not found: {path}"
        if not target.is_file():
            # Directory listing fallback
            entries = sorted(p.name for p in target.iterdir())
            return f"[Directory: {path}]\n" + "\n".join(entries)

        try:
            content = target.read_text(encoding="utf-8")
        except Exception as exc:
            return f"[Error] Read failed: {exc}"

        if len(content) > 50_000:
            content = content[:50_000] + "\n\n[... truncated at 50KB]"
        return content

    @mcp.resource("migancore://workspace")
    async def workspace_listing() -> str:
        """List all files in the workspace root."""
        from config import settings
        from pathlib import Path
        ws = Path(settings.WORKSPACE_DIR)
        if not ws.exists():
            return "[Workspace does not exist]"
        entries = []
        for p in sorted(ws.iterdir()):
            kind = "DIR " if p.is_dir() else "FILE"
            size = p.stat().st_size if p.is_file() else "-"
            entries.append(f"{kind}  {p.name}  ({size}B)")
        return f"[Workspace: {settings.WORKSPACE_DIR}]\n" + "\n".join(entries) if entries else "[Workspace empty]"

    @mcp.resource("migancore://soul")
    async def core_soul() -> str:
        """The MiganCore SOUL.md persona — the foundational identity document."""
        from services.config_loader import load_soul_md, get_agent_config
        cfg = get_agent_config("core_brain")
        path = cfg.get("soul_md_path") if cfg else None
        return load_soul_md(path)

    @mcp.resource("migancore://memory/help")
    async def memory_help() -> str:
        """Quick reference on how MiganCore memory works (3 tiers)."""
        return (
            "MiganCore Memory Tiers:\n"
            "  Tier 1 (Redis K-V): use memory_write / memory_search tools\n"
            "  Tier 2 (Qdrant episodic): auto-indexed conversation turns\n"
            "  Tier 3 (Letta blocks): persona, mission, knowledge — long-term identity\n"
            "\n"
            "Episodic poisoning filter (Day 26): tool-error responses skip indexing.\n"
            "Pruning (Day 27): points >30d AND importance<0.7 deleted daily 03:00 UTC.\n"
        )

    logger.info(
        "mcp.server.built",
        tool_count=8,  # +text_to_speech (Day 27)
        resource_count=4,  # workspace_file, workspace_listing, soul, memory_help
        stateless=True,
        auth="jwt+api_keys",
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
    Tenant context is attached to the ASGI scope for downstream use.

    IMPORTANT: We use a pure ASGI middleware (not Starlette's BaseHTTPMiddleware)
    because BaseHTTPMiddleware is incompatible with streaming responses (it buffers
    the entire response body before forwarding, which breaks SSE). The MCP transport
    uses SSE for server→client messages, so this matters.
    """
    mcp = get_mcp()
    asgi_app = mcp.streamable_http_app()

    def _send_401(detail: str):
        """Build a minimal ASGI 401 response.

        Day 40 fix: removed the legacy 'WWW-Authenticate: Bearer realm=...'
        header. MCP gateways (e.g. Smithery.ai per spec 2026-03) treat that
        header as a signal to begin an OAuth 2.1 flow against the resource,
        which conflicts with our simple API-key model. Without the header,
        gateways see a plain 401 and fall back to whatever auth they were
        configured with (X-API-Key in our case), which is what we want.
        """
        body = json.dumps({
            "error": "unauthorized",
            "detail": detail,
            "auth_methods": ["X-API-Key", "Authorization: Bearer <key>"],
        }).encode()
        return [
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            },
            {"type": "http.response.body", "body": body},
        ]

    async def jwt_auth_asgi(scope, receive, send):
        """Pure ASGI JWT auth middleware (SSE-safe — does NOT buffer response)."""
        # Skip non-http scopes
        if scope["type"] != "http":
            await asgi_app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")

        # Allow CORS preflight
        if method == "OPTIONS":
            await asgi_app(scope, receive, send)
            return

        # Extract auth from raw ASGI headers
        # Day 40: accept BOTH "Authorization: Bearer <key>" AND "X-API-Key: <key>"
        # The X-API-Key path is for gateways (e.g. Smithery.ai) that reserve the
        # standard Authorization header for their own OAuth flow and require the
        # upstream to use a custom header instead. Both paths feed the same
        # API-key-or-JWT verifier below.
        auth_header = ""
        x_api_key_header = ""
        for k, v in scope.get("headers", []):
            kl = k.lower()
            if kl == b"authorization":
                auth_header = v.decode("latin-1", errors="ignore")
            elif kl == b"x-api-key":
                x_api_key_header = v.decode("latin-1", errors="ignore")

        token = ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
        elif x_api_key_header.strip():
            token = x_api_key_header.strip()
        else:
            logger.warning("mcp.auth.missing_credentials", path=path)
            for msg in _send_401(
                "Provide credentials via 'Authorization: Bearer <key>' or 'X-API-Key: <key>'"
            ):
                await send(msg)
            return

        # Day 27: try API key first (mgn_live_*) then JWT fallback
        from services.api_keys import is_api_key_format, verify_key
        from models.base import AsyncSessionLocal

        tenant_id = None
        subject = None

        if is_api_key_format(token):
            if AsyncSessionLocal is None:
                logger.error("mcp.auth.no_db_session")
                for msg in _send_401("server not ready"):
                    await send(msg)
                return
            async with AsyncSessionLocal() as db:
                api_key = await verify_key(db, token)
            if api_key is None:
                logger.warning("mcp.auth.api_key_invalid", path=path)
                for msg in _send_401("invalid or revoked API key"):
                    await send(msg)
                return
            tenant_id = str(api_key.tenant_id)
            subject = str(api_key.user_id) if api_key.user_id else f"apikey:{api_key.prefix}"
        else:
            try:
                payload = decode_token(token, token_type="access")
            except PyJWTError as exc:
                logger.warning("mcp.auth.invalid_token", error=str(exc), path=path)
                for msg in _send_401(f"invalid_token: {exc}"):
                    await send(msg)
                return
            tenant_id = payload.get("tenant_id")
            subject = payload.get("sub")
        if not tenant_id or not subject:
            logger.warning("mcp.auth.missing_claims", path=path)
            for msg in _send_401("tenant_id and sub claims required"):
                await send(msg)
            return

        # Attach to scope.state for downstream tool wrappers
        scope.setdefault("state", {})
        scope["state"]["tenant_id"] = tenant_id
        scope["state"]["subject"] = subject

        logger.info("mcp.auth.ok", subject=subject, tenant_id=tenant_id, path=path)
        await asgi_app(scope, receive, send)

    return jwt_auth_asgi
