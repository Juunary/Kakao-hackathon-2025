"""
tools/transactions.py — get_recent_transactions tool.

Permission: READ — no state mutation.
"""

import logging
import time

from pydantic import BaseModel, field_validator

from app.database import create_session, Transaction

logger = logging.getLogger(__name__)

_MAX_LIMIT = 20


class TransactionsInput(BaseModel):
    user_id: str
    limit: int = 5

    @field_validator("user_id")
    @classmethod
    def user_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("user_id must not be empty")
        return v.strip()

    @field_validator("limit")
    @classmethod
    def limit_in_range(cls, v: int) -> int:
        if v < 1:
            raise ValueError("limit must be at least 1")
        if v > _MAX_LIMIT:
            raise ValueError(f"limit must not exceed {_MAX_LIMIT}")
        return v


def get_recent_transactions(user_id: str, limit: int = 5) -> dict:
    """
    Return the most recent transactions for a user (newest first).

    Returns:
        {
            "ok": bool,
            "data": {"transactions": list[dict]} | None,
            "error_code": str | None,
            "message": str | None,
        }
    """
    start = time.monotonic()
    ok = False
    error_code = None

    try:
        inp = TransactionsInput(user_id=user_id, limit=limit)
    except Exception as exc:
        logger.warning(f"tool=get_recent_transactions validation_error={exc}")
        return {"ok": False, "data": None, "error_code": "INVALID_INPUT", "message": str(exc)}

    try:
        with create_session() as db:
            rows = (
                db.query(Transaction)
                .filter(Transaction.user_id == inp.user_id)
                .order_by(Transaction.timestamp.desc())
                .limit(inp.limit)
                .all()
            )
            # Build dicts inside session scope to avoid detached-instance errors
            transactions = [
                {
                    "timestamp": row.timestamp.isoformat(),
                    "type": row.type,
                    "amount_krw": row.amount_krw,
                    "counterparty_masked": row.counterparty_masked,
                    "memo": row.memo,
                }
                for row in rows
            ]

        ok = True
        return {
            "ok": True,
            "data": {"transactions": transactions},
            "error_code": None,
            "message": None,
        }

    except Exception as exc:
        error_code = "INTERNAL_ERROR"
        logger.error(f"tool=get_recent_transactions unexpected_error={exc}")
        return {
            "ok": False,
            "data": None,
            "error_code": error_code,
            "message": "Unable to retrieve transactions. Please try again.",
        }
    finally:
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            f"tool=get_recent_transactions user_id={user_id} limit={limit} ok={ok} "
            f"error_code={error_code} duration_ms={duration_ms:.1f}"
        )
