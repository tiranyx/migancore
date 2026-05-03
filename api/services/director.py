"""
LangGraph Director — StateGraph orchestrator for MiganCore agents.

Replaces the plain for-loop in _run_agentic_loop with a proper
state machine. Benefits over plain loop:
  - Explicit node boundaries → easier to insert tracing/observability
  - Conditional routing is declarative → easy to add new branches (e.g. reflection)
  - State is a typed snapshot → debug-friendly, testable in isolation

Graph topology:
  START → reason → [execute_tools → reason]* → END

Nodes:
  reason         — main LLM call with optional tool spec (Ollama chat_with_tools)
  execute_tools  — dispatch all tool calls via ToolExecutor, inject role:tool messages

Routing (after reason):
  → execute_tools   if last assistant message has tool_calls AND iteration < MAX
  → END             otherwise (no tools, or circuit breaker hit)

After execute_tools:
  → reason          always (continue reasoning loop)

State fields (all plain Python — no checkpoint serialization needed):
  messages        list[dict]    full Ollama message history
  tools_spec      list[dict]    Ollama tool definitions (read-only after init)
  tool_ctx        ToolContext   tenant_id + agent_id
  model           str           Ollama model name
  options         dict          Ollama inference options
  tool_calls      list[dict]    accumulated tool call records
  iteration       int           current loop count (circuit breaker)
  final_response  str           set by reason when done
  reasoning_trace list[str]     human-readable node visit log
"""

import json
from typing import TypedDict

import structlog
from langgraph.graph import StateGraph, END

from services.ollama import OllamaClient
from services.tool_executor import ToolExecutor, ToolContext

logger = structlog.get_logger()

MAX_TOOL_ITERATIONS = 5
MAX_TOKENS = 1024


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    messages: list[dict]
    tools_spec: list[dict]
    tool_ctx: ToolContext
    model: str
    options: dict
    tool_calls: list[dict]
    iteration: int
    final_response: str
    reasoning_trace: list[str]


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

async def reason_node(state: AgentState) -> dict:
    """Main LLM reasoning step.

    Calls Ollama with tools if tools_spec is non-empty and under iteration limit.
    Sets final_response when done (no tool_calls returned).
    """
    messages = state["messages"]
    tools_spec = state["tools_spec"]
    model = state["model"]
    options = state["options"]
    iteration = state["iteration"]
    trace = list(state["reasoning_trace"])

    use_tools = bool(tools_spec) and iteration < MAX_TOOL_ITERATIONS
    trace.append(f"reason[{iteration}] model={model} tools={use_tools}")
    logger.info("director.reason", iteration=iteration, model=model, tools=use_tools)

    async with OllamaClient() as client:
        if use_tools:
            try:
                resp = await client.chat_with_tools(model, messages, tools_spec, options)
            except Exception as exc:
                # Ollama version may not support tool calling (e.g. 404)
                # Fallback to plain chat without tools
                logger.warning("director.tools_unsupported", error=str(exc), fallback="plain_chat")
                resp = await client.chat(model, messages, options=options)
        else:
            resp = await client.chat(model, messages, options=options)

    assistant = resp.get("message", {})
    content = assistant.get("content", "").strip()
    tool_calls = assistant.get("tool_calls", [])

    new_messages = list(messages)
    entry: dict = {"role": "assistant", "content": content}
    if tool_calls:
        entry["tool_calls"] = tool_calls
    new_messages.append(entry)

    updates: dict = {"messages": new_messages, "reasoning_trace": trace}
    if not tool_calls:
        updates["final_response"] = content or "[No response from model]"
    return updates


async def execute_tools_node(state: AgentState) -> dict:
    """Execute all pending tool calls from the last assistant message.

    Injects a role:tool result message for each call so Ollama can
    reference the results in the next reason iteration.
    """
    messages = list(state["messages"])
    tool_ctx = state["tool_ctx"]
    tool_calls_acc = list(state["tool_calls"])
    iteration = state["iteration"]
    trace = list(state["reasoning_trace"])

    pending = messages[-1].get("tool_calls", [])
    executor = ToolExecutor(tool_ctx)

    for tc in pending:
        fn = tc.get("function", {})
        skill_id = fn.get("name", "")
        arguments = fn.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}

        result = await executor.execute(skill_id, arguments)
        tool_calls_acc.append({
            "skill_id": skill_id,
            "arguments": arguments,
            "result": result,
            "iteration": iteration,
        })
        messages.append({
            "role": "tool",
            "content": json.dumps(
                result.get("result") or {"error": result.get("error")},
                ensure_ascii=False,
            ),
        })
        status = "ok" if result["success"] else "err"
        trace.append(f"tool[{iteration}] {skill_id} → {status}")
        logger.info("director.tool", skill=skill_id, ok=result["success"], iteration=iteration)

    return {
        "messages": messages,
        "tool_calls": tool_calls_acc,
        "iteration": iteration + 1,
        "reasoning_trace": trace,
    }


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _route_after_reason(state: AgentState) -> str:
    """Continue tool loop or end? Checks last message for pending tool_calls."""
    messages = state["messages"]
    iteration = state["iteration"]
    last = messages[-1] if messages else {}
    if last.get("tool_calls") and iteration < MAX_TOOL_ITERATIONS:
        return "execute_tools"
    return "done"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _build_director():
    graph = StateGraph(AgentState)
    graph.add_node("reason", reason_node)
    graph.add_node("execute_tools", execute_tools_node)
    graph.set_entry_point("reason")
    graph.add_conditional_edges(
        "reason",
        _route_after_reason,
        {"execute_tools": "execute_tools", "done": END},
    )
    graph.add_edge("execute_tools", "reason")
    return graph.compile()


_director = None


def _get_director():
    global _director
    if _director is None:
        _director = _build_director()
    return _director


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def run_director(
    model: str,
    messages: list[dict],
    tools_spec: list[dict],
    tool_ctx: ToolContext,
    options: dict | None = None,
) -> tuple[str, list[dict], list[str]]:
    """Run the LangGraph director graph.

    Returns:
        (final_response, tool_calls, reasoning_trace)
        - final_response: last assistant text content
        - tool_calls: all tool calls executed with results
        - reasoning_trace: list of node visit strings for debugging
    """
    director = _get_director()
    initial: AgentState = {
        "messages": messages,
        "tools_spec": tools_spec,
        "tool_ctx": tool_ctx,
        "model": model,
        "options": options or {"num_predict": MAX_TOKENS, "temperature": 0},
        "tool_calls": [],
        "iteration": 0,
        "final_response": "",
        "reasoning_trace": [],
    }
    final = await director.ainvoke(initial)
    return final["final_response"], final["tool_calls"], final["reasoning_trace"]
