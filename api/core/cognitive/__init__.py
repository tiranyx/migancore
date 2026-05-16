"""
OTAK — Cognitive Engine Module
================================
Provides: thinking modes, mode selector, cognitive loop

Usage:
    from core.cognitive import CognitiveEngine, ModeSelector
    
    # Get thinking mode for a query
    result = await ModeSelector.process("Debug this error", {})
    
    # Run full cognitive loop
    engine = CognitiveEngine()
    result = await engine.process(user_input, context, llm_call)
"""

from core.cognitive.engine import CognitiveEngine, CognitiveResult
from core.cognitive.mode_selector import ModeSelector
from core.cognitive.modes.base import BaseMode, ThinkingResult

__all__ = [
    "CognitiveEngine",
    "CognitiveResult",
    "ModeSelector",
    "BaseMode",
    "ThinkingResult",
]
