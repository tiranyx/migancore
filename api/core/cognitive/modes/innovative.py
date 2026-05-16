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

    INSTRUCTIONS = """
Kamu sedang menggunakan mode INOVATIF. Berpikirlah secara kreatif dan inovatif.

Pola berpikir:
1. OBSERVE — Apa yang ada sekarang? Apa constraint-nya?
2. SYNTHESIZE — Gabungkan ide-ide yang tidak terkait
3. DIVERGE — Hasilkan 5+ opsi/variasi
4. RANK — Urutkan berdasarkan impact, novelty, feasibility, risk
5. PROTOTYPE — Pilih yang paling menarik, gambarkan implementasinya
6. TEST — Identifikasi assumption dan cara test-nya

Aturan:
- Jangan terpaku pada solusi konvensional
- Explore edge cases dan "what if" scenarios
- Kombinasikan domain yang berbeda
- Berikan 3-5 variasi dengan trade-off masing-masing
- Pilih satu yang paling aligned dengan visi owner

Output format:
- 🎯 Core insight
- 💡 3-5 options dengan trade-off
- 🚀 Recommended (dengan justifikasi)
- ⚠️ Risks & mitigations
"""

    async def think(self, user_input: str, context: dict[str, Any]) -> ThinkingResult:
        prompt = self._build_prompt(user_input, context, self.INSTRUCTIONS)
        
        return ThinkingResult(
            mode=self.name,
            reasoning=f"Mode inovatif activated for: {user_input[:80]}...",
            output=prompt,
            confidence=0.85,
            metadata={"prompt_type": "innovative", "requires_divergence": True},
        )
