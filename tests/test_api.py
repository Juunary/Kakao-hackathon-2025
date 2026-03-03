"""
tests/test_api.py — Deterministic pytest suite. No OPENAI_API_KEY required.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── 1. Health check ──────────────────────────────────────────────────────────
def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


# ── 2. Voice turn — fallback without API key ─────────────────────────────────
def test_agent_turn_voice_stub_or_fallback_without_key():
    resp = client.post(
        "/api/v1/agent/turn",
        json={
            "session_id": "test_voice_001",
            "user_id": "u_001",
            "input": {"type": "voice", "text": "잔액 알려줘"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    # Contract fields must all be present
    assert "request_id" in body
    assert "tts_text" in body
    assert "haptics" in body
    assert "pattern" in body["haptics"]
    assert "audio_cue" in body
    assert "id" in body["audio_cue"]
    assert "meta" in body
    assert "mode" in body["meta"]
    assert "tools_used" in body["meta"]
    assert "approval_required" in body["meta"]
    assert "next_expected_controls" in body
    # tts_text must be a non-empty string
    assert isinstance(body["tts_text"], str)
    assert len(body["tts_text"]) > 0


# ── 3. NEXT event with no loaded transactions ─────────────────────────────────
def test_control_event_next_without_transactions():
    # Fresh session — no transactions loaded yet
    resp = client.post(
        "/api/v1/agent/turn",
        json={
            "session_id": "test_next_fresh_001",
            "user_id": "u_001",
            "input": {"type": "control", "event": "NEXT"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    # Should return an error message (no transactions), not crash
    assert body["haptics"]["pattern"] == "ERROR_BUZZ"
    assert body["meta"]["approval_required"] is False
    assert "REPEAT" in body["next_expected_controls"]
    assert len(body["tts_text"]) > 0


# ── 4. CANCEL resets mode and clears pending state ───────────────────────────
def test_cancel_resets_state():
    resp = client.post(
        "/api/v1/agent/turn",
        json={
            "session_id": "test_cancel_001",
            "user_id": "u_001",
            "input": {"type": "control", "event": "CANCEL"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["mode"] == "idle"
    assert body["meta"]["approval_required"] is False
    assert body["haptics"]["pattern"] == "CANCEL_BUZZ"
    assert "REPEAT" in body["next_expected_controls"]
