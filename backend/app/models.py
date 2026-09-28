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


class Profile(SQLModel, table=True):
    """A resume turned into structured data. The newest row is the current profile."""

    __tablename__ = "profiles"

    id: int | None = Field(default=None, primary_key=True)
    source_filename: str
    resume_text: str = Field(sa_column=Column(Text, nullable=False))
    data: dict = Field(sa_column=Column(JSONB, nullable=False))  # a ResumeProfile (app/schemas.py)
    model: str  # which AI model extracted it
    prompt_version: str
    edited_by_user: bool = False
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))


class LLMCall(SQLModel, table=True):
    """One call to an AI model: what it was for, how long it took, tokens used and cost."""

    __tablename__ = "llm_calls"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=utcnow, sa_type=DateTime(timezone=True), index=True
    )
    provider: str  # "ollama", later "anthropic"
    model: str
    purpose: str = Field(index=True)  # e.g. "resume_profile", later "job_screen", "job_score"
    prompt_version: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    success: bool = False
    error: str | None = Field(default=None, sa_column=Column(Text))
