"""Shared test setup. Database tests use a separate "jobmatch_test" database, never the real one.

Requires the Postgres container to be running: docker compose up -d
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url, text
from sqlmodel import Session, SQLModel

from app import models  # noqa: F401  (registers the tables)
from app.config import settings
from app.db import get_session
from app.main import app

TEST_DB_NAME = "jobmatch_test"


@pytest.fixture(scope="session")
def engine():
    url = make_url(settings.database_url)

    # Create the test database the first time the tests run.
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB_NAME}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin.dispose()

    test_engine = create_engine(url.set(database=TEST_DB_NAME))
    # Rebuild the tables from app/models.py so tests always match the current code.
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as db_session:
        yield db_session
    # Empty every table so each test starts clean.
    with engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def client(session):
    """An API client whose requests use the test database."""
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()
