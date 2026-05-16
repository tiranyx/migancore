"""
Mode Selector — Pilih thinking mode berdasarkan intent user.
"""

from __future__ import annotations

from typing import Any

from core.cognitive.modes.base import BaseMode, ThinkingResult
from core.cognitive.modes.cognitive import CognitiveMode
from core.cognitive.modes.innovative import InnovativeMode
from core.cognitive.modes.synthesis import SynthesisMode
from core.cognitive.modes.coding import CodingMode
from core.cognitive.modes.autonomous import AutonomousMode


class ModeSelector:
    """Select appropriate thinking mode based on user intent."""

    MODES: dict[str, BaseMode] = {
        "kognitif": CognitiveMode(),
        "inovatif": InnovativeMode(),
        "sintesis": SynthesisMode(),
        "coding": CodingMode(),
        "autonomous": AutonomousMode(),
    }

    # Intent keywords → mode mapping
    KEYWORDS: dict[str, list[str]] = {
        "coding": [
            "code", "script", "function", "program", "debug", "error",
            "python", "javascript", "js", "html", "css", "api", "bug",
            "traceback", "exception", "compile", "syntax", "runtime",
            "buatkan kode", "buat script", "debugging", "errornya",
            "test", "unit test", "refactor", "algorithm",
        ],
        "inovatif": [
            "ide", "inovasi", "kreatif", "design", "desain", "konsep",
            "prototype", "mockup", "wireframe", "brainstorm", "imagine",
            "what if", "bagaimana kalau", "alternatif", "variasi",
            "ide baru", "fitur baru", "improvement", "enhancement",
            "creative", "vision", "future", "roadmap", "strategy",
        ],
        "sintesis": [
            "bandingkan", "compare", "vs", "versus", "bedanya",
            "research", "research", "literature", "paper", "study",
            "kombinasikan", "combine", "merge", "integrate",
            "sintesis", "synthesize", "consolidate", "summarize",
            "pros and cons", "kelebihan kekurangan", "analisis komprehensif",
            "review", "survey", "meta-analysis",
        ],
        "autonomous": [
            "evaluasi diri", "evaluasi", "self-eval", "refleksi", "reflection",
            "belajar dari", "learn from", "lesson learned", "post-mortem",
            "apa yang salah", "what went wrong", "root cause",
            "improvement plan", "growth", "evolusi", "evolve",
            "skill", "kemampuan baru", "mastery", "progress",
        ],
        "kognitif": [
            "analisis", "analysis", "break down", "pecah",
            "reasoning", "logic", "logical", "matematika", "math",
            "problem solving", "solve", "cara kerja", "how does",
            "explain why", "jelaskan kenapa", "proof", "bukti",
            "step by step", "langkah demi langkah", "deduction",
            "infer", "conclude", "hypothesis", "theory",
        ],
    }

    @classmethod
    def select(cls, user_input: str, context: dict[str, Any] | None = None) -> tuple[str, float]:
        """Select mode based on user input.
        
        Returns:
            (mode_name, confidence)
        """
        text_lower = user_input.lower()
        context = context or {}
        
        # Check explicit mode request
        explicit = cls._check_explicit(text_lower)
        if explicit:
            return explicit, 1.0
        
        # Score each mode by keyword matches
        scores: dict[str, float] = {}
        for mode, keywords in cls.KEYWORDS.items():
            score = 0.0
            for kw in keywords:
                if kw in text_lower:
                    score += 1.0
                    # Longer keyword match = higher confidence
                    score += len(kw) * 0.01
            scores[mode] = score
        
        # Check context hints
        if context.get("has_sources"):
            scores["sintesis"] = scores.get("sintesis", 0) + 2.0
        
        if context.get("has_error_output"):
            scores["coding"] = scores.get("coding", 0) + 3.0
        
        if context.get("is_retrospective"):
            scores["autonomous"] = scores.get("autonomous", 0) + 2.0
        
        # Get best mode
        if not scores or max(scores.values()) == 0:
            # Default: kognitif for questions, inovatif for open-ended
            if any(kw in text_lower for kw in ["?", "apa", "bagaimana", "mengapa", "why", "how", "what"]):
                return "kognitif", 0.6
            return "inovatif", 0.5
        
        best_mode = max(scores, key=scores.get)
        best_score = scores[best_mode]
        
        # Normalize confidence
        max_possible = max(scores.values())
        confidence = min(0.95, 0.5 + (best_score / (max_possible + 1)) * 0.5)
        
        return best_mode, round(confidence, 2)

    @classmethod
    def _check_explicit(cls, text: str) -> str | None:
        """Check if user explicitly requests a mode."""
        explicit_patterns = {
            "coding": ["mode coding", "coding mode", "pake mode coding", "gunakan mode coding"],
            "inovatif": ["mode inovatif", "innovative mode", "pake mode inovatif"],
            "sintesis": ["mode sintesis", "synthesis mode", "pake mode sintesis"],
            "autonomous": ["mode autonomous", "autonomous mode", "pake mode autonomous"],
            "kognitif": ["mode kognitif", "cognitive mode", "pake mode kognitif", "think deeply"],
        }
        
        for mode, patterns in explicit_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    return mode
        
        return None

    @classmethod
    async def process(cls, user_input: str, context: dict[str, Any] | None = None) -> ThinkingResult:
        """Select mode and run thinking."""
        mode_name, confidence = cls.select(user_input, context)
        mode = cls.MODES.get(mode_name)
        
        if mode is None:
            mode = cls.MODES["kognitif"]
            mode_name = "kognitif"
        
        result = await mode.think(user_input, context or {})
        result.confidence = confidence
        return result
