# Job Match Assistant

An AI-powered job-matching and application assistant. It collects job postings, ranks them against a resume with a 3-stage retrieval + LLM pipeline, explains the fit (matched skills with evidence, gaps), and drafts tailored resume bullets that are checked against the resume so nothing is made up. Quality, cost and latency are measured with an eval harness.

> 🚧 Work in progress. Currently at **M0: project setup**.

## Stack
- **Backend:** Python, FastAPI, SQLModel, Postgres 16 + pgvector
- **LLMs:** Claude Haiku 4.5 (screening), Claude Sonnet 5 (scoring and tailoring)
- **Frontend:** Next.js + TypeScript (coming in M5)

## Run locally
Requires Docker Desktop, [uv](https://docs.astral.sh/uv/) and Node 20+.

```bash
cp .env.example .env              # then fill in values
docker compose up -d              # start Postgres + pgvector
cd backend
uv sync                           # install Python dependencies
uv run uvicorn app.main:app --reload
```

Check it's working: http://localhost:8000/health should return `{"status": "ok", "database": "ok"}`.

Run the tests: `cd backend && uv run pytest`
