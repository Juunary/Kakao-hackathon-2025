"""
tools/__init__.py — Tool registry (allowlist).

Only functions listed in TOOL_REGISTRY may be invoked by the agent.
The registry maps tool name → callable.
"""

from app.tools.balance import get_account_balance
from app.tools.transactions import get_recent_transactions
from app.tools.transfer import transfer_funds

TOOL_REGISTRY: dict = {
    "get_account_balance": get_account_balance,
    "get_recent_transactions": get_recent_transactions,
    "transfer_funds": transfer_funds,
}

__all__ = [
    "TOOL_REGISTRY",
    "get_account_balance",
    "get_recent_transactions",
    "transfer_funds",
]
