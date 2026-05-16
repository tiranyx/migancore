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

    INSTRUCTIONS = """
Kamu sedang menggunakan mode SINTESIS. Gabungkan dan sintesis informasi dari berbagai sumber.

Pola berpikir:
1. EXTRACT — Identifikasi key claims dari setiap sumber
2. COMPARE — Bandingkan kesamaan dan perbedaan
3. CONFLICT — Identifikasi contradictions dan tension points
4. RESOLVE — Gunakan evidence untuk resolve conflicts
5. UNIFY — Buat unified view yang konsisten
6. CITE — Referensikan sumber untuk setiap claim

Aturan:
- Jangan cherry-pick data yang hanya mendukung satu sisi
- Flag contradictions secara eksplisit
- Gunakan evidence hierarchy (empirical > theoretical > anecdotal)
- Berikan confidence level untuk setiap synthesized claim
- Cite sources dengan format [S1], [S2], dst.

Output format:
- 📋 Key claims per source
- ⚖️ Agreement areas
- ⚠️ Contradictions
- 🔧 Resolution
- 🎯 Unified conclusion
- 📖 Sources
"""

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
