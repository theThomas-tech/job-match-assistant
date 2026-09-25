# Job Match Assistant

An AI-powered job-matching and application assistant. It collects job postings, ranks them against a resume with a 3-stage retrieval + LLM pipeline, explains the fit (matched skills with evidence, gaps), and drafts tailored resume bullets that are checked against the resume so nothing is made up. Quality, cost and latency are measured with an eval harness.

> 🚧 Work in progress. Done: **M0 setup, M1 job collection**. Next: M2 resume profile.

## Stack
- **Backend:** Python, FastAPI, SQLModel, Alembic, Postgres 16 + pgvector
- **LLMs:** Claude Haiku 4.5 (screening), Claude Sonnet 5 (scoring and tailoring)
- **Frontend:** Next.js + TypeScript (coming in M5)

## Job sources
Jobs are collected from public job-board APIs for the companies in [`backend/companies.yaml`](backend/companies.yaml):
- **Ashby** (OpenAI, Cohere, ElevenLabs, ...) and **Greenhouse** (Anthropic, ...)
- **Paste in** any other posting (LinkedIn, company sites, Ghanaian job boards) with `POST /jobs/manual`

Re-running collection is safe: known jobs are updated rather than duplicated, a job cross-posted for several cities is stored once with all its locations, and jobs removed from their board are marked closed. One board failing doesn't stop the others.

## Run locally
Requires Docker Desktop, [uv](https://docs.astral.sh/uv/) and Node 20+.

```bash
cp .env.example .env              # then fill in values
docker compose up -d              # start Postgres + pgvector
cd backend
uv sync                           # install Python dependencies
uv run alembic upgrade head       # create/update the database tables
uv run python -m app.ingest       # collect jobs (about 15 seconds)
uv run uvicorn app.main:app --reload
```

Then open the interactive API docs at http://localhost:8000/docs

| Endpoint | What it does |
|---|---|
| `GET /health` | API and database status |
| `GET /jobs?q=&company=&include_closed=&limit=&offset=` | List jobs, newest first |
| `GET /jobs/{id}` | One job with its full description |
| `POST /jobs/manual` | Add a job by pasting it in |
| `POST /jobs/ingest` | Collect from all job boards now |

Run the tests (the database container must be running; tests use a separate `jobmatch_test` database): `cd backend && uv run pytest`

## Known limitations
- Some companies post the same role separately per city with slightly different text (e.g. OpenAI's "Applied AI Engineer, Codex" for Paris, Munich and Madrid). Exact-content matching can't merge these; near-duplicate detection is planned with vector similarity in M3.
- The `is_remote` flag comes straight from each board and is often wrong: many "remote" roles are limited to one country. The location-eligibility screen in M4 will decide what's really open to a candidate in Ghana.
