"""
tools/transfer.py — transfer_funds tool.

Permission: EXECUTE — confirmation-gated (two-phase commit).
Phase 2: Creates a pending draft + returns action_token. No balance change yet.
Phase 3: confirm_transfer() finalises after CONFIRM event.
"""

import logging
import time
import uuid

from pydantic import BaseModel, field_validator

from app.database import create_session, Account

logger = logging.getLogger(__name__)

# In-memory pending transfer store  {action_token: draft_dict}
# Replaced by DB-backed store in Phase 3.
_pending: dict[str, dict] = {}


class TransferInput(BaseModel):
    from_user_id: str
    to_account: str
    amount: int

    @field_validator("from_user_id")
    @classmethod
    def from_user_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("from_user_id must not be empty")
        return v.strip()

    @field_validator("to_account")
    @classmethod
    def to_account_format(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("to_account must not be empty")
        return v.strip()

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v


def transfer_funds(from_user_id: str, to_account: str, amount: int) -> dict:
    """
    Create a pending transfer draft (Phase 2 — no balance change).

    Returns:
        {
            "ok": bool,
            "data": {
                "approval_required": True,
                "action_token": str,
                "draft": {"from_user_id": str, "to_account_masked": str, "amount_krw": int}
            } | None,
            "error_code": str | None,
            "message": str | None,
        }
    """
    start = time.monotonic()
    ok = False
    error_code = None

    try:
        inp = TransferInput(from_user_id=from_user_id, to_account=to_account, amount=amount)
    except Exception as exc:
        logger.warning(f"tool=transfer_funds validation_error={exc}")
        return {"ok": False, "data": None, "error_code": "INVALID_INPUT", "message": str(exc)}

    try:
        # Verify sender account exists and has sufficient balance
        balance_krw = None
        with create_session() as db:
            account = db.query(Account).filter(Account.user_id == inp.from_user_id).first()
            if account is None:
                error_code = "USER_NOT_FOUND"
                return {
                    "ok": False,
                    "data": None,
                    "error_code": error_code,
                    "message": "Sender account not found.",
                }
            balance_krw = account.balance_krw  # read inside session scope

        if balance_krw < inp.amount:
            error_code = "INSUFFICIENT_BALANCE"
            return {
                "ok": False,
                "data": None,
                "error_code": error_code,
                "message": "Insufficient balance for this transfer.",
            }

        # Mask destination account
        raw = inp.to_account.replace("-", "").replace(" ", "")
        suffix = raw[-2:] if len(raw) >= 2 else "**"
        to_masked = f"****-****-**{suffix}"

        # Create pending draft
        action_token = f"act_{uuid.uuid4().hex[:16]}"
        draft = {
            "from_user_id": inp.from_user_id,
            "to_account_masked": to_masked,
            "amount_krw": inp.amount,
        }
        _pending[action_token] = {**draft, "to_account_raw": inp.to_account}

        ok = True
        return {
            "ok": True,
            "data": {
                "approval_required": True,
                "action_token": action_token,
                "draft": draft,
            },
            "error_code": None,
            "message": None,
        }

    except Exception as exc:
        error_code = "INTERNAL_ERROR"
        logger.error(f"tool=transfer_funds unexpected_error={exc}")
        return {
            "ok": False,
            "data": None,
            "error_code": error_code,
            "message": "Unable to create transfer. Please try again.",
        }
    finally:
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            f"tool=transfer_funds from_user_id={from_user_id} amount={amount} ok={ok} "
            f"error_code={error_code} duration_ms={duration_ms:.1f}"
        )


def confirm_transfer(action_token: str) -> dict:
    """
    Phase 3 — finalise a pending transfer after CONFIRM event.
    Deducts balance from sender account.
    """
    start = time.monotonic()
    ok = False
    error_code = None

    draft = _pending.get(action_token)
    if not draft:
        return {
            "ok": False,
            "data": None,
            "error_code": "TOKEN_NOT_FOUND",
            "message": "Transfer token not found or already used.",
        }

    try:
        with create_session() as db:
            account = db.query(Account).filter(Account.user_id == draft["from_user_id"]).first()
            if not account or account.balance_krw < draft["amount_krw"]:
                error_code = "INSUFFICIENT_BALANCE"
                return {
                    "ok": False,
                    "data": None,
                    "error_code": error_code,
                    "message": "Insufficient balance at confirmation time.",
                }
            account.balance_krw -= draft["amount_krw"]

        del _pending[action_token]

        ok = True
        return {
            "ok": True,
            "data": {
                "transferred_krw": draft["amount_krw"],
                "to_account_masked": draft["to_account_masked"],
            },
            "error_code": None,
            "message": None,
        }

    except Exception as exc:
        error_code = "INTERNAL_ERROR"
        logger.error(f"tool=confirm_transfer unexpected_error={exc}")
        return {
            "ok": False,
            "data": None,
            "error_code": error_code,
            "message": "Transfer confirmation failed.",
        }
    finally:
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            f"tool=confirm_transfer token={action_token} ok={ok} "
            f"error_code={error_code} duration_ms={duration_ms:.1f}"
        )
