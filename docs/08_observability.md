# 08. Observability (Logging & Metrics)

## Goals
- Debuggability: trace why a tool was called and what happened
- Safety: detect forbidden actions and abnormal loops
- Performance: tool latency and LLM usage visibility

## Minimum logging fields
- request_id (trace id)
- session_id (opaque)
- user_id (masked or hashed)
- input.type (voice/control)
- control event (if present)
- tools_used
- tool_duration_ms
- agent_iterations
- pending_action_type (if any)
- (optional) token usage: prompt/completion/total

## Sensitive logging rules
- Never log full account numbers
- Never log raw personal data
- Mask or hash identifiers where possible