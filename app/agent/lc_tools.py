"""
agent/lc_tools.py — LangChain tool wrappers around permission-controlled functions.

The LLM sees these tool definitions. Under the hood each wrapper
delegates to the corresponding function in app/tools/, which is
the only layer allowed to touch the database.
"""

import json

from langchain_core.tools import tool

from app.tools.balance import get_account_balance as _get_balance
from app.tools.transactions import get_recent_transactions as _get_txns
from app.tools.transfer import transfer_funds as _transfer


@tool
def get_account_balance(user_id: str) -> str:
    """잔액 조회. 사용자의 계좌 잔액을 반환합니다."""
    result = _get_balance(user_id=user_id)
    return json.dumps(result, ensure_ascii=False)


@tool
def get_recent_transactions(user_id: str, limit: int = 5) -> str:
    """최근 거래 내역 조회. 최신순으로 최대 20건까지 반환합니다."""
    result = _get_txns(user_id=user_id, limit=limit)
    return json.dumps(result, ensure_ascii=False)


@tool
def transfer_funds(from_user_id: str, to_account: str, amount: int) -> str:
    """이체 초안 생성. 실제 이체는 사용자 확인(CONFIRM) 후에만 실행됩니다."""
    result = _transfer(from_user_id=from_user_id, to_account=to_account, amount=amount)
    return json.dumps(result, ensure_ascii=False)


LC_TOOLS = [get_account_balance, get_recent_transactions, transfer_funds]
