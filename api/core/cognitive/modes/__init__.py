"""Thinking modes package."""

from core.cognitive.modes.base import BaseMode, ThinkingResult
from core.cognitive.modes.cognitive import CognitiveMode
from core.cognitive.modes.innovative import InnovativeMode
from core.cognitive.modes.synthesis import SynthesisMode
from core.cognitive.modes.coding import CodingMode
from core.cognitive.modes.autonomous import AutonomousMode

__all__ = [
    "BaseMode",
    "ThinkingResult",
    "CognitiveMode",
    "InnovativeMode",
    "SynthesisMode",
    "CodingMode",
    "AutonomousMode",
]
