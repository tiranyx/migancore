"""
SINTESIS — Multi-Source Fusion
================================
Untuk: Research, documentation, knowledge consolidation, contradiction resolution
"""

from __future__ import annotations

from typing import Any

from core.cognitive.modes.base import BaseMode, ThinkingResult


class SynthesisMode(BaseMode):
    """Mode untuk menggabungkan, membandingkan, dan menyintesis informasi dari multiple sources."""

    name = "sintesis"
    description = "Multi-source fusion, contradiction resolution, research"

    INSTRUCTIONS = """[MODE: SINTESIS]
Sintesis multi-source. Pola: EXTRACT key claims → COMPARE → CONFLICT detection → RESOLVE with evidence → UNIFY → CITE sources.
Rules: (1) Jangan cherry-pick, (2) Flag contradictions, (3) Evidence hierarchy: empirical > theoretical > anecdotal, (4) Confidence level per claim, (5) Cite [S1], [S2].
Format: 📋 Claims | ⚖️ Agreement | ⚠️ Contradictions | 🔧 Resolution | 🎯 Conclusion | 📖 Sources"""

    async def think(self, user_input: str, context: dict[str, Any]) -> ThinkingResult:
        # Check if we have sources in context
        sources = context.get("sources", [])
        
        prompt = self._build_prompt(user_input, context, self.INSTRUCTIONS)
        
        return ThinkingResult(
            mode=self.name,
            reasoning=f"Mode sintesis activated. Sources: {len(sources)}",
            output=prompt,
            confidence=0.8 if sources else 0.6,
            metadata={
                "prompt_type": "synthesis",
                "source_count": len(sources),
                "has_sources": bool(sources),
            },
        )
