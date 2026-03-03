# Kakao-hackathon-2025

# Voice Banking Agent Backend (Low-Vision, Multisensory)

This project rebuilds a capstone prototype into a production-style **Voice-to-Action AI Agent Backend**
designed for low-vision users who operate the app using:

- **Voice** (natural language requests)
- **Haptics / Vibration** (feedback patterns)
- **Volume buttons** (list navigation, repeat, cancel shortcuts)
- **Active button** (push-to-talk + explicit confirmation for sensitive actions)

Core banking tasks supported (mocked):
- Check account balance
- Read recent transactions
- Transfer funds with **out-of-band confirmation** (Active Button)

> ⚠️ This is a demo/mock system for learning and prototyping. It is not affiliated with KakaoBank.

## Key production constraints
- Core server: **FastAPI (Python native)** (avoid heavy frameworks)
- Agent orchestration: **LangGraph** (cyclic state machine)
- **No raw SQL from the LLM**. The agent can only use allowlisted tools.
- Evaluation: **LLM-as-a-Judge** pipeline for accuracy/safety/accessibility.

## Quickstart (local)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="..."
uvicorn app.main:app --reload --port 8000