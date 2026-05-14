"""Code organ — Python REPL with subprocess sandbox."""

import asyncio
import time
from typing import Any

import structlog

from services.tool_policy import validate_python_code, PolicyViolation
from .base import ToolContext, ToolExecutionError

logger = structlog.get_logger()


async def _python_repl(args: dict, ctx: ToolContext) -> dict:
    """Execute Python code via subprocess — real process isolation."""
    import subprocess

    code = args.get("code", "").strip()
    timeout = min(int(args.get("timeout", 30)), 30)

    if not code:
        raise ToolExecutionError("'code' is required")

    try:
        validate_python_code(code)
    except PolicyViolation as exc:
        logger.warning("tool.python_repl.policy_violation", reason=exc.reason, agent=ctx.agent_id)
        raise ToolExecutionError(f"Security policy violation: {exc.reason}") from exc

    started_at = time.time()
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
        elapsed_ms = int((time.time() - started_at) * 1000)
        stdout = (result.stdout or "")[:2000]
        stderr = (result.stderr or "")[:500]
        success = result.returncode == 0
        exit_code = result.returncode
    except asyncio.TimeoutError:
        elapsed_ms = int((time.time() - started_at) * 1000)
        stdout, stderr, success, exit_code = "", f"Timed out after {timeout}s", False, -1
    except FileNotFoundError:
        elapsed_ms = int((time.time() - started_at) * 1000)
        stdout, stderr, success, exit_code = "", "Python interpreter not found", False, -1
    except Exception as exc:
        elapsed_ms = int((time.time() - started_at) * 1000)
        stdout, stderr, success, exit_code = "", str(exc), False, -1

    # Enrich with Code Lab scoring + adaptive lesson capture
    try:
        from services.code_lab import enrich_execution
        enrichment = enrich_execution(
            code=code,
            success=success,
            elapsed_ms=elapsed_ms,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            context={"agent_id": ctx.agent_id, "tenant_id": ctx.tenant_id},
        )
    except Exception as exc:
        logger.warning("tool.python_repl.scoring_failed", error=str(exc))
        enrichment = {"score": None, "lesson": None}

    lesson_meta = enrichment.get("lesson")
    if lesson_meta and lesson_meta.get("save"):
        try:
            from services.memory import memory_write as kv_write
            bucket = lesson_meta["bucket"]
            key = f"codelab_{int(time.time())}_{hash(code) & 0xFFFFFFFF:08x}"
            await kv_write(
                tenant_id=ctx.tenant_id,
                agent_id=ctx.agent_id,
                key=key,
                value=lesson_meta["summary"],
                namespace=bucket,
                ttl_days=90,
            )
            logger.info("tool.python_repl.lesson_saved", bucket=bucket, key=key, agent=ctx.agent_id)
        except Exception as exc:
            logger.warning("tool.python_repl.lesson_save_failed", error=str(exc))

    logger.info("tool.python_repl", rc=exit_code, agent=ctx.agent_id,
                elapsed_ms=elapsed_ms,
                score=(enrichment.get("score") or {}).get("score"),
                feeling=(enrichment.get("score") or {}).get("feeling"))

    return {
        "output": stdout,
        "error": stderr if stderr else None,
        "return_code": exit_code,
        "success": success,
        "elapsed_ms": elapsed_ms,
        "score": enrichment.get("score"),
        "lesson_saved": bool(lesson_meta and lesson_meta.get("save")),
    }


HANDLERS: dict[str, Any] = {
    "python_repl": _python_repl,
}
