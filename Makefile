.PHONY: run test eval docker-build docker-run

run:
	uvicorn app.main:app --reload --port 8000

test:
	pytest tests/ -v

eval:
	PYTHONIOENCODING=utf-8 python -m app.eval.llm_judge

docker-build:
	docker build -t banking-agent .

docker-run:
	docker run -p 8000:8000 -e OPENAI_API_KEY=$(OPENAI_API_KEY) banking-agent
