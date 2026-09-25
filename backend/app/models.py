"""Database tables. After changing a table here, create a migration:

    uv run alembic revision --autogenerate -m "describe the change"
    uv run alembic upgrade head
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class Job(SQLModel, table=True):
    """One job posting, from a job board or pasted in by hand."""

    __tablename__ = "jobs"
    # The same posting from the same board is stored once; re-collecting updates it.
    __table_args__ = (UniqueConstraint("source", "external_id"),)

    id: int | None = Field(default=None, primary_key=True)
    source: str = Field(index=True)  # "ashby", "greenhouse" or "manual"
    external_id: str  # the posting's id on its board (content hash for manual jobs)
    company: str = Field(index=True)
    title: str
    description: str = Field(sa_column=Column(Text, nullable=False))
    locations: list[str] = Field(
        default_factory=list, sa_column=Column(JSONB, nullable=False, server_default="[]")
    )
    is_remote: bool | None = None  # None = the posting doesn't say
    workplace_type: str | None = None  # e.g. "Remote", "Hybrid", "OnSite"
    department: str | None = None
    employment_type: str | None = None  # e.g. "FullTime"
    salary: str | None = None
    url: str | None = None
    content_hash: str = Field(index=True, max_length=64)
    posted_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    first_seen_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))
    last_seen_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))
    is_active: bool = Field(default=True, index=True)  # False once removed from its board
