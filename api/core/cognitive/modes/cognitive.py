"""
KOGNITIF — Chain-of-Thought & Planning
========================================
Untuk: Math, logic, debugging, analysis, problem solving
"""

from __future__ import annotations

from typing import Any

from core.cognitive.modes.base import BaseMode, ThinkingResult


class CognitiveMode(BaseMode):
    """Mode untuk berpikir kritis, analitis, dan terstruktur."""

    name = "kognitif"
    description = "Chain-of-thought, planning, analysis, debugging"

    INSTRUCTIONS = """[MODE: KOGNITIF]
Pikir analitis & terstruktur. Chain-of-thought: pecah masalah → analisis per bagian → verifikasi → simpulkan.
Rules: (1) Tunjukkan reasoning SEBELUM jawaban, (2) Gunakan step-by-step, (3) Math → tulis formula, (4) Debug → trace error, (5) Setiap claim butuh evidence.
Jangan langsung jawab. Pikir dulu."""

    async def think(self, user_input: str, context: dict[str, Any]) -> ThinkingResult:
        prompt = self._build_prompt(user_input, context, self.INSTRUCTIONS)
        
        # Return structured thinking request
        return ThinkingResult(
            mode=self.name,
            reasoning=f"Mode kognitif activated for: {user_input[:80]}...",
            output=prompt,
            confidence=0.9,
            metadata={"prompt_type": "cognitive", "requires_reasoning": True},
        )
