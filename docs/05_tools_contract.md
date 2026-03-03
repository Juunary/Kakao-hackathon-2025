# 05. Tools Contract (Permission-Controlled Tools)

## Principles
- Tools are the only way the agent can read or mutate banking data.
- Tools must:
  - validate inputs (Pydantic)
  - handle exceptions (try/except)
  - return structured JSON results with `ok`, `error_code`, `message`

## Tool allowlist
Only registered tools can be invoked. Unknown tool calls must be rejected.

## Tool results: common shape
```json
{
  "ok": true,
  "data": { },
  "error_code": null,
  "message": null
}
```

## Tools (Phase 2)

### 1) get_account_balance(user_id: str) — READ

**Purpose:** Read account balance for a user.

**Returns**

```json

{
  "ok": true,
  "data": {
    "balance_krw": 125000,
    "masked_account": "****-****-**34"
  },
  "error_code": null,
  "message": null
}
```

### 2) get_recent_transactions(user_id: str, limit: int) — READ

**Purpose:** Fetch the last N transactions (max limit enforced, e.g., 20).

**Returns**

```json

{
  "ok": true,
  "data": {
    "transactions": [
      {
        "timestamp": "2026-03-03T09:12:00+09:00",
        "type": "debit",
        "amount_krw": 12000,
        "counterparty_masked": "Coffee Shop",
        "memo": "Latte"
      }
    ]
  },
  "error_code": null,
  "message": null
}
```

### 3) transfer_funds(from_user_id: str, to_account: str, amount: int) — EXECUTE (confirmation-gated)

**Purpose:** Create a transfer draft and return `approval_required=true`.
Final execution must only happen after an explicit Active Button confirmation event.

**Expected behavior**

- Phase 2: create draft + return token (no balance change yet)
- Phase 3: server-side finalization after confirmation event

**Returns (draft created)**

```json

{
  "ok": true,
  "data": {
    "approval_required": true,
    "action_token": "act_opaque_token",
    "draft": {
      "from_user_id": "u_123",
      "to_account_masked": "****-****-**77",
      "amount_krw": 50000
    }
  },
  "error_code": null,
  "message": null
}
```

## Defensive coding requirements

- Do not crash on missing/invalid args.
- Enforce strict ranges (amount > 0, limit bounds, account format sanity checks).
- Always return `ok=false` with a safe error message on failure.

## Logging

Log:

- `tool_name`
- `duration_ms`
- `ok` / `error_code`
- Never log raw account numbers or sensitive payloads.