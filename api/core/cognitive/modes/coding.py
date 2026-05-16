"""
CODING — Code Generation & Debugging
======================================
Untuk: Software development, debugging, code review, algorithm design
"""

from __future__ import annotations

from typing import Any

from core.cognitive.modes.base import BaseMode, ThinkingResult


class CodingMode(BaseMode):
    """Mode untuk programming, debugging, dan code generation."""

    name = "coding"
    description = "Code generation, execution, debugging, testing"

    INSTRUCTIONS = """[MODE: CODING]
Solid software engineering. Pola: DESIGN API → IMPLEMENT → HANDLE errors/edge cases → TEST → EXECUTE → ITERATE.
Rules: (1) Readable + tested + type hints, (2) Handle edge cases, (3) Jangan hardcode config values, (4) Complexity analysis, (5) Error → trace step-by-step.
Code Lab: Execute via run_python → verify → iterate → save pattern.
Format: 📝 Design | 💻 Code | 🧪 Tests | 📊 Result | 🔍 Complexity"""

    async def think(self, user_input: str, context: dict[str, Any]) -> ThinkingResult:
        # Detect if this is a debugging request
        is_debug = any(kw in user_input.lower() for kw in ["error", "bug", "fix", "debug", "traceback"])
        
        prompt = self._build_prompt(user_input, context, self.INSTRUCTIONS)
        
        return ThinkingResult(
            mode=self.name,
            reasoning=f"Mode coding activated. Debug: {is_debug}",
            output=prompt,
            confidence=0.9,
            metadata={
                "prompt_type": "coding",
                "is_debugging": is_debug,
                "language": context.get("language", "python"),
                "use_code_lab": True,
            },
        )
