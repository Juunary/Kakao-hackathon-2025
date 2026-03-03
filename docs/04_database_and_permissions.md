# 04. Database & Permission-Controlled Access

## Goal
Prevent the LLM/agent from performing arbitrary DB access. The agent can only perform
allowed operations via predefined functions (tools).

## Phase 1 minimal schema
### Users
- user_id (PK, string)
- display_name (optional)
- created_at

### Accounts
- account_id (PK)
- user_id (FK)
- balance_krw (int)
- updated_at

### (Optional for Phase 2+) Transactions
- transaction_id (PK)
- user_id (FK)
- timestamp
- type (debit/credit)
- amount_krw (int)
- counterparty_masked (string)
- memo (string, optional)

## Permission pattern
- `database.py` defines engine/session/models only.
- Tools/repositories implement fixed queries (no free-form SQL).
- Agent code must not import DB engine/session or build queries directly.

## Hard prohibitions
- Any tool that accepts raw SQL text
- Any “query tool” that runs arbitrary SELECT/UPDATE from LLM-generated strings
- Any prompt pattern that encourages SQL generation

## Error handling
- Return structured errors from tools instead of raising uncaught exceptions.
- Never leak stack traces to clients.