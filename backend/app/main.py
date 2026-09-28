"""FastAPI entry point.

Run locally (from the backend/ folder):
    uv run uvicorn app.main:app --reload
Then open http://localhost:8000/health or the interactive docs at http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.db import database_is_up
from app.routers import jobs, profile, search

app = FastAPI(title="Job Match Assistant API", version="0.1.0")
app.include_router(jobs.router)
app.include_router(profile.router)
app.include_router(search.router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Opening the bare address shows the interactive API docs."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check: the API is running, and reports whether Postgres is reachable."""
    return {
        "status": "ok",
        "database": "ok" if database_is_up() else "unreachable",
    }
