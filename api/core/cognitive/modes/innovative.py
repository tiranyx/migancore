"""
INOVATIF — Creative Synthesis
===============================
Untuk: Design, architecture, feature ideas, creative writing, lateral thinking
"""

from __future__ import annotations

from typing import Any

from core.cognitive.modes.base import BaseMode, ThinkingResult


class InnovativeMode(BaseMode):
    """Mode untuk berpikir kreatif, inovatif, dan out-of-the-box."""

    name = "inovatif"
    description = "Creative synthesis, lateral thinking, idea generation"

    INSTRUCTIONS = """[MODE: INOVATIF]
Pikir kreatif & out-of-the-box. Pola: OBSERVE constraint → SYNTHESIZE ide tak terkait → DIVERGE 3-5 opsi → RANK by impact/novelty/feasibility/risk → PROTOTYPE best → TEST assumptions.
Rules: (1) Jangan solusi konvensional, (2) Explore "what if", (3) Kombinasi domain berbeda, (4) 3-5 opsi + trade-off, (5) Pilih yang aligned visi owner.
Format: 🎯 Core insight | 💡 3-5 options | 🚀 Recommended | ⚠️ Risks"""

    async def think(self, user_input: str, context: dict[str, Any]) -> ThinkingResult:
        prompt = self._build_prompt(user_input, context, self.INSTRUCTIONS)
        
        return ThinkingResult(
            mode=self.name,
            reasoning=f"Mode inovatif activated for: {user_input[:80]}...",
            output=prompt,
            confidence=0.85,
            metadata={"prompt_type": "innovative", "requires_divergence": True},
        )
