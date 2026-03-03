"""
agent/state.py — AgentState TypedDict for the LangGraph graph.

All fields in this dict flow through every node in the graph.
Persistent fields (mode, last_transactions, list_cursor,
pending_action_token, last_tts_text) are saved/restored by
session_store between HTTP requests.
"""

from __future__ import annotations

from typing import Annotated, Optional
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # ── Input ────────────────────────────────────────────────
    session_id: str
    current_user_id: str
    input_type: str           # "voice" | "control"
    voice_text: Optional[str]
    control_event: Optional[str]  # "NEXT"|"PREV"|"REPEAT"|"CONFIRM"|"CANCEL"
    haptics_enabled: bool

    # ── LLM conversation (accumulated within one turn) ───────
    messages: Annotated[list[BaseMessage], add_messages]

    # ── Session context (persisted between turns) ────────────
    mode: str   # "idle" | "reading_transactions" | "awaiting_transfer_confirmation"
    last_transactions: Optional[list]
    list_cursor: int
    pending_action_token: Optional[str]
    last_tts_text: str        # used by REPEAT handler

    # ── Loop guard ───────────────────────────────────────────
    iterations: int

    # ── Output (set by finalizer_node / control_handler_node) ─
    tts_text: str
    haptics_pattern: str
    audio_cue_id: str
    tools_used: list[str]
    approval_required: bool
    next_expected_controls: list[str]
