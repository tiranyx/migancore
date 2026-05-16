"""
Unit tests for OTAK — Cognitive Engine & Thinking Modes
"""

import pytest
from core.cognitive.mode_selector import ModeSelector
from core.cognitive.modes.cognitive import CognitiveMode
from core.cognitive.modes.innovative import InnovativeMode
from core.cognitive.modes.synthesis import SynthesisMode
from core.cognitive.modes.coding import CodingMode
from core.cognitive.modes.autonomous import AutonomousMode


class TestModeSelector:
    """Test thinking mode selection."""

    @pytest.mark.asyncio
    async def test_select_coding_mode(self):
        """Coding keywords should select coding mode."""
        queries = [
            "buatkan script python untuk scraping",
            "debug error ini",
            "buatkan function API endpoint",
            "code review untuk module ini",
        ]
        for q in queries:
            mode, confidence = ModeSelector.select(q)
            assert mode == "coding", f"Expected coding for '{q[:40]}...', got {mode}"
            assert confidence > 0.5

    @pytest.mark.asyncio
    async def test_select_innovative_mode(self):
        """Innovation keywords should select inovatif mode."""
        queries = [
            "ide baru untuk fitur dashboard",
            "desain arsitektur microservices",
            "brainstorm fitur AI",
            "bagaimana kalau kita tambahkan gamification?",
        ]
        for q in queries:
            mode, confidence = ModeSelector.select(q)
            assert mode == "inovatif", f"Expected inovatif for '{q[:40]}...', got {mode}"

    @pytest.mark.asyncio
    async def test_select_synthesis_mode(self):
        """Synthesis keywords should select sintesis mode."""
        queries = [
            "bandingkan postgres vs mysql",
            "sintesis literatur tentang RAG",
            "pros and cons dari microservices",
            "kombinasikan ide dari 3 paper ini",
        ]
        for q in queries:
            mode, confidence = ModeSelector.select(q)
            assert mode == "sintesis", f"Expected sintesis for '{q[:40]}...', got {mode}"

    @pytest.mark.asyncio
    async def test_select_autonomous_mode(self):
        """Self-evaluation keywords should select autonomous mode."""
        queries = [
            "evaluasi performa hari ini",
            "refleksi dari sprint kemarin",
            "apa yang salah dengan approach ini?",
            "lesson learned dari deployment",
        ]
        for q in queries:
            mode, confidence = ModeSelector.select(q)
            assert mode == "autonomous", f"Expected autonomous for '{q[:40]}...', got {mode}"

    @pytest.mark.asyncio
    async def test_select_cognitive_mode(self):
        """Analytical keywords should select kognitif mode."""
        queries = [
            "analisis kompleksitas algoritma ini",
            "jelaskan kenapa error terjadi",
            "bagaimana cara kerja neural network?",
            "proof bahwa O(n log n) optimal",
        ]
        for q in queries:
            mode, confidence = ModeSelector.select(q)
            assert mode == "kognitif", f"Expected kognitif for '{q[:40]}...', got {mode}"

    @pytest.mark.asyncio
    async def test_explicit_mode_request(self):
        """User can explicitly request a mode."""
        mode, confidence = ModeSelector.select("pake mode coding untuk ini")
        assert mode == "coding"
        assert confidence == 1.0

        mode, confidence = ModeSelector.select("think deeply about this")
        assert mode == "kognitif"
        assert confidence == 1.0

    @pytest.mark.asyncio
    async def test_default_mode_for_question(self):
        """Questions without clear mode default to kognitif."""
        mode, confidence = ModeSelector.select("apa itu machine learning?")
        assert mode == "kognitif"

    @pytest.mark.asyncio
    async def test_context_hints(self):
        """Context hints should influence mode selection."""
        # Error context should push to coding
        mode, _ = ModeSelector.select("ini outputnya", context={"has_error_output": True})
        assert mode == "coding"

        # Retrospective context should push to autonomous
        mode, _ = ModeSelector.select("review hasil", context={"is_retrospective": True})
        assert mode == "autonomous"

        # Sources context should push to synthesis
        mode, _ = ModeSelector.select("analisis data", context={"has_sources": True})
        assert mode == "sintesis"

    @pytest.mark.asyncio
    async def test_process_method(self):
        """ModeSelector.process should return ThinkingResult."""
        result = await ModeSelector.process("buatkan function python")
        assert result.mode == "coding"
        assert result.confidence > 0
        assert "coding" in result.output.lower()


