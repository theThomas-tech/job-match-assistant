"""Endpoints for browsing jobs, adding one by hand, and triggering a collection run."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session, col, func, select

from app.db import get_session
from app.ingest import run_ingest
from app.models import Job
from app.normalize import clean_text, content_hash
from app.schemas import JobRead, JobSummary, ManualJobIn

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobSummary])
def list_jobs(
    company: str | None = None,
    q: str | None = Query(default=None, description="Text to search for in job titles"),
    include_closed: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    query = select(Job)
    if not include_closed:
        query = query.where(Job.is_active)
    if company:
        query = query.where(col(Job.company).ilike(company))
    if q:
        query = query.where(col(Job.title).ilike(f"%{q}%"))
    # Newest first. Pasted jobs have no posting date, so use when we first saw them instead.
    newest = func.coalesce(col(Job.posted_at), col(Job.first_seen_at))
    query = query.order_by(newest.desc(), col(Job.id).desc())
    return session.exec(query.offset(offset).limit(limit)).all()


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/manual", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def add_manual_job(body: ManualJobIn, response: Response, session: Session = Depends(get_session)):
    """Add a job by pasting it in. Pasting the same job twice returns the existing one."""
    company, title = body.company.strip(), body.title.strip()
    description = clean_text(body.description)
    hash_ = content_hash(company, title, description)

    existing = session.exec(select(Job).where(Job.content_hash == hash_)).first()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return existing

    job = Job(
        source="manual",
        external_id=hash_,
        company=company,
        title=title,
        description=description,
        locations=[body.location.strip()] if body.location and body.location.strip() else [],
        url=body.url,
        content_hash=hash_,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.post("/ingest")
def trigger_ingest() -> list[dict]:
    """Collect from every company in companies.yaml now. Takes up to a minute."""
    return [asdict(result) for result in run_ingest()]
