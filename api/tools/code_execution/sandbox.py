"""
ORGAN — Code Execution Sandbox
================================
Pyodide-based sandbox for safe Python code execution.
Primary: Pyodide (WASM) for 95% Python tasks
Fallback: subprocess isolation for non-Python or C-ext needs

Usage:
    from tools.code_execution.sandbox import CodeSandbox
    
    sandbox = CodeSandbox()
    result = await sandbox.execute("print('Hello')", language="python")
    # result.success, result.stdout, result.stderr, result.elapsed_ms, result.score
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool = False
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    elapsed_ms: int = 0
    memory_kb: int = 0
    sandbox: str = "unknown"  # pyodide, docker, subprocess
    language: str = "python"
    code: str = ""
    
    # Scoring fields (populated by code_lab)
    score: float = 0.0
    feeling: str = ""
    error_type: Optional[str] = None


class CodeSandbox:
    """Safe code execution sandbox."""

    def __init__(
        self,
        timeout_s: int = 30,
        memory_limit_mb: int = 512,
        pyodide_path: Optional[str] = None,
    ):
        self.timeout_s = timeout_s
        self.memory_limit_mb = memory_limit_mb
        self.pyodide_path = pyodide_path or "/opt/migancore/codelab/pyodide_runner.js"
        self._pyodide_available = None  # lazy check

    async def _check_pyodide(self) -> bool:
        """Check if pyodide-node is available."""
        if self._pyodide_available is not None:
            return self._pyodide_available
        try:
            proc = await asyncio.create_subprocess_exec(
                "node", "-e", "require('pyodide'); console.log('ok')",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            self._pyodide_available = b"ok" in stdout
        except Exception:
            self._pyodide_available = False
        logger.info("sandbox.pyodide_check", available=self._pyodide_available)
        return self._pyodide_available

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout_s: Optional[int] = None,
        sandbox: str = "auto",  # auto, pyodide, subprocess
    ) -> ExecutionResult:
        """Execute code in sandbox.
        
        Args:
            code: Code to execute
            language: python, javascript, bash
            timeout_s: Override default timeout
            sandbox: auto (pick best), pyodide, subprocess
        
        Returns:
            ExecutionResult with output, timing, and status
        """
        timeout = timeout_s or self.timeout_s
        
        if sandbox == "auto":
            if language == "python" and await self._check_pyodide():
                sandbox = "pyodide"
            else:
                sandbox = "subprocess"
        
        if sandbox == "pyodide" and language == "python":
            return await self._run_pyodide(code, timeout)
        
        return await self._run_subprocess(code, language, timeout)

    async def _run_pyodide(self, code: str, timeout_s: int) -> ExecutionResult:
        """Execute Python via Pyodide (Node.js subprocess)."""
        start = time.time()
        
        # Ensure runner script exists
        runner_path = Path(self.pyodide_path)
        if not runner_path.exists():
            # Create minimal runner
            runner_path.parent.mkdir(parents=True, exist_ok=True)
            runner_path.write_text(PYODIDE_RUNNER_JS, encoding="utf-8")
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "node", str(runner_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=code.encode("utf-8")),
                    timeout=timeout_s,
                )
            except asyncio.TimeoutError:
                proc.kill()
                elapsed = int((time.time() - start) * 1000)
                return ExecutionResult(
                    success=False,
                    stderr="TIMEOUT: Execution exceeded {timeout_s}s".format(timeout_s=timeout_s),
                    exit_code=-1,
                    elapsed_ms=elapsed,
                    sandbox="pyodide",
                    code=code,
                    error_type="timeout",
                )
            
            elapsed = int((time.time() - start) * 1000)
            
            # Parse JSON output from runner
            try:
                result_data = json.loads(stdout.decode("utf-8").strip().split("\n")[-1])
                return ExecutionResult(
                    success=result_data.get("success", False),
                    stdout=result_data.get("stdout", ""),
                    stderr=result_data.get("stderr", "") or stderr.decode("utf-8"),
                    exit_code=0 if result_data.get("success") else 1,
                    elapsed_ms=elapsed,
                    sandbox="pyodide",
                    code=code,
                )
            except json.JSONDecodeError:
                # Runner didn't output JSON — return raw
                return ExecutionResult(
                    success=proc.returncode == 0,
                    stdout=stdout.decode("utf-8"),
                    stderr=stderr.decode("utf-8"),
                    exit_code=proc.returncode or 0,
                    elapsed_ms=elapsed,
                    sandbox="pyodide",
                    code=code,
                )
        
        except Exception as exc:
            elapsed = int((time.time() - start) * 1000)
            logger.error("sandbox.pyodide_error", error=str(exc))
            return ExecutionResult(
                success=False,
                stderr=f"Pyodide error: {exc}",
                exit_code=-1,
                elapsed_ms=elapsed,
                sandbox="pyodide",
                code=code,
                error_type="runtime",
            )

    async def _run_subprocess(self, code: str, language: str, timeout_s: int) -> ExecutionResult:
        """Execute code via subprocess isolation."""
        start = time.time()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            if language == "python":
                script_path = Path(tmpdir) / "script.py"
                script_path.write_text(code, encoding="utf-8")
                cmd = [sys.executable, str(script_path)]
            elif language == "javascript":
                script_path = Path(tmpdir) / "script.js"
                script_path.write_text(code, encoding="utf-8")
                cmd = ["node", str(script_path)]
            elif language == "bash":
                script_path = Path(tmpdir) / "script.sh"
                script_path.write_text(code, encoding="utf-8")
                cmd = ["bash", str(script_path)]
            else:
                return ExecutionResult(
                    success=False,
                    stderr=f"Unsupported language: {language}",
                    exit_code=-1,
                    sandbox="subprocess",
                    code=code,
                )
            
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmpdir,
                    # Security: restrict environment
                    env={"PATH": os.environ.get("PATH", ""), "HOME": tmpdir, "TMPDIR": tmpdir},
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=timeout_s,
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    elapsed = int((time.time() - start) * 1000)
                    return ExecutionResult(
                        success=False,
                        stderr=f"TIMEOUT: Execution exceeded {timeout_s}s",
                        exit_code=-1,
                        elapsed_ms=elapsed,
                        sandbox="subprocess",
                        code=code,
                        error_type="timeout",
                    )
                
                elapsed = int((time.time() - start) * 1000)
                return ExecutionResult(
                    success=proc.returncode == 0,
                    stdout=stdout.decode("utf-8", errors="replace"),
                    stderr=stderr.decode("utf-8", errors="replace"),
                    exit_code=proc.returncode or 0,
                    elapsed_ms=elapsed,
                    sandbox="subprocess",
                    code=code,
                )
            
            except Exception as exc:
                elapsed = int((time.time() - start) * 1000)
                logger.error("sandbox.subprocess_error", error=str(exc))
                return ExecutionResult(
                    success=False,
                    stderr=f"Subprocess error: {exc}",
                    exit_code=-1,
                    elapsed_ms=elapsed,
                    sandbox="subprocess",
                    code=code,
                    error_type="runtime",
                )

    async def execute_with_scoring(
        self,
        code: str,
        language: str = "python",
        context: Optional[dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Execute code and enrich with scoring (rasa sakit/senang)."""
        from services.code_lab import enrich_execution
        
        result = await self.execute(code, language)
        enriched = enrich_execution(
            code=code,
            success=result.success,
            elapsed_ms=result.elapsed_ms,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            context=context,
        )
        
        result.score = enriched["score"]["score"]
        result.feeling = enriched["score"]["feeling"]
        result.error_type = enriched["score"].get("error_type")
        
        # Publish event
        try:
            from core.event_bus import event_bus
            await event_bus.code_executed(
                execution_id=f"exec_{int(time.time()*1000)}",
                tenant_id=(context or {}).get("tenant_id", "unknown"),
                success=result.success,
                score=result.score,
                feeling=result.feeling,
                error_type=result.error_type,
                elapsed_ms=result.elapsed_ms,
                code_length=len(code),
                lesson_saved=enriched.get("lesson", {}).get("save", False) if enriched.get("lesson") else False,
                lesson_bucket=enriched.get("lesson", {}).get("bucket") if enriched.get("lesson") else None,
            )
        except Exception:
            pass  # Event bus failure should not break execution
        
        return result


# Minimal Pyodide runner script (created on-demand if not present)
PYODIDE_RUNNER_JS = '''
const { loadPyodide } = require("pyodide");

(async () => {
    try {
        const pyodide = await loadPyodide({
            stdout: (text) => process.stdout.write(text),
            stderr: (text) => process.stderr.write(text),
        });
        
        let code = "";
        process.stdin.setEncoding("utf8");
        for await (const chunk of process.stdin) {
            code += chunk;
        }
        
        const t0 = Date.now();
        try {
            const result = await pyodide.runPythonAsync(code);
            console.log(JSON.stringify({
                success: true,
                stdout: String(result || ""),
                stderr: "",
                elapsed_ms: Date.now() - t0,
            }));
        } catch (err) {
            console.log(JSON.stringify({
                success: false,
                stdout: "",
                stderr: err.message || String(err),
                elapsed_ms: Date.now() - t0,
            }));
        }
    } catch (setupErr) {
        console.log(JSON.stringify({
            success: false,
            stdout: "",
            stderr: "Pyodide setup failed: " + (setupErr.message || String(setupErr)),
            elapsed_ms: 0,
        }));
    }
})();
'''
