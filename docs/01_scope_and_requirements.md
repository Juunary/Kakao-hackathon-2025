# 01. Scope & Requirements

## Functional requirements

### FR1 — Balance
- Input: voice intent (“What’s my balance?”)
- Tool: `get_account_balance(user_id)`
- Output: TTS-friendly statement with clear currency and amount
- Feedback: success vibration pattern

### FR2 — Recent transactions
- Input: voice intent (“Read my last 5 transactions.”)
- Tool: `get_recent_transactions(user_id, limit)`
- Output:
  - reads one transaction at a time (TTS-friendly)
  - supports Volume Up / Volume Down navigation events
- Feedback:
  - short vibration per item
  - distinct vibration for “end of list”

### FR3 — Transfer funds (two-step, confirmation required)
- Step A (voice): user requests transfer
- Backend creates a **transfer draft** (no execution yet) and returns:
  - summary of recipient + amount
  - instruction: “Hold Active Button to confirm, press twice to cancel” (client-defined mapping)
  - `approval_required = true`
- Step B (control event): client sends an explicit Active Button confirmation event
- Backend executes the transfer (mocked) and returns:
  - completion message
  - completion vibration pattern

> Safety rule: the agent must never finalize a transfer without an explicit confirmation event.

## Non-functional requirements
- NFR1 Security: LLM cannot access DB directly; only allowlisted tool functions
- NFR2 Robustness: invalid/hallucinated tool args must not crash the server
- NFR3 Observability: log tool duration and request trace IDs
- NFR4 Accessibility: responses must be optimized for hearing + haptics + simple controls
- NFR5 Loop guardrails: cyclic agent must have a max iteration cap and safe fallback

## Data output / privacy
- Mask sensitive identifiers (account numbers) in responses and logs
- Avoid leaking private user data; only what is needed for the requested task