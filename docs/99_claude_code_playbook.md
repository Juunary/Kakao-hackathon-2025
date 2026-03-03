# 99. Claude Code Playbook (Execution Rules)

## Non-negotiable execution rule
Do NOT write all code at once.
Implement and stop at each Phase when it is:
- complete,
- runnable,
- testable,
- ready for review.

Only then proceed to the next Phase.

---

## Phase 1 — Infrastructure & Secure Database Setup
Goal: Build the FastAPI skeleton and a secure mock database.

Deliverables:
1) `requirements.txt` or `pyproject.toml` with:
   - fastapi, uvicorn, sqlalchemy, langgraph, langchain-openai, pydantic
2) `app/database.py` using SQLite + SQLAlchemy models:
   - Users, Accounts (Transactions optional later)
3) Enforce security structure:
   - Agent code must not have DB engine/session access
   - No raw SQL execution patterns anywhere in agent layer
4) `app/main.py` with:
   - FastAPI app
   - `GET /healthz`

Definition of Done:
- `uvicorn app.main:app` runs
- `/healthz` returns `{ "ok": true }`
- DB tables initialize successfully
- Code structure clearly prevents LLM from direct SQL access

Stop and report:
- what files were created
- how to run locally
- how to verify the DB and health endpoint

---

## Phase 2 — Permission-Controlled Tools
Goal: Create strict tools as the only “arms and legs” for the agent.

Deliverables:
- `app/tools/` directory
- Tool functions with Pydantic validation + try/except:
  - get_account_balance(user_id)
  - get_recent_transactions(user_id, limit)
  - transfer_funds(from_user_id, to_account, amount) → returns approval_required + action_token
- Tool allowlist/registry and safe error returns

Stop and report test commands and example payloads.

---

## Phase 3 — LangGraph Agent Workflow (Cyclic + Control Events)
Goal: Implement the agent graph and expose `/api/v1/agent/turn`.

Deliverables:
- `app/agent/graph.py` with AgentState and nodes:
  - router_node (voice vs control)
  - planner_node
  - tool_executor_node
  - checker_node (loop if insufficient)
  - control_handler_node (NEXT/PREV/REPEAT/CONFIRM/CANCEL)
  - finalizer_node (multisensory-friendly)
- Loop guardrails

Stop and report:
- example curl requests for voice and control events
- example transfer flow (draft → confirm)

---

## Phase 4 — Observability & LLM-as-a-Judge Evaluation
Goal: Add monitoring and an automated grading pipeline.

Deliverables:
- tool timing logs, basic token usage logs
- `app/eval/llm_judge.py`
- `app/eval/test_cases.json`
- scored results output with 1–5 ratings on:
  - Accuracy
  - Safety
  - Accessibility (multisensory + TTS)

Stop and report how to run eval and read results.