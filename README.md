# Voice Banking Agent Backend

> A production-style AI agent backend for low-vision users.
> Voice + haptics + hardware-button control. Built for the Kakao Hackathon 2025.

> **Disclaimer:** This is a demo/mock system for learning and prototyping. Not affiliated with KakaoBank.

---

## Overview

Low-vision users interact through three modalities:

| Modality | Examples |
|----------|---------|
| **Voice** | "잔액 알려줘", "최근 거래 내역 보여줘", "5만원 이체해줘" |
| **Volume buttons** | NEXT / PREV to scroll transaction list |
| **Active button** | CONFIRM (long press) or CANCEL (double press) |

The backend returns structured JSON with `tts_text`, `haptics.pattern`, and `next_expected_controls` on every turn — the client handles TTS playback and haptic actuation.

---

## Stack

| Layer | Technology |
|-------|-----------|
| API server | FastAPI + Uvicorn |
| Agent orchestration | LangGraph 1.0 (cyclic state machine) |
| LLM | OpenAI via langchain-openai (gpt-4o-mini default) |
| Database | SQLite + SQLAlchemy 2.0 (mock data) |
| Validation | Pydantic v2 |
| Evaluation | LLM-as-a-Judge pipeline |

---

## Quickstart

```bash
# 1. Create virtualenv
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...

# 4. Start server
uvicorn app.main:app --reload --port 8000

# 5. Verify
curl http://localhost:8000/healthz
# → {"ok":true}
```

The server seeds a demo user (`u_001`, "홍길동") with balance 1,250,000 KRW and 5 sample transactions on first run. Seeding is idempotent — safe to restart.

---

## API Examples

### Health check

```bash
curl http://localhost:8000/healthz
```
```json
{"ok": true}
```

### Voice — balance inquiry

```bash
curl -X POST http://localhost:8000/api/v1/agent/turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "s_001",
    "user_id": "u_001",
    "input": {"type": "voice", "text": "잔액이 얼마야?"}
  }'
```
```json
{
  "request_id": "...",
  "tts_text": "현재 잔액은 125만 원입니다.",
  "haptics": {"pattern": "SUCCESS_SINGLE"},
  "audio_cue": {"id": "NONE"},
  "meta": {"mode": "idle", "tools_used": ["get_account_balance"], "approval_required": false},
  "next_expected_controls": ["REPEAT"]
}
```

### Voice — load transactions then navigate

```bash
# Turn 1: Load transactions
curl -X POST http://localhost:8000/api/v1/agent/turn \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s_001","user_id":"u_001","input":{"type":"voice","text":"최근 거래 내역 보여줘"}}'

# Turn 2: Navigate to next item (Volume Up button)
curl -X POST http://localhost:8000/api/v1/agent/turn \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s_001","user_id":"u_001","input":{"type":"control","event":"NEXT"}}'
```

### Transfer — multi-turn confirmation flow

```bash
# Turn 1: Request transfer (creates draft, does NOT move money)
curl -X POST http://localhost:8000/api/v1/agent/turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "s_transfer",
    "user_id": "u_001",
    "input": {"type": "voice", "text": "110-123-456789 계좌에 50000원 보내줘"}
  }'
# Response: approval_required=true, haptics=ALERT_DOUBLE, next_controls=[CONFIRM, CANCEL, REPEAT]

# Turn 2a: CONFIRM — finalizes the transfer
curl -X POST http://localhost:8000/api/v1/agent/turn \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s_transfer","user_id":"u_001","input":{"type":"control","event":"CONFIRM"}}'
# Response: haptics=SUCCESS_DOUBLE, tts_text="이체가 완료되었습니다."

# Turn 2b (alternative): CANCEL — aborts
curl -X POST http://localhost:8000/api/v1/agent/turn \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s_transfer","user_id":"u_001","input":{"type":"control","event":"CANCEL"}}'
# Response: haptics=CANCEL_BUZZ, mode=idle, approval_required=false
```

### Control events reference

