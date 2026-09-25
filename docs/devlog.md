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
