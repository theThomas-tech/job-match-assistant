# Job Match Assistant

An AI-powered job-matching and application assistant. It collects job postings, ranks them against a resume with a 3-stage retrieval + LLM pipeline, explains the fit (matched skills with evidence, gaps), and drafts tailored resume bullets that are checked against the resume so nothing is made up. Quality, cost and latency are measured with an eval harness.

> 🚧 Work in progress. Done: **M0 setup, M1 job collection, M2 resume profile**. Next: M3 vector search.

## Stack
- **Backend:** Python, FastAPI, SQLModel, Alembic, Postgres 16 + pgvector
- **LLMs:** swappable providers behind one interface. Currently **Qwen 2.5 7B running locally via Ollama** (free, private); Claude to be added and compared in evals.
- **Frontend:** Next.js + TypeScript (coming in M5)

## Resume profile
Upload a resume PDF and the model extracts a structured profile (skills, experience, projects, education) as schema-validated JSON:
- **Validated output:** answers are parsed into Pydantic models; an invalid answer is retried once with the validation error.
- **Grounding check:** every skill, organization, institution and location in the profile is checked against the resume text, and anything not found is returned as a warning (catches invented content without another model call).
- **Code over prompts where possible:** technologies used in projects are merged into the skills list in code, because the small model reliably missed them.
- **Every model call is logged** (`llm_calls` table): purpose, prompt version, tokens, latency, cost, success/error.
- **Privacy:** contact details are excluded from the profile, and resumes are git-ignored.

First results on a real resume (Qwen 2.5 7B on a laptop CPU): ~2–2.5 minutes per resume, 1,279 input / 432 output tokens. Before the fixes above, the model invented a location and missed 4 of 21 skills.

## Job sources
Jobs are collected from public job-board APIs for the companies in [`backend/companies.yaml`](backend/companies.yaml):
- **Ashby** (OpenAI, Cohere, ElevenLabs, ...) and **Greenhouse** (Anthropic, ...)
- **Paste in** any other posting (LinkedIn, company sites, Ghanaian job boards) with `POST /jobs/manual`

Re-running collection is safe: known jobs are updated rather than duplicated, a job cross-posted for several cities is stored once with all its locations, and jobs removed from their board are marked closed. One board failing doesn't stop the others.

## Run locally
Requires Docker Desktop, [uv](https://docs.astral.sh/uv/), Node 20+ and [Ollama](https://ollama.com) with the model pulled: `ollama pull qwen2.5:7b`.

```bash
cp .env.example .env              # then fill in values
docker compose up -d              # start Postgres + pgvector
cd backend
uv sync                           # install Python dependencies
uv run alembic upgrade head       # create/update the database tables
uv run python -m app.ingest       # collect jobs (about 15 seconds)
uv run python -m app.resume ../resumes/your-resume.pdf   # build your profile (a few minutes)
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
| `POST /profile` | Upload a resume PDF and extract a profile (minutes with a local model) |
| `GET /profile` | The current profile, with grounding warnings |
| `PUT /profile` | Correct the profile by hand |

Run the tests (the database container must be running; tests use a separate `jobmatch_test` database and a fake AI model, so Ollama isn't needed): `cd backend && uv run pytest`

## Known limitations
- Some companies post the same role separately per city with slightly different text (e.g. OpenAI's "Applied AI Engineer, Codex" for Paris, Munich and Madrid). Exact-content matching can't merge these; near-duplicate detection is planned with vector similarity in M3.
- `temperature=0` doesn't make the local model fully repeatable: two runs on the same resume gave different headlines (and only one invented a location). Evals will need several runs per case.
- The `is_remote` flag comes straight from each board and is often wrong: many "remote" roles are limited to one country. The location-eligibility screen in M4 will decide what's really open to a candidate in Ghana.
