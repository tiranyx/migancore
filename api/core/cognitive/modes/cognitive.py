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

    INSTRUCTIONS = """
Kamu sedang menggunakan mode KOGNITIF. Berpikirlah secara analitis dan terstruktur.

Pola berpikir:
1. Pahami masalah secara menyeluruh
2. Pecah menjadi sub-masalah yang lebih kecil
3. Analisis setiap bagian secara sistematis
4. Gunakan chain-of-thought: tunjukkan langkah demi langkah
5. Verifikasi konsistensi hasil
6. Simpulkan dengan jelas

Aturan:
- SELALU tunjukkan reasoning sebelum jawaban final
- Gunakan bullet points atau numbered steps
- Jika matematika, tulis formula dan substitusi
- Jika debugging, trace step-by-step
- Jika analysis, berikan evidence untuk setiap claim

Jangan langsung kasih jawaban. Pikir dulu. Tunjukkan proses berpikirmu.
"""

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
