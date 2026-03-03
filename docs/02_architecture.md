# 02. Architecture

## Components
- **FastAPI Server**: API gateway for agent turns and control events
- **SQLite + SQLAlchemy**: mock persistence for users, accounts, transactions (optional)
- **Permission-Controlled Tools**: allowlisted functions that encapsulate DB access
- **LangGraph Agent**: cyclic state machine:
  - planner → tool_executor → checker → finalizer
- **Action Confirmation Layer** (server-side):
  - stores pending sensitive actions (e.g., transfer drafts)
  - requires explicit control events (Active Button) before finalizing
- **Evaluation Pipeline**: LLM-as-a-Judge scoring accuracy/safety/accessibility

## Data flow
1) Client sends an agent turn:
   - voice text OR control event (NEXT/PREV/CONFIRM/CANCEL/REPEAT)
2) Agent routes:
   - control events may be handled without calling tools (e.g., NEXT item in already-fetched list)
   - voice requests go through planner → tools
3) For sensitive actions:
   - create draft and set state to `awaiting_confirmation`
   - finalize only after confirm event

## Security model (critical)
- The LLM never receives a DB session/engine and never executes SQL.
- DB operations happen only inside:
  - tool functions (allowlisted)
  - server-side confirmation executor (not LLM-driven)
- Strict Pydantic validation at every boundary.

## LangGraph sketch
```mermaid
flowchart TD
  A[router_node (voice vs control)] -->|voice| B[planner_node]
  A -->|control| G[control_handler_node]

  B --> C[tool_executor_node]
  C --> D[checker_node]
  D -->|insufficient| B
  D -->|sufficient| E[finalizer_node]
  E --> F[END]

  G --> E
```