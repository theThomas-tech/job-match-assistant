"""FastAPI entry point.

Run locally (from the backend/ folder):
    uv run uvicorn app.main:app --reload
Then open http://localhost:8000/health or the interactive docs at http://localhost:8000/docs
"""

from fastapi import FastAPI

from app.db import database_is_up

app = FastAPI(title="Job Match Assistant API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check: the API is running, and reports whether Postgres is reachable."""
    return {
        "status": "ok",
        "database": "ok" if database_is_up() else "unreachable",
    }
