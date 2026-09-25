"""Database connection. Every part of the app gets its connection from `engine`."""

from collections.abc import Iterator

from sqlalchemy import text
from sqlmodel import Session, create_engine

from app.config import settings

# pool_pre_ping: re-checks old connections before use (avoids errors after the DB restarts).
# connect_timeout: fail after 3s instead of hanging when the DB is down.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 3},
)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: gives each request its own database session."""
    with Session(engine) as session:
        yield session


def database_is_up() -> bool:
    """Return True if we can run a trivial query against Postgres."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
