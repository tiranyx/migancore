"""
Mode Selector — Pilih thinking mode berdasarkan intent user.

Day 76 v1: Basic keyword matching
Day 76 v2: + compound scoring, negation, conversation context, intent classification
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
    """Select appropriate thinking mode based on user intent.
    
    Detection pipeline:
    1. Explicit mode request (e.g., "pake mode coding")
    2. Negation filter (e.g., "bukan evaluasi" → skip autonomous)
    3. Compound keyword scoring (2-word phrases get bonus)
    4. Context hints (error output → coding, sources → synthesis)
    5. Conversation continuity (previous mode → sticky)
    6. Intent classification (question → kognitif, open-ended → inovatif)
    """

    MODES: dict[str, BaseMode] = {
        "kognitif": CognitiveMode(),
        "inovatif": InnovativeMode(),
        "sintesis": SynthesisMode(),
        "coding": CodingMode(),
        "autonomous": AutonomousMode(),
    }

    # Intent keywords → mode mapping
    # Compound keywords (2+ words) get 2x score
    KEYWORDS: dict[str, list[str]] = {
        "coding": [
            # Compound (2x weight)
            "buatkan kode", "buat script", "unit test", "error handling",
            "code review", "debugging", "runtime error", "syntax error",
            "api endpoint", "html css", "python script", "js function",
            # Single
            "code", "script", "function", "program", "debug", "error",
            "python", "javascript", "js", "html", "css", "api", "bug",
            "traceback", "exception", "compile", "syntax", "runtime",
            "errornya", "test", "refactor", "algorithm",
        ],
        "inovatif": [
            # Compound
            "ide baru", "fitur baru", "what if", "bagaimana kalau",
            "brainstorm", "design thinking", "creative solution",
            # Single
            "ide", "inovasi", "kreatif", "design", "desain", "konsep",
            "prototype", "mockup", "wireframe", "imagine",
            "alternatif", "variasi", "improvement", "enhancement",
            "creative", "vision", "future", "roadmap", "strategy",
        ],
        "sintesis": [
            # Compound
            "pros and cons", "kelebihan kekurangan", "analisis komprehensif",
            "compare and contrast", "literature review", "meta-analysis",
            # Single
            "bandingkan", "compare", "vs", "versus", "bedanya",
            "research", "literature", "paper", "study",
            "kombinasikan", "combine", "merge", "integrate",
            "sintesis", "synthesize", "consolidate", "summarize",
            "review", "survey",
        ],
        "autonomous": [
            # Compound
            "evaluasi diri", "self-eval", "lesson learned", "post-mortem",
            "improvement plan", "root cause", "what went wrong",
            "apa yang salah",
            # Single
            "evaluasi", "refleksi", "reflection",
            "belajar dari", "learn from",
            "growth", "evolusi", "evolve",
            "skill", "kemampuan baru", "mastery", "progress",
        ],
        "kognitif": [
            # Compound
            "problem solving", "break down", "cara kerja", "how does",
            "explain why", "jelaskan kenapa", "step by step",
            "langkah demi langkah", "chain of thought", "proof by",
            # Single
            "analisis", "analysis", "pecah",
            "reasoning", "logic", "logical", "matematika", "math",
            "solve", "proof", "bukti",
            "deduction", "infer", "conclude", "hypothesis", "theory",
        ],
    }

    # Negation patterns — if found near keyword, reduce score
    NEGATION_PATTERNS = [
        "bukan", "tidak", "not", "no ", "jangan", "don't", "bukanlah",
    ]

    # Sticky mode: if previous mode was X and user continues related topic,
    # boost X by this amount
    STICKY_BOOST = 1.5

    # How many turns back to look for sticky context
    STICKY_WINDOW = 3

    @classmethod
    def select(cls, user_input: str, context: dict[str, Any] | None = None) -> tuple[str, float]:
        """Select mode based on user input.
        
        Returns:
            (mode_name, confidence)
        """
        text_lower = user_input.lower()
        context = context or {}
        
        # [1] Check explicit mode request
        explicit = cls._check_explicit(text_lower)
        if explicit:
            return explicit, 1.0
        
        # [2] Score each mode by keyword matches
        scores: dict[str, float] = {}
        negated_regions = cls._find_negated_regions(text_lower)
        
        for mode, keywords in cls.KEYWORDS.items():
            score = 0.0
            for kw in keywords:
                # Find all occurrences
                idx = text_lower.find(kw)
                while idx != -1:
                    # Check if keyword is in negated region
                    is_negated = any(start <= idx < end for start, end in negated_regions)
                    
                    if not is_negated:
                        # Compound keywords (contains space) get 2x score
                        weight = 2.0 if " " in kw else 1.0
                        score += weight
                        # Longer keyword = slightly higher confidence
                        score += len(kw) * 0.005
                    
                    idx = text_lower.find(kw, idx + 1)
            
            scores[mode] = score
        
        # [3] Context hints
        if context.get("has_sources"):
            scores["sintesis"] = scores.get("sintesis", 0) + 2.0
        
        if context.get("has_error_output"):
            scores["coding"] = scores.get("coding", 0) + 3.0
        
        if context.get("is_retrospective"):
            scores["autonomous"] = scores.get("autonomous", 0) + 2.0
        
        # [4] Sticky mode (conversation continuity)
        prev_modes = context.get("previous_modes", [])
        if prev_modes:
            # Boost recent modes
            for i, prev_mode in enumerate(prev_modes[-cls.STICKY_WINDOW:]):
                if prev_mode in scores:
                    # More recent = higher boost
                    boost = cls.STICKY_BOOST * (1 + i * 0.3)
                    scores[prev_mode] = scores.get(prev_mode, 0) + boost
        
        # [5] Intent classification fallback
        if not scores or max(scores.values()) == 0:
            return cls._intent_fallback(text_lower)
        
        # Get best mode
        best_mode = max(scores, key=scores.get)
        best_score = scores[best_mode]
        
        # Check runner-up gap (if too close, lower confidence)
        sorted_scores = sorted(scores.values(), reverse=True)
        gap = sorted_scores[0] - (sorted_scores[1] if len(sorted_scores) > 1 else 0)
        
        # Normalize confidence
        max_possible = max(scores.values())
        base_confidence = 0.5 + (best_score / (max_possible + 1)) * 0.4
        
        # Penalize if gap is small (ambiguous)
        if gap < 1.0:
            base_confidence *= 0.8
        
        confidence = min(0.95, base_confidence)
        
        return best_mode, round(confidence, 2)

    @classmethod
    def _find_negated_regions(cls, text: str) -> list[tuple[int, int]]:
        """Find text regions affected by negation.
        
        Returns list of (start, end) tuples where keywords should be ignored.
        Pattern: <negation> ... <punctuation or conjunction>
        """
        regions = []
        for neg in cls.NEGATION_PATTERNS:
            idx = text.find(neg)
            while idx != -1:
                # Find end of negated region (next punctuation or conjunction)
                end = len(text)
                for punct in [".", "?", "!", ",", " tapi ", " tapi", " dan ", " atau "]:
                    punct_idx = text.find(punct, idx + len(neg))
                    if punct_idx != -1 and punct_idx < end:
                        end = punct_idx
                regions.append((idx, end))
                idx = text.find(neg, idx + 1)
        return regions

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
    def _intent_fallback(cls, text: str) -> tuple[str, float]:
        """Default mode based on question vs statement."""
        question_words = ["?", "apa", "bagaimana", "mengapa", "kenapa", "why", "how", "what", "when", "where", "siapa", "who"]
        if any(kw in text for kw in question_words):
            return "kognitif", 0.6
        return "inovatif", 0.5

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
