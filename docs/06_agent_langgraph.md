# 06. LangGraph Agent (Cyclic State Machine + Control Events)

## Goal
Use LangGraph to support:
- cyclic reasoning (planner ↔ checker)
- multimodal operation (voice + buttons)
- safe confirmations for high-risk actions

## AgentState (suggested)
- session_id: str
- current_user_id: str
- messages: list
- mode: str
  - "idle" | "reading_transactions" | "awaiting_transfer_confirmation"
- last_transactions: list | null
- list_cursor: int
- pending_action_token: str | null
- pending_action_type: str | null
- iterations: int

## Node responsibilities

### router_node
Routes the turn based on input type:
- voice → planner_node
- control event → control_handler_node

### planner_node
- Interpret the user’s voice request.
- Decide which tool(s) to call.
- For transactions, fetch once and store `last_transactions` in state.

### tool_executor_node
- Execute only allowlisted tools.
- Catch and structure errors.

### checker_node
- Verify tool outputs are sufficient.
- If missing info, loop back to planner (max iterations guard).
- Ensure safety rule: transfer must not be marked complete without confirmation.

### control_handler_node
Handles control inputs without heavy LLM usage when possible:
- NEXT / PREV (Volume buttons):
  - move cursor, read next/previous transaction item
- REPEAT (Active Button short press):
  - repeat last spoken content
- CONFIRM / CANCEL (Active Button long press / double press):
  - confirm: trigger transfer finalization (server-side confirmation layer)
  - cancel: clear pending action state and respond safely

### finalizer_node
Produces multisensory-friendly output:
- short sentences
- explicit numbers and currency
- includes haptic pattern and control hints

## Loop and safety guardrails
- max_iterations (e.g., 3)
- if exceeded: respond with a safe fallback asking the user to rephrase or confirm intent