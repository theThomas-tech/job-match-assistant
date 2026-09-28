"""Embed jobs and the profile, and detect near-duplicate postings.

Run from the backend/ folder after collecting jobs:
    uv run python -m app.embed

Only jobs that are new or changed since their last embedding are processed, so after the
first run (a few minutes) it takes seconds.
"""

import re
import sys
import time
from collections.abc import Callable

from sqlalchemy import or_, text, update
from sqlmodel import Session, col, select

from app.embeddings import Embedder
from app.models import Job, Profile
from app.schemas import ResumeProfile

MAX_EMBED_CHARS = 2000  # about the 512-token limit of the embedding model

# Two postings from the same company with the same title and at least this similarity are
# treated as the same job (e.g. one posting per city). Chosen from the real data: see docs/devlog.md.
NEAR_DUPLICATE_SIMILARITY = 0.97

# Section headings about what the candidate needs (skills, experience). Most useful for
# matching, so they go first: the embedding model only reads the first ~2000 characters.
_REQUIREMENTS = (
    "qualif", "requirement", "good fit", "a fit", "thrive", "who you are", "nice to have",
    "strong candidates", "would be great", "you have", "looking for", "skills", "you need",
)
# Section headings about the work itself. Come second.
_ROLE = ("role", "responsib", "you will", "you'll", "what you", "the team")
# ...and headings for company boilerplate, pay and logistics, which say nothing about fit.
_BOILERPLATE = (
    "about us", "who are we", "who we are", "benefit", "offer", "salary", "compensation",
    "logistics", "different", "work with us", "how we work", "where we work", "location",
    "overview", "rhythm", "equal", "perks", "why join", "mission", "life at",
)


def _is_heading(line: str) -> bool:
    return (
        3 <= len(line) <= 60
        and not line.startswith(("-", "•", "*"))
        and not line.rstrip().endswith((".", ",", ";"))
    )


def _section_kind(heading: str) -> str | None:
    """"requirements", "role", or None for sections to skip."""
    h = heading.lower().replace("’", "'")
    if any(word in h for word in _BOILERPLATE):
        return None
    if h.startswith("about") and not any(w in h for w in ("role", "team", "you")):
        return None  # "About OpenAI", "About Anthropic", ...
    if any(word in h for word in _REQUIREMENTS):
        return "requirements"
    if any(word in h for word in _ROLE):
        return "role"
    return None


def role_sections(description: str) -> str:
    """Keep only the sections of a job description about the requirements and the role.

    Requirements come first, then the role, so the most useful text survives truncation.
    Falls back to the whole description if no known headings are found.
    """
    kept: dict[str, list[str]] = {"requirements": [], "role": []}
    current: str | None = None
    for line in description.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _is_heading(stripped):
            current = _section_kind(stripped)
            continue
        if current:
            kept[current].append(stripped)
    lines = kept["requirements"] + kept["role"]
    return "\n".join(lines) if lines else description


def job_embedding_text(job: Job) -> str:
    # Location is deliberately left out: it says nothing about skills fit (the M4 screen checks
    # eligibility), and it would stop the same job posted in two cities from looking identical.
    return f"{job.title} at {job.company}\n\n{role_sections(job.description)}"[:MAX_EMBED_CHARS]


def profile_embedding_text(profile: ResumeProfile) -> str:
    parts = [profile.headline, "Skills: " + ", ".join(profile.skills)]
    for job in profile.experience:
        parts.append(f"{job.title} at {job.organization}: " + " ".join(job.highlights))
    for project in profile.projects:
        parts.append(f"Project {project.name}: {project.summary} ({', '.join(project.technologies)})")
    for education in profile.education:
        parts.append(f"{education.qualification}, {education.institution}")
    return "\n".join(parts)[:MAX_EMBED_CHARS]


def embed_jobs(
    session: Session,
    embedder: Embedder,
    batch_size: int = 64,
    on_progress: Callable[[int, int], None] | None = None,
) -> int:
    """Embed active jobs that have no embedding yet, or whose content changed since. Returns how many."""
    stale = session.exec(
        select(Job).where(
            Job.is_active,
            or_(
                col(Job.embedding).is_(None),
                col(Job.embedded_hash).is_distinct_from(col(Job.content_hash)),
            ),
        )
    ).all()
    for start in range(0, len(stale), batch_size):
        batch = stale[start : start + batch_size]
        vectors = embedder.embed([job_embedding_text(job) for job in batch])
        for job, vector in zip(batch, vectors, strict=True):
            job.embedding = vector
            job.embedded_hash = job.content_hash
        session.commit()
        if on_progress:
            on_progress(min(start + batch_size, len(stale)), len(stale))
    return len(stale)


def embed_profile(session: Session, embedder: Embedder, profile: Profile) -> Profile:
    profile.embedding = embedder.embed([profile_embedding_text(ResumeProfile.model_validate(profile.data))])[0]
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def mark_near_duplicates(session: Session, threshold: float = NEAR_DUPLICATE_SIMILARITY) -> int:
    """Link postings that are really the same job (same company and title, near-identical text).

    Each group keeps its oldest posting as the primary; the others get duplicate_of_id set.
    Returns the number of postings marked as duplicates.
    """
    pairs = session.connection().execute(
        text(
            """
            SELECT a.id, b.id
            FROM jobs a
            JOIN jobs b ON a.company = b.company AND lower(a.title) = lower(b.title) AND a.id < b.id
            WHERE a.is_active AND b.is_active
              AND a.embedding IS NOT NULL AND b.embedding IS NOT NULL
              AND 1 - (a.embedding <=> b.embedding) >= :threshold
            """
        ),
        {"threshold": threshold},
    ).all()

    # Group connected pairs (if A~B and B~C, all three are one job) with union-find.
    parent: dict[int, int] = {}

    def root(job_id: int) -> int:
        parent.setdefault(job_id, job_id)
        while parent[job_id] != job_id:
            parent[job_id] = parent[parent[job_id]]
            job_id = parent[job_id]
        return job_id

    for a, b in pairs:
        ra, rb = root(a), root(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)  # the oldest (smallest id) stays primary

    session.exec(update(Job).values(duplicate_of_id=None))
    duplicates = {job_id: root(job_id) for job_id in parent if root(job_id) != job_id}
    for job_id, primary_id in duplicates.items():
        session.exec(update(Job).where(col(Job.id) == job_id).values(duplicate_of_id=primary_id))
    session.commit()
    return len(duplicates)


if __name__ == "__main__":
    from app.db import engine
    from app.embeddings import get_embedder

    started = time.perf_counter()
    embedder = get_embedder()

    def progress(done: int, total: int) -> None:
        print(f"\r  embedded {done}/{total} jobs", end="", file=sys.stderr, flush=True)

    with Session(engine) as session:
        count = embed_jobs(session, embedder, on_progress=progress)
        print(f"\nJobs embedded: {count}")
        profile = session.exec(select(Profile).order_by(col(Profile.id).desc())).first()
        if profile is not None and profile.embedding is None:
            embed_profile(session, embedder, profile)
            print(f"Profile #{profile.id} embedded")
        print(f"Near-duplicate postings linked: {mark_near_duplicates(session)}")
    print(f"Done in {time.perf_counter() - started:.0f}s")
