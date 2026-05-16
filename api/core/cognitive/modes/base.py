"""
Base class untuk semua thinking modes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ThinkingResult:
    """Hasil dari thinking mode."""
    mode: str = ""
    reasoning: str = ""
    output: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseMode(ABC):
    """Base class untuk semua thinking modes."""

    name: str = "base"
    description: str = ""

    @abstractmethod
    async def think(self, user_input: str, context: dict[str, Any]) -> ThinkingResult:
        """Process user input and return thinking result."""
        pass

    def _build_prompt(self, user_input: str, context: dict[str, Any], instructions: str) -> str:
        """Build system prompt dengan thinking instructions."""
        parts = [
            f"[THINKING MODE: {self.name.upper()}]",
            instructions,
            "",
            f"User input: {user_input}",
        ]
        
        if context.get("conversation_history"):
            parts.append(f"\nContext: {context['conversation_history']}")
        
        if context.get("memory_summary"):
            parts.append(f"\nMemory: {context['memory_summary']}")
        
        return "\n".join(parts)
