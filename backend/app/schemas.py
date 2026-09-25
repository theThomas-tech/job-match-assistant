"""Shapes of the data the API accepts and returns (separate from the database tables)."""

from datetime import datetime

from pydantic import Field
from sqlmodel import SQLModel


class JobSummary(SQLModel):
    """A job in a list: everything except the long description."""

    id: int
    source: str
    company: str
    title: str
    locations: list[str]
    is_remote: bool | None
    workplace_type: str | None
    salary: str | None
    url: str | None
    posted_at: datetime | None
    is_active: bool


class JobRead(JobSummary):
    """A single job with all its details."""

    description: str
    department: str | None
    employment_type: str | None
    first_seen_at: datetime
    last_seen_at: datetime


class ManualJobIn(SQLModel):
    """A job pasted in by hand, e.g. from LinkedIn or a company website."""

    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=50, description="The full job description text")
    location: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=2000)
