"""
agent/graph.py — LangGraph cyclic state machine.

Graph topology:
  START
    └─► router
          ├─► planner ──► tool_executor ──► planner (loop, max 3)
          │       └─► finalizer ──► END
          └─► control_handler ──► finalizer ──► END
"""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    control_handler_node,
    finalizer_node,
    planner_node,
    router_node,
    tool_executor_node,
    _MAX_ITERATIONS,
)
from app.agent.state import AgentState

# ── Routing functions ────────────────────────────────────────────────────────

def _route_input(state: AgentState) -> str:
    """Router: voice → planner, control → control_handler."""
    if state.get("input_type") == "control":
        return "control_handler"
    return "planner"


def _route_after_planner(state: AgentState) -> str:
    """After planner: use tools (if LLM asked for them) or go to finalizer."""
    last = state["messages"][-1] if state.get("messages") else None
    if (
        isinstance(last, AIMessage)
        and getattr(last, "tool_calls", None)
        and state.get("iterations", 0) < _MAX_ITERATIONS
    ):
        return "tool_executor"
    return "finalizer"


# ── Build and compile graph ──────────────────────────────────────────────────

def build_graph() -> object:
    g = StateGraph(AgentState)

    g.add_node("router", router_node)
    g.add_node("planner", planner_node)
    g.add_node("tool_executor", tool_executor_node)
    g.add_node("control_handler", control_handler_node)
    g.add_node("finalizer", finalizer_node)

    g.add_edge(START, "router")

    g.add_conditional_edges(
        "router",
        _route_input,
        {"planner": "planner", "control_handler": "control_handler"},
    )

    g.add_conditional_edges(
        "planner",
        _route_after_planner,
        {"tool_executor": "tool_executor", "finalizer": "finalizer"},
    )

    # tool_executor always loops back to planner to process results
    g.add_edge("tool_executor", "planner")

    g.add_edge("control_handler", "finalizer")
    g.add_edge("finalizer", END)

    return g.compile()


# Compile once at import time
agent_graph = build_graph()
