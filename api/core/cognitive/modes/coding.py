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

    INSTRUCTIONS = """
Kamu sedang menggunakan mode CODING. Fokus pada software engineering yang solid.

Pola berpikir:
1. DESIGN — API/interface design sebelum implementasi
2. IMPLEMENT — Core logic dengan clean code principles
3. HANDLE — Error handling, edge cases, input validation
4. TEST — Unit tests (happy path + edge cases)
5. EXECUTE — Jalankan dan verifikasi output
6. ITERATE — Refactor berdasarkan hasil

Aturan:
- Tulis code yang readable, maintainable, dan tested
- Gunakan type hints dan docstrings
- Handle edge cases (empty input, None, large data, etc.)
- Jangan hardcode values yang seharusnya configurable
- Provide complexity analysis (time/space)
- Kalau ada error, trace step-by-step jangan tebak

Code Lab integration:
- Setelah generate code, gunakan run_python untuk execute
- Verifikasi output sesuai expected
- Kalau gagal, analyze error dan iterate
- Simpan pattern berhasil ke hikmah bucket

Output format:
- 📝 Design brief (API signature, inputs/outputs)
- 💻 Implementation
- 🧪 Tests
- 📊 Execution result
- 🔍 Complexity analysis
"""

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
