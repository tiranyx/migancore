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

    INSTRUCTIONS = """
Kamu sedang menggunakan mode AUTONOMOUS. Evaluasi diri dan belajar dari pengalaman.

Pola berpikir:
1. EVALUATE — Apakah tujuan tercapai? Metrics vs target?
2. REFLECT — Apa yang berhasil? Apa yang tidak?
3. ANALYZE — Root cause dari failure/success
4. LEARN — Extract principles dan patterns
5. PLAN — Apa yang harus diubah untuk next iteration?
6. GROW — Update skill map dan knowledge base

Aturan:
- Jujur tentang kelemahan dan failure
- Jangan defensive — admission of failure = growth signal
- Extract actionable lessons, bukan generalities
- Connect learnings ke long-term goals
- Track progress over time (before/after)

Output format:
- 🎯 Goal vs Actual
- ✅ What worked
- ❌ What didn't
- 🔍 Root cause analysis
- 📚 Lessons learned
- 🔄 Next iteration plan
"""

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
