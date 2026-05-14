"""Tool organ package — refactored from monolithic tool_executor.py.

Each module is an organ that handles one category of skills:
  web      — search, read, wikipedia
  memory   — write, search (redis + qdrant)
  code     — python_repl with sandbox
  media    — image gen, image analysis, tts
  files    — read/write workspace sandbox
  onamix   — MCP browser automation suite
  exports  — pdf, slides generation
  registry — ollama tools spec builder

Import from here for backward compat:
  from services.tools import ToolContext, ToolExecutor, ToolExecutionError
"""

from .base import ToolContext, ToolExecutionError, ToolExecutor
from .registry import build_ollama_tools_spec

__all__ = [
    "ToolContext",
    "ToolExecutionError",
    "ToolExecutor",
    "build_ollama_tools_spec",
]
