# Job Match Assistant

An AI-powered job-matching and application assistant. It collects job postings, ranks them against a resume with a 3-stage retrieval + LLM pipeline, explains the fit (matched skills with evidence, gaps), and drafts tailored resume bullets that are checked against the resume so nothing is made up. Quality, cost and latency are measured with an eval harness.

> 🚧 Work in progress. Done: **M0 setup, M1 job collection, M2 resume profile, M3 vector search**. Next: M4 scoring pipeline.

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

## Vector search
Jobs and the profile are embedded locally with `BAAI/bge-small-en-v1.5` (fastembed/ONNX, 384 dimensions) and searched in Postgres with pgvector cosine distance.
- **Embed what matters:** the model reads only ~512 tokens, but postings average 6–8k characters and open with company boilerplate. Only role sections are embedded, **requirements first** (detected from section headings in 99.7% of 2,221 real postings); "About <company>", benefits, salary and logistics are dropped. Location is left out on purpose.
- **Incremental:** only new or changed postings are re-embedded (first run: 2,221 jobs in ~6 min on a laptop CPU; later runs: seconds).
- **Near-duplicates:** same company + same title + cosine similarity ≥ 0.97 are linked to the oldest posting and shown once with all locations (74 linked). The threshold was checked against every same-title pair: above 0.97 are copy-pasted per city; below are rewritten per region, often with different requirements, so they stay separate.
- **Exact search, no index:** at a few thousand rows a sequential scan is exact and takes ~80 ms per query; an HNSW index is only worth it at much larger scale.

**What vector search can't do (measured on a real profile):** similarity scores are tightly bunched (top 20 all between 0.749 and 0.764), and it ignores seniority and location. Relevant early-career roles ranked #173, #251 and #456 of 2,147, so a plain top-40 cut would drop them. Stage 1 in M4 therefore combines vector similarity with title rules and always keeps pasted-in jobs.

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
uv run python -m app.embed        # embed new jobs + profile, link near-duplicates
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
| `GET /search/jobs?q=&limit=` | Jobs closest to your profile, or to a text query like "remote LLM engineer" |

Run the tests (the database container must be running; tests use a separate `jobmatch_test` database and a fake AI model, so Ollama isn't needed): `cd backend && uv run pytest`

## Known limitations
- `temperature=0` doesn't make the local model fully repeatable: two runs on the same resume gave different headlines (and only one invented a location). Evals will need several runs per case.
- The `is_remote` flag comes straight from each board and is often wrong: many "remote" roles are limited to one country. The location-eligibility screen in M4 will decide what's really open to a candidate in Ghana.
