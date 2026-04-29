# assistantchatbot (NLQ Multi-Agent)

Natural Language to SQL service built with FastAPI + LangGraph.

It runs a multi-agent pipeline:
`Guardrail -> Schema Linking -> SQL Generation -> Reflection`

## Current result

- **Mini-Dev E My SQL:** **58.5**

## Project structure

- `main.py`: FastAPI entrypoint and app lifespan (DB connect/disconnect)
- `src/routers/`: API routes (`/workflow`, `/test/guardrail`, `/database/*`)
- `src/core/workflows/`: NLQ workflow orchestration
- `src/core/agents/`: Agent implementations (guardrail, schema-linking, SQL-gen, reflection)
- `src/core/prompts/`: Prompt templates (`*.md`)
- `src/databases/`: Database adapters and factory

## Setup

```bash
pip install -r requirements.txt
```

Create `.env` from `.env.example` and configure DB + API keys.

## Run locally

```bash
uvicorn main:app --reload
```

API docs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## Quick smoke test

```bash
curl -X POST "http://127.0.0.1:8000/workflow" -H "Content-Type: application/json" -d "{\"nl_input\":\"Show 5 customers\"}"
```

## Evaluation commands

Run one Mini-Dev item:

```bash
python batch_evaluate.py --start 0 --limit 1
```

Run a larger Mini-Dev batch:

```bash
python batch_evaluate.py --start 0 --limit 10
```

Run EX / EX+VES evaluation scripts:

```bash
python run_eval.py
python run_eval.py --ves
```

> Note: `batch_evaluate.py` and `run_eval.py` currently use machine-specific default dataset paths.
