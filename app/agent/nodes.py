"""
agent/nodes.py — All LangGraph node functions.

Node contract: each function receives AgentState and returns a
partial dict that is merged into the state by the graph runtime.
"""

from __future__ import annotations

import json
import logging
import os
import time

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.agent.lc_tools import LC_TOOLS
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.state import AgentState
from app.observability import log_event
from app.tools.transfer import confirm_transfer

load_dotenv()

logger = logging.getLogger(__name__)

_MAX_ITERATIONS = 3

# ── LLM (initialised once) ──────────────────────────────────────────────────
_llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY", ""),
)
_llm_with_tools = _llm.bind_tools(LC_TOOLS)


# ── Helpers ─────────────────────────────────────────────────────────────────
def _controls_for_mode(mode: str, has_pending: bool) -> list[str]:
    if mode == "reading_transactions":
        return ["NEXT", "PREV", "REPEAT", "CANCEL"]
    if mode == "awaiting_transfer_confirmation" or has_pending:
        return ["CONFIRM", "CANCEL", "REPEAT"]
    return ["REPEAT"]


def _haptics_for_mode(mode: str) -> str:
    if mode == "reading_transactions":
        return "ITEM_TICK"
    if mode == "awaiting_transfer_confirmation":
        return "ALERT_DOUBLE"
    return "SUCCESS_SINGLE"


def _fmt_transaction(txn: dict, index: int, total: int) -> str:
    ttype = "입금" if txn["type"] == "credit" else "출금"
    amount = txn["amount_krw"]
    counterparty = txn["counterparty_masked"]
    memo = f', {txn["memo"]}' if txn.get("memo") else ""
    return f"{index + 1}번째 거래입니다. {ttype}, {amount:,}원, {counterparty}{memo}. 총 {total}건 중 {index + 1}번째입니다."


# ── Nodes ────────────────────────────────────────────────────────────────────
def router_node(state: AgentState) -> dict:
    """Entry node — no state changes, routing is done via conditional edges."""
    return {}


def planner_node(state: AgentState) -> dict:
    """Call the LLM with the current conversation and tools bound."""
    msgs = list(state.get("messages", []))

    if not msgs or not isinstance(msgs[0], SystemMessage):
        ctx = f"\n\n현재 사용자 ID: {state['current_user_id']}"
        msgs = [SystemMessage(content=SYSTEM_PROMPT + ctx)] + msgs

    # ── LLM call with timing ────────────────────────────────────────────────
    llm_start = time.monotonic()
    llm_ok = False
    try:
        response = _llm_with_tools.invoke(msgs)
        llm_ok = True
    except Exception as exc:
        llm_duration_ms = round((time.monotonic() - llm_start) * 1000, 1)
        log_event(
            logger,
            "llm_call_error",
            node="planner",
            session_id=state.get("session_id", ""),
            iteration=state.get("iterations", 0) + 1,
            error=str(exc),
            duration_ms=llm_duration_ms,
        )
        response = AIMessage(content="죄송합니다. 잠시 후 다시 말씀해 주세요.")
    else:
        llm_duration_ms = round((time.monotonic() - llm_start) * 1000, 1)
        # Extract token usage (available in langchain-openai 1.x via usage_metadata)
        usage = getattr(response, "usage_metadata", None) or {}
        log_event(
            logger,
            "llm_call",
            node="planner",
            session_id=state.get("session_id", ""),
            iteration=state.get("iterations", 0) + 1,
            duration_ms=llm_duration_ms,
            has_tool_calls=bool(getattr(response, "tool_calls", None)),
            prompt_tokens=usage.get("input_tokens"),
            completion_tokens=usage.get("output_tokens"),
            total_tokens=usage.get("total_tokens"),
        )

    tools_used = list(state.get("tools_used", []))
    if hasattr(response, "tool_calls") and response.tool_calls:
        tools_used += [tc["name"] for tc in response.tool_calls]

    return {
        "messages": [response],
        "iterations": state.get("iterations", 0) + 1,
        "tools_used": tools_used,
    }


def tool_executor_node(state: AgentState) -> dict:
    """Execute all tool calls in the last AIMessage using the allowlist."""
    from app.tools import TOOL_REGISTRY

    last_msg = state["messages"][-1]
    tool_messages: list[ToolMessage] = []
    updates: dict = {}

    for tc in last_msg.tool_calls:
        name = tc["name"]
        args = tc["args"]

        if name not in TOOL_REGISTRY:
            raw = {"ok": False, "error_code": "TOOL_NOT_ALLOWED",
                   "message": f"Tool '{name}' is not in the allowlist."}
        else:
            try:
                raw = TOOL_REGISTRY[name](**args)
            except Exception as exc:
                # Tool-level timing already logged inside each tool's finally block
                log_event(logger, "tool_exec_error", tool=name, error=str(exc))
                raw = {"ok": False, "error_code": "TOOL_EXEC_ERROR", "message": str(exc)}

        # Side-effects: update session state from tool results
        if name == "get_recent_transactions" and raw.get("ok"):
            updates["last_transactions"] = raw["data"]["transactions"]
            updates["list_cursor"] = 0
            updates["mode"] = "reading_transactions"

        if name == "transfer_funds" and raw.get("ok"):
            updates["pending_action_token"] = raw["data"]["action_token"]
            updates["mode"] = "awaiting_transfer_confirmation"
            updates["approval_required"] = True

        tool_messages.append(
            ToolMessage(
                content=json.dumps(raw, ensure_ascii=False),
                tool_call_id=tc["id"],
                name=name,
            )
        )

    return {"messages": tool_messages, **updates}


