# 03. Setup & Run

## Tech stack
- Python 3.11+ recommended
- FastAPI, Uvicorn
- SQLAlchemy
- LangGraph
- langchain-openai (or equivalent LLM client)
- Pydantic v2

## Local setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="..."
uvicorn app.main:app --reload --port 8000
```
## Notes about voice/haptics/buttons

- STT and TTS are client responsibilities.
- The backend expects voice transcript text and/or control events.
- The backend returns:
  - `tts_text`
  - `haptics.pattern`
  - `audio_cue.id` (optional)
  - `next_expected_controls` (optional)