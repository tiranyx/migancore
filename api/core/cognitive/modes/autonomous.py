"""
AUTONOMOUS — Self-Evaluation & Learning
=========================================
Untuk: Reflection, self-improvement, skill acquisition, growth tracking
"""

from __future__ import annotations

from typing import Any

from core.cognitive.modes.base import BaseMode, ThinkingResult


class AutonomousMode(BaseMode):
    """Mode untuk self-evaluation, reflection, dan continuous learning."""

    name = "autonomous"
    description = "Self-evaluation, reflection, skill acquisition"

    INSTRUCTIONS = """[MODE: AUTONOMOUS]
Self-evaluation & learning. Pola: EVALUATE goal vs actual → REFLECT → ANALYZE root cause → LEARN principles → PLAN changes → GROW skill map.
Rules: (1) Jujur tentang kelemahan, (2) Jangan defensive — admission = growth, (3) Actionable lessons, bukan generalities, (4) Connect ke long-term goals, (5) Track before/after progress.
Format: 🎯 Goal vs Actual | ✅ Worked | ❌ Didn't | 🔍 Root cause | 📚 Lessons | 🔄 Next plan"""

    async def think(self, user_input: str, context: dict[str, Any]) -> ThinkingResult:
        # Check if this is about past performance or future improvement
        is_retrospective = any(kw in user_input.lower() for kw in [
            "kemarin", "hari ini", "evaluasi", "review", "retro",
            "what happened", "how did", "performance", "result"
        ])
        
        prompt = self._build_prompt(user_input, context, self.INSTRUCTIONS)
        
        return ThinkingResult(
            mode=self.name,
            reasoning=f"Mode autonomous activated. Retrospective: {is_retrospective}",
            output=prompt,
            confidence=0.75,
            metadata={
                "prompt_type": "autonomous",
                "is_retrospective": is_retrospective,
                "requires_memory": True,
            },
        )