def control_handler_node(state: AgentState) -> dict:
    """Handle hardware button events without LLM overhead."""
    event = state.get("control_event", "")
    mode = state.get("mode", "idle")
    txns = state.get("last_transactions") or []
    cursor = state.get("list_cursor", 0)
    token = state.get("pending_action_token")

    if event == "NEXT":
        if not txns:
            tts = "표시할 거래 내역이 없습니다. 먼저 거래 내역을 조회해 주세요."
            return {"tts_text": tts, "haptics_pattern": "ERROR_BUZZ",
                    "audio_cue_id": "NONE", "next_expected_controls": ["REPEAT"],
                    "approval_required": False}
        new_cursor = min(cursor + 1, len(txns) - 1)
        tts = _fmt_transaction(txns[new_cursor], new_cursor, len(txns))
        end_hint = " 마지막 항목입니다." if new_cursor == len(txns) - 1 else ""
        return {
            "tts_text": tts + end_hint,
            "haptics_pattern": "ITEM_TICK",
            "audio_cue_id": "NONE",
            "list_cursor": new_cursor,
            "next_expected_controls": ["NEXT", "PREV", "REPEAT", "CANCEL"],
            "approval_required": False,
        }

    if event == "PREV":
        if not txns:
            tts = "표시할 거래 내역이 없습니다."
            return {"tts_text": tts, "haptics_pattern": "ERROR_BUZZ",
                    "audio_cue_id": "NONE", "next_expected_controls": ["REPEAT"],
                    "approval_required": False}
        new_cursor = max(cursor - 1, 0)
        tts = _fmt_transaction(txns[new_cursor], new_cursor, len(txns))
        return {
            "tts_text": tts,
            "haptics_pattern": "ITEM_TICK",
            "audio_cue_id": "NONE",
            "list_cursor": new_cursor,
            "next_expected_controls": ["NEXT", "PREV", "REPEAT", "CANCEL"],
            "approval_required": False,
        }

    if event == "REPEAT":
        last = state.get("last_tts_text", "")
        tts = last if last else "반복할 내용이 없습니다."
        return {
            "tts_text": tts,
            "haptics_pattern": "NONE",
            "audio_cue_id": "NONE",
            "next_expected_controls": _controls_for_mode(mode, bool(token)),
            "approval_required": bool(token),
        }

    if event == "CONFIRM":
        if not token:
            return {
                "tts_text": "확인할 이체 요청이 없습니다.",
                "haptics_pattern": "ERROR_BUZZ",
                "audio_cue_id": "NONE",
                "next_expected_controls": ["REPEAT"],
                "approval_required": False,
            }
        result = confirm_transfer(token)
        if result["ok"]:
            amount = result["data"]["transferred_krw"]
            to_acc = result["data"]["to_account_masked"]
            tts = f"이체가 완료되었습니다. {to_acc}에 {amount:,}원을 보냈습니다."
            return {
                "tts_text": tts,
                "haptics_pattern": "SUCCESS_DOUBLE",
                "audio_cue_id": "SUCCESS",
                "mode": "idle",
                "pending_action_token": None,
                "next_expected_controls": ["REPEAT"],
                "approval_required": False,
            }
        else:
            tts = f"이체에 실패했습니다. {result.get('message', '잠시 후 다시 시도해 주세요.')}"
            return {
                "tts_text": tts,
                "haptics_pattern": "ERROR_BUZZ",
                "audio_cue_id": "ERROR",
                "next_expected_controls": ["REPEAT"],
                "approval_required": False,
            }

    if event == "CANCEL":
        had_pending = bool(token)
        tts = "이체 요청이 취소되었습니다." if had_pending else "취소되었습니다."
        return {
            "tts_text": tts,
            "haptics_pattern": "CANCEL_BUZZ",
            "audio_cue_id": "NONE",
            "mode": "idle",
            "pending_action_token": None,
            "next_expected_controls": ["REPEAT"],
            "approval_required": False,
        }

    return {
        "tts_text": "알 수 없는 버튼 입력입니다.",
        "haptics_pattern": "ERROR_BUZZ",
        "audio_cue_id": "NONE",
        "next_expected_controls": ["REPEAT"],
        "approval_required": False,
    }


def finalizer_node(state: AgentState) -> dict:
    """
    Extract tts_text from the last non-tool-call AIMessage.
    Set haptics, audio_cue, and next_expected_controls based on state.
    """
    if state.get("input_type") == "control":
        mode = state.get("mode", "idle")
        token = state.get("pending_action_token")
        return {
            "last_tts_text": state.get("tts_text", ""),
            "next_expected_controls": _controls_for_mode(mode, bool(token)),
        }

    tts = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            tts = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    if not tts:
        tts = "죄송합니다. 잠시 후 다시 말씀해 주세요."

    mode = state.get("mode", "idle")
    token = state.get("pending_action_token")
    haptics = _haptics_for_mode(mode)
    controls = _controls_for_mode(mode, bool(token))

    return {
        "tts_text": tts,
        "haptics_pattern": haptics,
        "audio_cue_id": "NONE",
        "next_expected_controls": controls,
        "approval_required": bool(token),
        "last_tts_text": tts,
    }
