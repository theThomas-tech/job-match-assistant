"""Shapes of the data the API accepts and returns (separate from the database tables)."""

from datetime import datetime

from pydantic import BaseModel, Field
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


class JobMatch(JobSummary):
    """A job returned by vector search, with how similar it is to the profile or query."""

    similarity: float = Field(description="Cosine similarity, higher = closer (roughly 0 to 1)")
    also_posted_in: list[str] = Field(
        default_factory=list, description="Locations of near-duplicate postings of the same job"
    )


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


# --- Resume profile: what the AI model extracts from a resume (and what the user can edit) ---


class WorkExperience(BaseModel):
    title: str
    organization: str
    start: str | None = Field(description="e.g. 2023-06 or 2023; null if not stated")
    end: str | None = Field(description='"present" if current; null if not stated')
    highlights: list[str] = Field(description="At most 3 short achievements from the resume")


class Project(BaseModel):
    name: str
    summary: str = Field(description="One short sentence")
    technologies: list[str]


class Education(BaseModel):
    qualification: str
    institution: str
    end_year: str | None


class ResumeProfile(BaseModel):
    headline: str
    location: str | None
    total_years_experience: float | None = Field(description="null if unclear")
    skills: list[str]
    experience: list[WorkExperience]
    projects: list[Project]
    education: list[Education]
    certifications: list[str]


class ProfileRead(SQLModel):
    id: int
    source_filename: str
    model: str
    prompt_version: str
    edited_by_user: bool
    created_at: datetime
    updated_at: datetime
    data: ResumeProfile
    warnings: list[str] = Field(
        default_factory=list,
        description="Items in the profile that couldn't be found in the resume text (possible AI mistakes)",
    )
