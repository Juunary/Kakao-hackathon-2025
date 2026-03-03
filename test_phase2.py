"""
test_phase2.py — Quick smoke-test for all Phase 2 tools.
Run: python test_phase2.py
"""

import json
from app.database import init_db
from app.tools import get_account_balance, get_recent_transactions, transfer_funds
from app.tools.transfer import confirm_transfer

def pretty(label: str, result: dict) -> None:
    print(f"\n{'='*50}")
    print(f"  {label}")
    print('='*50)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    # Initialise DB (idempotent)
    init_db()
    print("DB initialised.")

    # 1. Balance — happy path
    pretty("get_account_balance(u_001)", get_account_balance("u_001"))

    # 2. Balance — unknown user
    pretty("get_account_balance(unknown)", get_account_balance("unknown_user"))

    # 3. Transactions — 3 most recent
    pretty("get_recent_transactions(u_001, 3)", get_recent_transactions("u_001", 3))

    # 4. Transactions — limit too large (should error)
    pretty("get_recent_transactions(u_001, 99)", get_recent_transactions("u_001", 99))

    # 5. Transfer — create draft
    result = transfer_funds("u_001", "110-123-456789", 50_000)
    pretty("transfer_funds(u_001, ..., 50000)", result)

    if result["ok"]:
        token = result["data"]["action_token"]

        # 6. Confirm transfer
        pretty(f"confirm_transfer({token})", confirm_transfer(token))

        # 7. Double-confirm should fail
        pretty("confirm_transfer(same token again)", confirm_transfer(token))

    # 8. Transfer — insufficient balance
    pretty(
        "transfer_funds(u_001, ..., 99_999_999) [insufficient]",
        transfer_funds("u_001", "110-123-456789", 99_999_999),
    )

    # 9. Transfer — invalid amount
    pretty(
        "transfer_funds(u_001, ..., -100) [invalid]",
        transfer_funds("u_001", "110-123-456789", -100),
    )
