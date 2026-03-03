"""
main.py — FastAPI application entry point (Phase 3 + Phase 4 observability).

Endpoints:
  GET  /healthz              → { "ok": true }
  POST /api/v1/agent/turn    → TurnResponse (real LangGraph agent)
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Literal, Union

from fastapi import FastAPI, HTTPException, Request
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.agent.graph import agent_graph
from app.agent.session_store import load_session, save_session
from app.database import init_db
from app.observability import log_event, mask_user_id, timed_block

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: initialise DB on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Multisensory Banking API", version="0.4.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# HTTP-level timing middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def http_timing_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 1)
    log_event(
        logger,
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class VoiceInput(BaseModel):
    type: Literal["voice"]
    text: str


class ControlInput(BaseModel):
    type: Literal["control"]
    event: Literal["NEXT", "PREV", "REPEAT", "CONFIRM", "CANCEL"]


class DeviceContext(BaseModel):
    volume_level: float = 0.5
    haptics_enabled: bool = True


class TurnRequest(BaseModel):
    session_id: str
    user_id: str
    input: Union[VoiceInput, ControlInput] = Field(discriminator="type")
    device_context: DeviceContext = Field(default_factory=DeviceContext)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class HapticsPayload(BaseModel):
    pattern: str


class AudioCue(BaseModel):
    id: str


class Meta(BaseModel):
    mode: str
    tools_used: list[str]
    approval_required: bool


class TurnResponse(BaseModel):
    request_id: str
    tts_text: str
    haptics: HapticsPayload
    audio_cue: AudioCue
    meta: Meta
    next_expected_controls: list[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/api/v1/agent/turn", response_model=TurnResponse)
def agent_turn(req: TurnRequest) -> TurnResponse:
    """
    Process one turn through the LangGraph agent.
    Loads/saves cross-turn session state (mode, transactions, pending transfers).
    """
    request_id = str(uuid.uuid4())
    control_event = req.input.event if req.input.type == "control" else None

    # ── Build initial state ──────────────────────────────────────────────────
    session = load_session(req.session_id)

    if req.input.type == "voice":
        messages = [HumanMessage(content=req.input.text)]
        input_type = "voice"
    else:
        messages = []
        input_type = "control"

    initial_state = {
        "session_id": req.session_id,
        "current_user_id": req.user_id,
        "input_type": input_type,
        "voice_text": req.input.text if input_type == "voice" else None,
        "control_event": control_event,
        "haptics_enabled": req.device_context.haptics_enabled,
        "messages": messages,
        "mode": session["mode"],
        "last_transactions": session["last_transactions"],
        "list_cursor": session["list_cursor"],
        "pending_action_token": session["pending_action_token"],
        "last_tts_text": session["last_tts_text"],
        "iterations": 0,
        "tools_used": [],
        "tts_text": "",
        "haptics_pattern": "NONE",
        "audio_cue_id": "NONE",
        "approval_required": False,
        "next_expected_controls": ["REPEAT"],
    }

    # ── Run graph with timing ────────────────────────────────────────────────
    try:
        with timed_block(logger, "agent_graph_invoke") as meta:
            final_state = agent_graph.invoke(initial_state)
            meta["session_id"] = req.session_id
            meta["request_id"] = request_id
    except Exception as exc:
        log_event(
            logger,
            "agent_graph_error",
            level=logging.ERROR,
            request_id=request_id,
            session_id=req.session_id,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail="Agent error. Please try again.")

    # ── Persist updated session fields ───────────────────────────────────────
    save_session(req.session_id, final_state)

    # ── Structured turn log ──────────────────────────────────────────────────
    log_event(
        logger,
        "agent_turn",
        request_id=request_id,
        session_id=req.session_id,
        user_id=mask_user_id(req.user_id),
        input_type=input_type,
        control_event=control_event,
        mode=final_state.get("mode", "idle"),
        iterations=final_state.get("iterations", 0),
        tools_used=final_state.get("tools_used", []),
        approval_required=final_state.get("approval_required", False),
    )

    # ── Build response ───────────────────────────────────────────────────────
    return TurnResponse(
        request_id=request_id,
        tts_text=final_state.get("tts_text") or "죄송합니다. 다시 말씀해 주세요.",
        haptics=HapticsPayload(pattern=final_state.get("haptics_pattern", "NONE")),
        audio_cue=AudioCue(id=final_state.get("audio_cue_id", "NONE")),
        meta=Meta(
            mode=final_state.get("mode", "idle"),
            tools_used=final_state.get("tools_used", []),
            approval_required=final_state.get("approval_required", False),
        ),
        next_expected_controls=final_state.get("next_expected_controls", ["REPEAT"]),
    )