class TestIndividualModes:
    """Test individual thinking modes."""

    @pytest.mark.asyncio
    async def test_cognitive_mode(self):
        """Cognitive mode should include reasoning instructions."""
        mode = CognitiveMode()
        result = await mode.think("2+2=", {})
        assert result.mode == "kognitif"
        assert "chain-of-thought" in result.output.lower() or "reasoning" in result.output.lower()
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_innovative_mode(self):
        """Innovative mode should include creative instructions."""
        mode = InnovativeMode()
        result = await mode.think("ide fitur baru", {})
        assert result.mode == "inovatif"
        assert "synthesize" in result.output.lower() or "options" in result.output.lower()

    @pytest.mark.asyncio
    async def test_synthesis_mode(self):
        """Synthesis mode should handle sources."""
        mode = SynthesisMode()
        result = await mode.think("bandingkan 2 pendekatan", {"sources": ["s1", "s2"]})
        assert result.mode == "sintesis"
        assert result.metadata["source_count"] == 2
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_synthesis_mode_no_sources(self):
        """Synthesis mode with no sources should have lower confidence."""
        mode = SynthesisMode()
        result = await mode.think("bandingkan 2 pendekatan", {})
        assert result.confidence == 0.6

    @pytest.mark.asyncio
    async def test_coding_mode_debug(self):
        """Coding mode should detect debugging requests."""
        mode = CodingMode()
        result = await mode.think("fix this bug", {})
        assert result.mode == "coding"
        assert result.metadata["is_debugging"] is True
        assert result.metadata["use_code_lab"] is True

    @pytest.mark.asyncio
    async def test_autonomous_mode_retrospective(self):
        """Autonomous mode should detect retrospective queries."""
        mode = AutonomousMode()
        result = await mode.think("evaluasi hari ini", {})
        assert result.mode == "autonomous"
        assert result.metadata["is_retrospective"] is True

    @pytest.mark.asyncio
    async def test_autonomous_mode_non_retrospective(self):
        """Autonomous mode for non-retrospective queries."""
        mode = AutonomousMode()
        result = await mode.think("bagaimana cara improve?", {})
        assert result.metadata["is_retrospective"] is False


class TestModeSelectorEdgeCases:
    """Edge cases for mode selection."""

    @pytest.mark.asyncio
    async def test_empty_input(self):
        """Empty input should not crash."""
        mode, confidence = ModeSelector.select("")
        assert mode in ["kognitif", "inovatif"]

    @pytest.mark.asyncio
    async def test_very_long_input(self):
        """Very long input should not crash."""
        long_text = "python " * 1000
        mode, confidence = ModeSelector.select(long_text)
        assert mode == "coding"

    @pytest.mark.asyncio
    async def test_multiple_keywords(self):
        """Input with multiple mode keywords should pick strongest match."""
        mode, confidence = ModeSelector.select("debug dan analisis error ini")
        assert mode == "coding"

    @pytest.mark.asyncio
    async def test_negation_filtering(self):
        """Negated keywords should not trigger mode."""
        mode, confidence = ModeSelector.select("bukan evaluasi, tapi analisis")
        # "evaluasi" is negated by "bukan", should not trigger autonomous
        assert mode != "autonomous"

    @pytest.mark.asyncio
    async def test_negation_with_valid_keyword(self):
        """Valid keyword outside negation should still work."""
        mode, confidence = ModeSelector.select("bukan evaluasi, tapi debug error ini")
        # "evaluasi" negated, but "debug" and "error" should trigger coding
        assert mode == "coding"

    @pytest.mark.asyncio
    async def test_compound_keyword_bonus(self):
        """Compound keywords (2+ words) should score higher."""
        # "problem solving" (compound, 2x) should beat "solve" (single)
        # But "problem solving" is kognitif, let's test coding compound
        mode, confidence = ModeSelector.select("buatkan kode python")
        # "buatkan kode" is compound (2x) → should strongly favor coding
        assert mode == "coding"
        assert confidence > 0.7

    @pytest.mark.asyncio
    async def test_sticky_mode(self):
        """Previous mode should influence current selection."""
        # Without context, "analisis" → kognitif
        mode, _ = ModeSelector.select("analisis data")
        assert mode == "kognitif"
        
        # With previous coding context, should boost coding if ambiguous
        mode, _ = ModeSelector.select(
            "analisis error di code ini",
            context={"previous_modes": ["coding"]}
        )
        assert mode == "coding"

    @pytest.mark.asyncio
    async def test_ambiguous_low_confidence(self):
        """Ambiguous input should have lower confidence."""
        # "analisis" alone is kognitif but weak
        mode, confidence = ModeSelector.select("analisis")
        assert mode == "kognitif"
        assert confidence < 0.8  # Should be uncertain