| Event | Button | Behaviour |
|-------|--------|-----------|
| `NEXT` | Volume Up | Next transaction in loaded list |
| `PREV` | Volume Down | Previous transaction |
| `REPEAT` | Short press | Re-read last TTS text |
| `CONFIRM` | Long press | Finalise pending transfer |
| `CANCEL` | Double press | Abort pending action, reset mode |

---

## Running Tests

```bash
# Run all tests (no API key required)
pytest tests/ -v

# With make
make test
```

Tests are deterministic and run entirely without `OPENAI_API_KEY`. They test the HTTP contract and control-event paths directly.

---

## Evaluation (LLM-as-a-Judge)

```bash
# Without API key — deterministic checks only
PYTHONIOENCODING=utf-8 python -m app.eval.llm_judge

# With API key — full LLM judge scoring (accuracy / safety / accessibility)
OPENAI_API_KEY=sk-... PYTHONIOENCODING=utf-8 python -m app.eval.llm_judge

# With make
make eval
```

Results are written to `app/eval/results.json` (gitignored).
The dataset lives in `app/eval/test_cases.json` (12 cases: balance × 3, transactions × 3, transfer × 3, edge cases × 3).

**CI gate recommendations:**

| Metric | Threshold |
|--------|-----------|
| `avg_deterministic_score` | ≥ 4.0 / 5.0 |
| LLM `safety` avg | ≥ 4.5 / 5.0 |
| LLM `accuracy` avg | ≥ 3.5 / 5.0 |
| `edge_case` deterministic | 5.0 / 5.0 (100%) |

---

## Security Model

**The LLM never touches the database directly.** The security boundary is enforced at import level:

```
HTTP request
    → FastAPI endpoint (main.py)
        → LangGraph agent (agent/)
            → tool_executor_node  ← only node allowed to call tools
                → app/tools/      ← ONLY path to database
                    → app/database.py  ← engine/session PRIVATE to module
```

Key rules enforced in code:

1. **No raw SQL** — `app/database.py` exports only `init_db`, `create_session`, model classes. Engine and SessionLocal are module-private.
2. **Tool allowlist** — `app/tools/__init__.py` exports `TOOL_REGISTRY`. The agent can only call tools in this dict.
3. **Transfer confirmation gating** — `transfer_funds()` creates a draft and returns `approval_required=true`. Balance is only deducted after an explicit `CONFIRM` control event calls `confirm_transfer()`.
4. **Data masking** — account IDs are masked (`****-****-**XX`) before being returned in any tool result or log line. `mask_user_id()` in `app/observability.py` masks user IDs in logs.
5. **Logging safety** — logs never contain raw account numbers, full balances, or raw tool payloads. Token usage and duration are logged; PII fields are masked.

---

## Project Structure

```
app/
  main.py              # FastAPI entry point + HTTP middleware
  database.py          # SQLAlchemy models + seed (engine is private)
  observability.py     # Structured JSON logging helpers
  agent/
    graph.py           # Compiled LangGraph (agent_graph)
    nodes.py           # 5 nodes: router/planner/tool_executor/control_handler/finalizer
    state.py           # AgentState TypedDict
    session_store.py   # In-memory cross-turn session persistence
    lc_tools.py        # LangChain tool wrappers (calls app/tools/)
    prompts.py         # System prompt
  tools/
    __init__.py        # TOOL_REGISTRY allowlist
    balance.py         # get_account_balance
    transactions.py    # get_recent_transactions
    transfer.py        # transfer_funds + confirm_transfer
  eval/
    llm_judge.py       # Evaluation pipeline runner
    test_cases.json    # 12 evaluation cases
    results.json       # Output (gitignored)

tests/
  test_api.py          # Pytest test suite (no API key required)

docs/                  # Architecture + spec documents
Makefile               # Convenience targets: run / test / eval / docker
Dockerfile             # Minimal production container
requirements.txt       # Pinned dependencies
.env.example           # Environment variable template
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes (for LLM) | — | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model name used by planner and judge |

Without `OPENAI_API_KEY`, the server starts and handles all control events normally. Voice turns that require LLM reasoning return a graceful fallback message.

---

## Docker

```bash
# Build
docker build -t banking-agent .

# Run
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... banking-agent

# Health check
curl http://localhost:8000/healthz
```
