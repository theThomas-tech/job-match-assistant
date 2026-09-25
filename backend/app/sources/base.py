"""The shape every job source produces, and the interface every source implements."""

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field


class RawJob(BaseModel):
    """A job posting converted into one common shape, whichever board it came from."""

    source: str
    external_id: str
    company: str
    title: str
    description: str
    locations: list[str] = Field(default_factory=list)
    is_remote: bool | None = None
    workplace_type: str | None = None
    department: str | None = None
    employment_type: str | None = None
    salary: str | None = None
    url: str | None = None
    posted_at: datetime | None = None


class JobSource(Protocol):
    """Anything with these attributes and a fetch() method can be collected from.

    Adding a new job board means writing one class like this (see ashby.py).
    """

    source: str  # "ashby", "greenhouse", ...
    company: str  # display name, e.g. "Cohere"

    def fetch(self) -> list[RawJob]: ...
