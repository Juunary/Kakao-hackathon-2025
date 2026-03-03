"""
observability.py — Structured logging utilities.

All log lines emitted by this module are valid JSON objects so they can be
ingested by any log aggregator (CloudWatch, Datadog, Loki, etc.).

NEVER log raw account numbers, full balances from tool payloads, or
un-masked user PII.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from typing import Any, Generator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mask_user_id(user_id: str) -> str:
    """Return a safe-to-log version of user_id (first 2 chars + ***)."""
    if not user_id:
        return "***"
    if len(user_id) <= 3:
        return "***"
    return user_id[:2] + "***"


def _emit(logger: logging.Logger, level: int, payload: dict[str, Any]) -> None:
    logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))


def log_event(
    logger: logging.Logger,
    event: str,
    level: int = logging.INFO,
    **kwargs: Any,
) -> None:
    """Emit a structured log line: {"event": event, ...kwargs}."""
    _emit(logger, level, {"event": event, **kwargs})


# ---------------------------------------------------------------------------
# Context managers
# ---------------------------------------------------------------------------

@contextmanager
def timed_block(
    logger: logging.Logger,
    event: str,
    level: int = logging.INFO,
    **kwargs: Any,
) -> Generator[dict, None, None]:
    """
    Context manager that logs the wall-clock duration of a block.

    Usage:
        with timed_block(logger, "my_event", node="planner") as meta:
            result = do_work()
            meta["extra_key"] = "value"  # add fields after the fact
    """
    meta: dict[str, Any] = {}
    start = time.monotonic()
    try:
        yield meta
    finally:
        duration_ms = round((time.monotonic() - start) * 1000, 1)
        _emit(logger, level, {"event": event, "duration_ms": duration_ms, **kwargs, **meta})
