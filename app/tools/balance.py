"""
tools/balance.py — get_account_balance tool.

Permission: READ — no state mutation.
"""

import logging
import time

from pydantic import BaseModel, field_validator

from app.database import create_session, Account

logger = logging.getLogger(__name__)


class BalanceInput(BaseModel):
    user_id: str

    @field_validator("user_id")
    @classmethod
    def user_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("user_id must not be empty")
        return v.strip()


def get_account_balance(user_id: str) -> dict:
    """
    Return the account balance for a user.

    Returns:
        {
            "ok": bool,
            "data": {"balance_krw": int, "masked_account": str} | None,
            "error_code": str | None,
            "message": str | None,
        }
    """
    start = time.monotonic()
    ok = False
    error_code = None

    try:
        inp = BalanceInput(user_id=user_id)
    except Exception as exc:
        logger.warning(f"tool=get_account_balance validation_error={exc}")
        return {"ok": False, "data": None, "error_code": "INVALID_INPUT", "message": str(exc)}

    try:
        balance_krw = None
        account_id = None
        with create_session() as db:
            account = db.query(Account).filter(Account.user_id == inp.user_id).first()
            if account is None:
                error_code = "USER_NOT_FOUND"
                return {
                    "ok": False,
                    "data": None,
                    "error_code": error_code,
                    "message": "Account not found for the given user.",
                }
            # Read inside session scope to avoid detached-instance errors
            balance_krw = account.balance_krw
            account_id = account.account_id

        suffix = account_id[-2:] if len(account_id) >= 2 else "**"
        masked = f"****-****-**{suffix}"

        ok = True
        return {
            "ok": True,
            "data": {"balance_krw": balance_krw, "masked_account": masked},
            "error_code": None,
            "message": None,
        }

    except Exception as exc:
        error_code = "INTERNAL_ERROR"
        logger.error(f"tool=get_account_balance unexpected_error={exc}")
        return {
            "ok": False,
            "data": None,
            "error_code": error_code,
            "message": "Unable to retrieve balance. Please try again.",
        }
    finally:
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            f"tool=get_account_balance user_id={user_id} ok={ok} "
            f"error_code={error_code} duration_ms={duration_ms:.1f}"
        )
