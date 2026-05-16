"""
OTAK — Cognitive Engine v2
============================
PERCEIVE → PLAN → REASON → ACT → REFLECT → RESPOND

Day 76 v1: Skeleton
Day 76 v2: + structured reasoning, tool integration, reflection persistence

Usage:
    from core.cognitive.engine import CognitiveEngine
    
    engine = CognitiveEngine()
    result = await engine.process(user_input, context, llm_call)
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

from config import settings
from core.cognitive.mode_selector import ModeSelector
from core.event_bus import event_bus

logger = structlog.get_logger()


@dataclass
class ReasoningOutput:
    """Structured output dari REASON phase."""
    chain_of_thought: str = ""
    key_insights: list[str] = field(default_factory=list)
    confidence: float = 0.0
    needs_tool: bool = False
    suggested_tools: list[str] = field(default_factory=list)
    draft_response: str = ""


@dataclass
class CognitiveResult:
    """Result dari cognitive loop."""
    response: str = ""
    mode: str = "kognitif"
    plan: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    reflections: list[str] = field(default_factory=list)
    reasoning: ReasoningOutput = field(default_factory=ReasoningOutput)
    identity_enforced: bool = False
    identity_score: float = 0.0
    elapsed_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class CognitiveEngine:
    """Main cognitive loop engine.
    
    Implements ReAct-style reasoning + Reflexion reflection.
    Compatible with LangGraph director (can wrap or replace).
    """

    def __init__(self):
        self.reflection_count = 0

    async def process(
        self,
        user_input: str,
        context: dict[str, Any],
        llm_call: Any = None,
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
            return await self._direct_response(user_input, context, llm_call)
        
        start = time.time()
        result = CognitiveResult()
        
        try:
            # [1] PERCEIVE
            perception = await self._perceive(user_input, context)
            result.mode = perception.get("mode", "kognitif")
            
            # [2] PLAN
            plan = self._plan(perception)
            result.plan = plan
            
            # [3] REASON — Structured chain-of-thought
            reasoning = await self._reason(user_input, plan, perception, context, llm_call)
            result.reasoning = reasoning
            
            # [4] ACT — Tool execution if needed
            if reasoning.needs_tool and reasoning.suggested_tools:
                actions = await self._act_with_tools(reasoning, context, llm_call)
            else:
                actions = {"response": reasoning.draft_response, "tool_calls": []}
            
            result.tool_calls = actions.get("tool_calls", [])
            
            # [5] REFLECT — Async, non-blocking
            asyncio.create_task(self._reflect(user_input, reasoning, actions, perception, context))
            
            # [6] RESPOND
            result.response = actions.get("response", reasoning.draft_response)
            result.elapsed_ms = int((time.time() - start) * 1000)
            
            logger.info(
                "cognitive.loop_complete",
                mode=result.mode,
                plan_steps=len(plan),
                tool_calls=len(result.tool_calls),
                reasoning_confidence=reasoning.confidence,
                elapsed_ms=result.elapsed_ms,
            )
            
        except Exception as exc:
            logger.error("cognitive.loop_error", error=str(exc))
            return await self._direct_response(user_input, context, llm_call)
        
        return result

    async def _perceive(self, user_input: str, context: dict[str, Any]) -> dict[str, Any]:
        """[1] PERCEIVE — Parse intent, extract entities, load context."""
        mode_result = await ModeSelector.process(user_input, context)
        
        perception = {
            "mode": mode_result.mode,
            "mode_confidence": mode_result.confidence,
            "entities": self._extract_entities(user_input),
            "intent": self._classify_intent(user_input),
            "memory_summary": context.get("memory_summary", "")[:500],
            "is_identity_question": any(kw in user_input.lower() for kw in [
                "siapa kamu", "who are you", "pencipta", "creator", "tujuan", "purpose",
            ]),
            "is_code_request": mode_result.mode == "coding",
            "is_creative_request": mode_result.mode == "inovatif",
            "has_history": bool(context.get("conversation_history")),
        }
        
        logger.debug("cognitive.perceive", mode=perception["mode"], intent=perception["intent"])
        return perception

    def _plan(self, perception: dict[str, Any]) -> list[dict]:
        """[2] PLAN — Decompose into sub-tasks."""
        mode = perception.get("mode", "kognitif")
        
        plans = {
            "coding": [
                {"step": 1, "task": "Design API/interface", "tool": None},
                {"step": 2, "task": "Implement core logic", "tool": None},
                {"step": 3, "task": "Handle errors/edge cases", "tool": None},
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
                {"step": 2, "task": "Generate options", "tool": None},
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
        perception: dict[str, Any],
        context: dict[str, Any],
        llm_call: Any,
    ) -> ReasoningOutput:
        """[3] REASON — Structured chain-of-thought with tool detection."""
        if llm_call is None:
            return ReasoningOutput(draft_response="", confidence=0.0)
        
        system_prompt = context.get("system_prompt", "")
        
        # Build structured reasoning prompt
        reasoning_prompt = self._build_reasoning_prompt(
            system_prompt, user_input, plan, perception
        )
        
        messages = [{"role": "system", "content": reasoning_prompt}]
        
        # Call LLM with lower temperature for reasoning
        raw_response = await llm_call(messages, {
            "temperature": 0.2,
            "num_predict": 1024,
        })
        
        # Parse structured output
        return self._parse_reasoning_output(raw_response, perception)

    def _build_reasoning_prompt(
        self,
        system_prompt: str,
        user_input: str,
        plan: list[dict],
        perception: dict[str, Any],
    ) -> str:
        """Build prompt for structured reasoning."""
        plan_str = " → ".join([p["task"] for p in plan])
        
        prompt_parts = [
            system_prompt,
            "",
            "[COGNITIVE LOOP — REASONING PHASE]",
            f"Mode: {perception['mode']}",
            f"Intent: {perception['intent']}",
            f"Plan: {plan_str}",
            "",
            "Respond in this JSON format:",
            '{',
            '  "chain_of_thought": "Your step-by-step reasoning here",',
            '  "key_insights": ["insight 1", "insight 2"],',
            '  "confidence": 0.85,',
            '  "needs_tool": false,',
            '  "suggested_tools": [],',
            '  "draft_response": "Your draft answer"',
            '}',
            "",
            f"User: {user_input}",
            "",
            "Assistant reasoning (JSON):",
        ]
        
        return "\n".join(prompt_parts)

    def _parse_reasoning_output(self, raw: str, perception: dict[str, Any]) -> ReasoningOutput:
        """Parse LLM response into structured ReasoningOutput."""
        # Try to extract JSON from response
        try:
            # Find JSON block
            json_start = raw.find("{")
            json_end = raw.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = raw[json_start:json_end]
                data = json.loads(json_str)
                
                return ReasoningOutput(
                    chain_of_thought=data.get("chain_of_thought", ""),
                    key_insights=data.get("key_insights", []),
                    confidence=float(data.get("confidence", 0.5)),
                    needs_tool=bool(data.get("needs_tool", False)),
                    suggested_tools=data.get("suggested_tools", []),
                    draft_response=data.get("draft_response", raw),
                )
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("cognitive.reasoning_parse_failed", error=str(exc))
        
        # Fallback: treat entire response as draft_response
        return ReasoningOutput(
            chain_of_thought="Direct response (parsing failed)",
            draft_response=raw,
            confidence=0.5,
        )

    async def _act_with_tools(
        self,
        reasoning: ReasoningOutput,
        context: dict[str, Any],
        llm_call: Any,
    ) -> dict[str, Any]:
        """[4] ACT — Execute suggested tools and compose response."""
        tool_calls = []
        
        # For now, log tool suggestions but don't execute
        # Full integration requires tool_router access
        if reasoning.suggested_tools:
            logger.info(
                "cognitive.tool_suggestions",
                tools=reasoning.suggested_tools,
                mode=context.get("mode", "unknown"),
            )
            
            # Placeholder: in production, this would call tool_router
            for tool_name in reasoning.suggested_tools[:3]:  # Max 3 tools
                tool_calls.append({
                    "tool": tool_name,
                    "status": "pending",
                    "result": None,
                })
        
        return {
            "response": reasoning.draft_response,
            "tool_calls": tool_calls,
        }

    async def _reflect(
        self,
        user_input: str,
        reasoning: ReasoningOutput,
        actions: dict[str, Any],
        perception: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        """[5] REFLECT — Evaluate outcome, extract learning (async, non-blocking)."""
        try:
            response = actions.get("response", "")
            reflection_points = []
            
            # Heuristic 1: Response length check
            if len(response) < 20:
                reflection_points.append("response_too_short")
            
            # Heuristic 2: Identity markers on identity questions
            if perception.get("is_identity_question"):
                if "mighan" not in response.lower() and "tiranyx" not in response.lower():
                    reflection_points.append("identity_missing")
            
            # Heuristic 3: Reasoning confidence
            if reasoning.confidence < 0.5:
                reflection_points.append("low_reasoning_confidence")
            
            # Heuristic 4: Tool was suggested but not executed
            if reasoning.needs_tool and not actions.get("tool_calls"):
                reflection_points.append("tool_suggested_not_executed")
            
            # Persist reflection
            if reflection_points:
                self.reflection_count += 1
                
                if settings.EVENT_BUS_ENABLED:
                    await event_bus.publish(
                        "mighan:reflection:created",
                        {
                            "reflection_key": f"cognitive_loop_{self.reflection_count}",
                            "content": "; ".join(reflection_points),
                            "category": "learn",
                            "user_input_preview": user_input[:100],
                            "response_preview": response[:100],
                            "reasoning_confidence": reasoning.confidence,
                        },
                        source="cognitive_engine",
                    )
                
                logger.info(
                    "cognitive.reflection",
                    points=reflection_points,
                    confidence=reasoning.confidence,
                )
        
        except Exception as exc:
            logger.warning("cognitive.reflect_error", error=str(exc))

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
        import re
        entities = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', text)
        return list(set(entities))[:10]

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
        if any(kw in text_lower for kw in ["ide", "inovasi", "brainstorm"]):
            return "ideation"
        
        return "general"
