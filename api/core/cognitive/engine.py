"""
OTAK — Cognitive Engine
=========================
PERCEIVE → PLAN → REASON → ACT → REFLECT → RESPOND

Usage:
    from core.cognitive.engine import CognitiveEngine
    
    engine = CognitiveEngine()
    result = await engine.process(user_input, context)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

from config import settings
from core.cognitive.mode_selector import ModeSelector
from core.identity.enforcer import _get_identity_enforcer
from core.event_bus import event_bus

logger = structlog.get_logger()


@dataclass
class CognitiveResult:
    """Result dari cognitive loop."""
    response: str = ""
    mode: str = "kognitif"
    plan: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    reflections: list[str] = field(default_factory=list)
    identity_enforced: bool = False
    identity_score: float = 0.0
    elapsed_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class CognitiveEngine:
    """Main cognitive loop engine."""

    def __init__(self):
        self.identity_enforcer = _get_identity_enforcer()

    async def process(
        self,
        user_input: str,
        context: dict[str, Any],
        llm_call: Any = None,  # Function to call LLM
    ) -> CognitiveResult:
        """Run full cognitive loop.
        
        Args:
            user_input: Raw user message
            context: Dict with conversation_history, memory, agent, etc.
            llm_call: Async function(messages, options) -> response
        
        Returns:
            CognitiveResult with response and metadata
        """
        if not settings.COGNITIVE_LOOP_ENABLED:
            # Fallback: direct LLM call without cognitive loop
            return await self._direct_response(user_input, context, llm_call)
        
        start = time.time()
        result = CognitiveResult()
        
        try:
            # [1] PERCEIVE
            perception = await self._perceive(user_input, context)
            result.mode = perception.get("mode", "kognitif")
            
            # [2] PLAN
            plan = await self._plan(user_input, perception, context, llm_call)
            result.plan = plan
            
            # [3] REASON
            reasoning = await self._reason(user_input, plan, context, llm_call)
            
            # [4] ACT
            actions = await self._act(reasoning, context, llm_call)
            result.tool_calls = actions.get("tool_calls", [])
            
            # [5] REFLECT (async, non-blocking)
            asyncio.create_task(self._reflect(user_input, reasoning, actions, context))
            
            # [6] RESPOND
            response = actions.get("response", reasoning.get("response", ""))
            
            # Identity enforcement
            if settings.IDENTITY_ENFORCEMENT_ENABLED:
                response, identity_meta = await self._enforce_identity(response, user_input)
                result.identity_enforced = identity_meta.get("enforced", False)
                result.identity_score = identity_meta.get("score", 0.0)
            
            result.response = response
            result.elapsed_ms = int((time.time() - start) * 1000)
            
            logger.info(
                "cognitive.loop_complete",
                mode=result.mode,
                plan_steps=len(plan),
                tool_calls=len(result.tool_calls),
                identity_score=result.identity_score,
                elapsed_ms=result.elapsed_ms,
            )
            
        except Exception as exc:
            logger.error("cognitive.loop_error", error=str(exc))
            # Fallback to direct response
            return await self._direct_response(user_input, context, llm_call)
        
        return result

    async def _perceive(self, user_input: str, context: dict[str, Any]) -> dict[str, Any]:
        """[1] PERCEIVE — Parse intent, extract entities, load context."""
        # Select thinking mode
        mode_result = await ModeSelector.process(user_input, context)
        
        # Extract entities (simple keyword-based for now)
        entities = self._extract_entities(user_input)
        
        # Load relevant memories
        memory_summary = context.get("memory_summary", "")
        
        perception = {
            "mode": mode_result.mode,
            "mode_confidence": mode_result.confidence,
            "entities": entities,
            "intent": self._classify_intent(user_input),
            "memory_summary": memory_summary,
            "is_identity_question": any(kw in user_input.lower() for kw in [
                "siapa kamu", "who are you", "pencipta", "creator", "tujuan", "purpose",
            ]),
            "is_code_request": mode_result.mode == "coding",
            "is_creative_request": mode_result.mode == "inovatif",
        }
        
        logger.debug("cognitive.perceive", **perception)
        return perception

    async def _plan(
        self,
        user_input: str,
        perception: dict[str, Any],
        context: dict[str, Any],
        llm_call: Any,
    ) -> list[dict]:
        """[2] PLAN — Decompose into sub-tasks."""
        mode = perception.get("mode", "kognitif")
        
        # Simple planning: map mode to default plan
        plans = {
            "coding": [
                {"step": 1, "task": "Design API/interface", "tool": None},
                {"step": 2, "task": "Implement core logic", "tool": None},
                {"step": 3, "task": "Add error handling", "tool": None},
                {"step": 4, "task": "Test execution", "tool": "run_python"},
            ],
            "sintesis": [
                {"step": 1, "task": "Extract key claims", "tool": None},
                {"step": 2, "task": "Compare sources", "tool": None},
                {"step": 3, "task": "Resolve contradictions", "tool": None},
                {"step": 4, "task": "Synthesize unified view", "tool": None},
            ],
            "inovatif": [
                {"step": 1, "task": "Observe constraints", "tool": None},
                {"step": 2, "task": "Generate 5+ options", "tool": None},
                {"step": 3, "task": "Rank by impact/feasibility", "tool": None},
                {"step": 4, "task": "Prototype best option", "tool": None},
            ],
            "autonomous": [
                {"step": 1, "task": "Evaluate outcome", "tool": None},
                {"step": 2, "task": "Extract lessons", "tool": None},
                {"step": 3, "task": "Update skill map", "tool": "memory_write"},
            ],
            "kognitif": [
                {"step": 1, "task": "Understand problem", "tool": None},
                {"step": 2, "task": "Break into sub-problems", "tool": None},
                {"step": 3, "task": "Solve each step", "tool": None},
                {"step": 4, "task": "Verify consistency", "tool": None},
            ],
        }
        
        return plans.get(mode, plans["kognitif"])

    async def _reason(
        self,
        user_input: str,
        plan: list[dict],
        context: dict[str, Any],
        llm_call: Any,
    ) -> dict[str, Any]:
        """[3] REASON — Chain-of-thought, evaluate options."""
        if llm_call is None:
            return {"response": "", "reasoning": "No LLM available"}
        
        # Build reasoning prompt
        system_prompt = context.get("system_prompt", "")
        reasoning_prompt = (
            f"{system_prompt}\n\n"
            f"[COGNITIVE LOOP — REASONING PHASE]\n"
            f"Plan: {[p['task'] for p in plan]}\n\n"
            f"Think step-by-step before responding. Show your reasoning.\n\n"
            f"User: {user_input}\n\n"
            f"Assistant reasoning:"
        )
        
        messages = [{"role": "system", "content": reasoning_prompt}]
        response = await llm_call(messages, {"temperature": 0.3, "num_predict": 512})
        
        return {
            "response": response,
            "reasoning": response,
        }

    async def _act(
        self,
        reasoning: dict[str, Any],
        context: dict[str, Any],
        llm_call: Any,
    ) -> dict[str, Any]:
        """[4] ACT — Execute tool calls, query memory, etc."""
        # For now, just return the reasoning response
        # Full tool execution will be integrated with existing tool router
        return {
            "response": reasoning.get("response", ""),
            "tool_calls": [],
        }

    async def _reflect(
        self,
        user_input: str,
        reasoning: dict[str, Any],
        actions: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        """[5] REFLECT — Evaluate outcome, extract learning (async, non-blocking)."""
        try:
            response = actions.get("response", "")
            
            # Simple reflection heuristics
            reflection_points = []
            
            # Check if response addresses the question
            if len(response) < 20:
                reflection_points.append("Response too short — may not address question fully")
            
            # Check for identity markers
            if "mighan" not in response.lower() and "tiranyx" not in response.lower():
                if any(kw in user_input.lower() for kw in ["siapa", "who", "kamu"]):
                    reflection_points.append("Identity question without identity markers")
            
            # Publish reflection event if meaningful
            if reflection_points and settings.EVENT_BUS_ENABLED:
                await event_bus.publish(
                    "mighan:reflection:created",
                    {
                        "reflection_key": "cognitive_loop",
                        "content": "; ".join(reflection_points),
                        "category": "learn",
                        "user_input_preview": user_input[:100],
                        "response_preview": response[:100],
                    },
                    source="cognitive_engine",
                )
        
        except Exception as exc:
            logger.warning("cognitive.reflect_error", error=str(exc))

    async def _enforce_identity(self, response: str, user_question: str) -> tuple[str, dict]:
        """Identity enforcement wrapper."""
        from routers.chat import _enforce_identity as chat_enforce
        return await chat_enforce(response, user_question, is_streaming=False)

    async def _direct_response(
        self,
        user_input: str,
        context: dict[str, Any],
        llm_call: Any,
    ) -> CognitiveResult:
        """Fallback: direct LLM call without cognitive loop."""
        start = time.time()
        
        if llm_call:
            response = await llm_call(
                [{"role": "user", "content": user_input}],
                {"temperature": 0, "num_predict": 1024},
            )
        else:
            response = ""
        
        return CognitiveResult(
            response=response,
            mode="direct",
            elapsed_ms=int((time.time() - start) * 1000),
        )

    def _extract_entities(self, text: str) -> list[str]:
        """Simple entity extraction."""
        # Extract capitalized phrases as entities
        import re
        entities = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', text)
        return list(set(entities))[:10]  # Limit to 10

    def _classify_intent(self, text: str) -> str:
        """Simple intent classification."""
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in ["buatkan", "create", "generate", "write", "code"]):
            return "creation"
        if any(kw in text_lower for kw in ["apa", "what", "siapa", "who", "bagaimana", "how"]):
            return "question"
        if any(kw in text_lower for kw in ["bandingkan", "compare", "vs", "bedanya"]):
            return "comparison"
        if any(kw in text_lower for kw in ["fix", "debug", "error", "bug", "solve"]):
            return "problem_solving"
        if any(kw in text_lower for kw in ["ide", "ide", "inovasi", "brainstorm"]):
            return "ideation"
        
        return "general"
