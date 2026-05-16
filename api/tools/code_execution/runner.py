"""
Code Execution Runner — High-level API untuk Code Lab.
Wraps sandbox dengan retry, iteration, dan integration ke cognitive loop.

Usage:
    from tools.code_execution.runner import CodeRunner
    
    runner = CodeRunner()
    result = await runner.run("def sort(arr): return sorted(arr)", context={"intent": "test"})
    # result includes execution + scoring + lesson decision
"""

from __future__ import annotations

import time
from typing import Any, Optional

import structlog

from tools.code_execution.sandbox import CodeSandbox, ExecutionResult

logger = structlog.get_logger()


class CodeRunner:
    """High-level code execution with iteration and learning."""

    def __init__(self, max_retries: int = 2):
        self.sandbox = CodeSandbox()
        self.max_retries = max_retries

    async def run(
        self,
        code: str,
        language: str = "python",
        context: Optional[dict[str, Any]] = None,
        iterate_on_failure: bool = True,
    ) -> dict[str, Any]:
        """Run code with scoring and optional iteration.
        
        Args:
            code: Code to execute
            language: python, javascript, bash
            context: Execution context (intent, tenant_id, etc.)
            iterate_on_failure: If True, attempt fix on failure
        
        Returns:
            Dict with result, score, lesson, and iteration history
        """
        context = context or {}
        history = []
        
        for attempt in range(self.max_retries + 1):
            result = await self.sandbox.execute_with_scoring(code, language, context)
            
            history.append({
                "attempt": attempt + 1,
                "success": result.success,
                "score": result.score,
                "feeling": result.feeling,
                "error_type": result.error_type,
                "elapsed_ms": result.elapsed_ms,
            })
            
            if result.success:
                logger.info("code_runner.success", attempts=attempt + 1, score=result.score)
                return {
                    "result": result,
                    "history": history,
                    "iterations": attempt,
                    "final_success": True,
                }
            
            if not iterate_on_failure or attempt >= self.max_retries:
                break
            
            # Attempt auto-fix for simple errors
            if result.error_type == "syntax":
                code = await self._fix_syntax(code, result.stderr)
            elif result.error_type == "runtime":
                code = await self._fix_runtime(code, result.stderr)
            else:
                break  # Timeout — can't fix
        
        logger.info("code_runner.failure", attempts=len(history), final_error=result.error_type)
        return {
            "result": result,
            "history": history,
            "iterations": len(history) - 1,
            "final_success": False,
        }

    async def _fix_syntax(self, code: str, error: str) -> str:
        """Attempt simple syntax fixes."""
        # Common fixes
        if "IndentationError" in error:
            lines = code.split("\n")
            fixed = []
            for line in lines:
                stripped = line.lstrip()
                if stripped:
                    fixed.append("    " + stripped)
                else:
                    fixed.append(line)
            return "\n".join(fixed)
        
        if "unexpected EOF" in error:
            return code + "\n"
        
        return code

    async def _fix_runtime(self, code: str, error: str) -> str:
        """Attempt simple runtime fixes."""
        if "NameError" in error:
            # Add common imports
            imports = "import os\nimport sys\nimport json\n"
            return imports + code
        
        if "ModuleNotFoundError" in error:
            # Try to install or mock
            return code
        
        return code

    async def run_and_learn(
        self,
        code: str,
        language: str = "python",
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Run code, capture lesson, and save to memory if meaningful."""
        run_result = await self.run(code, language, context)
        
        # Extract lesson from code_lab scoring
        from services.code_lab import enrich_execution
        enriched = enrich_execution(
            code=code,
            success=run_result["result"].success,
            elapsed_ms=run_result["result"].elapsed_ms,
            stdout=run_result["result"].stdout,
            stderr=run_result["result"].stderr,
            exit_code=run_result["result"].exit_code,
            context=context,
        )
        
        lesson = enriched.get("lesson")
        
        # Save to memory if lesson is meaningful
        if lesson and lesson.get("save"):
            try:
                from services.memory import memory_write
                bucket = lesson.get("bucket", "hikmah")
                await memory_write(
                    namespace="code_lab",
                    key=f"lesson_{int(time.time())}",
                    value=lesson.get("summary", ""),
                    bucket=bucket,
                )
                logger.info("code_runner.lesson_saved", bucket=bucket)
            except Exception as exc:
                logger.warning("code_runner.lesson_save_failed", error=str(exc))
        
        return {
            **run_result,
            "lesson": lesson,
        }
