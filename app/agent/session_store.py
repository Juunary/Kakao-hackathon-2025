"""
agent/session_store.py — In-memory cross-turn session persistence.

Stores fields that must survive between HTTP requests for the same session
(e.g., last_transactions for NEXT/PREV navigation, pending transfer token).

Replace with Redis or DB-backed store in production.
"""

from __future__ import annotations

_PERSISTENT_KEYS = [
    "mode",
    "last_transactions",
    "list_cursor",
    "pending_action_token",
    "last_tts_text",
]

_DEFAULT_SESSION: dict = {
    "mode": "idle",
    "last_transactions": None,
    "list_cursor": 0,
    "pending_action_token": None,
    "last_tts_text": "",
}

_store: dict[str, dict] = {}


def load_session(session_id: str) -> dict:
    """Return persisted fields for a session (or defaults if new)."""
    return dict(_store.get(session_id, _DEFAULT_SESSION))


def save_session(session_id: str, state: dict) -> None:
    """Persist the relevant fields from an AgentState after a turn."""
    _store[session_id] = {k: state.get(k, _DEFAULT_SESSION.get(k)) for k in _PERSISTENT_KEYS}
