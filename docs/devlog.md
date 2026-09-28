# Dev log

A short note after each milestone: what was built, what I learned, and what was hard. (Good material for interviews.)

## M0: Project setup
**Built:**
- Postgres 16 + pgvector running in Docker Compose
- FastAPI backend with a `/health` endpoint that also checks the database connection
- First automated test (pytest)

**Learned:**
- *(fill in: e.g. what Docker volumes do, why secrets go in .env, what `uv sync` does)*

**Hard / surprising:**
- *(fill in)*

## M1: Collecting jobs
**Built:**
- Ashby and Greenhouse sources behind one `JobSource` interface, driven by `companies.yaml` (10 companies)
- Ingestion that updates instead of duplicating, merges cross-posted jobs into one row, marks removed jobs closed, and keeps going if one board fails
- `jobs` table created with an Alembic migration
- API: list/search jobs, job detail, paste a job, trigger collection
- 26 tests: parsers (offline, with sample API responses), ingestion rules, API endpoints

**Numbers from the first real run:** 2,220 jobs from 10 companies in about 12 seconds; 20 cross-posted duplicates merged; a second run changed nothing.

**Found along the way:**
- Most AI startups use Ashby, not Greenhouse (probed 40 companies' boards before choosing).
- Greenhouse sends descriptions as escaped HTML, so they're unescaped and then converted to text.
- Of 1,602 Ashby jobs, 1,123 are flagged remote. That's far too many to be true, which confirms location eligibility needs its own AI screen (M4).
- Near-duplicates (same role, one posting per city, slightly different text) slip past exact matching; planned for M3.

**Learned:**
- *(fill in: e.g. what a database migration is, why the parsers are tested without the network, what "idempotent" means for the ingest run)*

## M2: Resume profile
**Built:**
- Provider-agnostic model layer (`app/llm/`): an `LLMProvider` interface with an Ollama implementation; Claude plugs in later with one `.env` change
- `generate_structured()`: gets schema-valid JSON into a Pydantic model, retries once with the validation error, refuses empty input, and logs every call to `llm_calls`
- Resume PDF → text → structured profile (`profiles` table), as a command and as API endpoints (upload, view, edit)
- Grounding check: flags skills/organizations/institutions/location that don't appear in the resume
- Versioned prompt file: `app/prompts/profile_v1.md`
- 46 tests, using a fake model so they run in about a second without Ollama

**Decision: start with a free local model.** Chose Ollama + Qwen 2.5 7B over paying for Claude up front. Measured on my laptop (CPU only, MX550 GPU too small): reading ~86 tokens/s, writing ~4 tokens/s. Writing is the bottleneck, so outputs must stay short.

**What went wrong, and the fixes:**
- Given an *empty* job description in a test, the model invented a full answer. → The model layer now refuses empty input.
- It said `min_years_experience: 0` for a posting that didn't state it. → Schemas use `null` for "not stated".
- Ollama's JSON `format` only constrains the output; the model never sees it. → The schema is also included in the instructions.
- On my resume it invented "Accra, Ghana" (not in the resume, guessed from "University of Ghana") and missed PHP, Java, GitHub and Gradle. → Location added to the grounding check; project technologies merged into skills in code.
- Same input, `temperature=0`, two runs → different headlines. Local models aren't perfectly repeatable, which matters for evals.

**Learned:**
- *(fill in: e.g. why validate AI output with a schema, why log every model call, why fix some problems in code instead of the prompt)*
