"""Collect jobs from every company in companies.yaml and save them to the database.

Run from the backend/ folder:
    uv run python -m app.ingest

Safe to run repeatedly: known jobs are updated rather than duplicated, and jobs that
have disappeared from their board are marked closed (is_active = False).
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass

import httpx
from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.models import Job, utcnow
from app.normalize import content_hash, unique_nonempty
from app.sources import JobSource, RawJob, load_sources

logger = logging.getLogger(__name__)


@dataclass
class SourceResult:
    """What happened when collecting one company's board."""

    company: str
    source: str
    fetched: int = 0
    new: int = 0
    updated: int = 0
    duplicates: int = 0  # same posting listed more than once (e.g. one per city)
    closed: int = 0
    error: str | None = None


def ingest(session: Session, sources: Sequence[JobSource]) -> list[SourceResult]:
    results = []
    for src in sources:
        result = SourceResult(company=src.company, source=src.source)
        try:
            raw_jobs = src.fetch()
        except Exception as exc:
            # One broken board shouldn't stop the others. Its jobs stay as they were.
            result.error = f"{type(exc).__name__}: {exc}"
            logger.warning("Failed to fetch %s (%s): %s", src.company, src.source, result.error)
            results.append(result)
            continue

        result.fetched = len(raw_jobs)
        save_jobs(session, src.source, src.company, raw_jobs, result)
        session.commit()
        results.append(result)
    return results


def save_jobs(
    session: Session, source: str, company: str, raw_jobs: list[RawJob], result: SourceResult
) -> None:
    now = utcnow()
    existing = session.exec(
        select(Job).where(Job.source == source, Job.company == company)
    ).all()
    by_external_id = {job.external_id: job for job in existing}
    by_hash = {job.content_hash: job for job in existing}

    # Group postings with identical content, so a job listed once per city becomes one row.
    groups: dict[str, list[RawJob]] = {}
    for raw in raw_jobs:
        groups.setdefault(content_hash(raw.company, raw.title, raw.description), []).append(raw)

    seen: set[int] = set()  # Python ids of the rows found on the board this run
    for hash_, group in groups.items():
        # Prefer the listing we already have stored, so its row keeps the same id.
        primary = next((r for r in group if r.external_id in by_external_id), group[0])
        fields = primary.model_dump() | {
            "locations": unique_nonempty(loc for r in group for loc in r.locations),
            "content_hash": hash_,
        }
        result.duplicates += len(group) - 1

        job = by_external_id.get(primary.external_id) or by_hash.get(hash_)
        if job is None:
            job = Job(**fields, first_seen_at=now)
            session.add(job)
            result.new += 1
        elif _update(job, fields):
            result.updated += 1

        job.last_seen_at = now
        job.is_active = True
        seen.add(id(job))

    for job in existing:
        if job.is_active and id(job) not in seen:
            job.is_active = False
            result.closed += 1


def _update(job: Job, fields: dict) -> bool:
    """Copy changed fields onto the stored job. Returns True if anything changed."""
    changed = False
    for key, value in fields.items():
        if getattr(job, key) != value:
            setattr(job, key, value)
            changed = True
    return changed


def run_ingest() -> list[SourceResult]:
    """Collect from every company in companies.yaml, using the real database."""
    with (
        httpx.Client(
            timeout=30,
            headers={"User-Agent": "job-match-assistant (personal job search tool)"},
            transport=httpx.HTTPTransport(retries=2),
        ) as client,
        Session(engine) as session,
    ):
        return ingest(session, load_sources(settings.companies_file, client))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # hide one log line per request
    header = f"{'company':<12} {'source':<11} {'fetched':>7} {'new':>5} {'updated':>7} {'dupes':>5} {'closed':>6}"
    print(header)
    print("-" * len(header))
    for r in run_ingest():
        if r.error:
            print(f"{r.company:<12} {r.source:<11} ERROR: {r.error}")
        else:
            print(
                f"{r.company:<12} {r.source:<11} {r.fetched:>7} {r.new:>5} {r.updated:>7} "
                f"{r.duplicates:>5} {r.closed:>6}"
            )
