"""Vector search: find the jobs closest in meaning to the profile or to a free-text query."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, select

from app.db import get_session
from app.embed import embed_profile
from app.embeddings import Embedder, get_embedder
from app.models import Job, Profile
from app.normalize import unique_nonempty
from app.schemas import JobMatch, JobSummary

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/jobs", response_model=list[JobMatch])
def search_jobs(
    q: str | None = Query(
        default=None,
        description='Search by meaning, e.g. "remote LLM engineer". Leave empty to match against your profile.',
    ),
    limit: int = Query(default=40, ge=1, le=200),
    session: Session = Depends(get_session),
    embedder: Embedder = Depends(get_embedder),
):
    if q and q.strip():
        vector = embedder.embed_query(q.strip())
    else:
        profile = session.exec(select(Profile).order_by(col(Profile.id).desc())).first()
        if profile is None:
            raise HTTPException(status_code=404, detail="No profile yet. Upload a resume, or pass q.")
        if profile.embedding is None:
            profile = embed_profile(session, embedder, profile)
        vector = profile.embedding

    # "<=>" in pgvector is cosine distance: 0 = same direction, so similarity = 1 - distance.
    distance = col(Job.embedding).cosine_distance(vector)
    rows = session.exec(
        select(Job, distance)
        .where(
            Job.is_active,
            col(Job.embedding).is_not(None),
            col(Job.duplicate_of_id).is_(None),
        )
        .order_by(distance)
        .limit(limit)
    ).all()

    # Collect the locations of near-duplicate postings, so each job shows everywhere it's offered.
    ids = [job.id for job, _ in rows]
    also_posted: dict[int, list[str]] = {}
    for primary_id, locations in session.exec(
        select(Job.duplicate_of_id, Job.locations).where(
            col(Job.duplicate_of_id).in_(ids), Job.is_active
        )
    ):
        also_posted.setdefault(primary_id, []).extend(locations)

    return [
        JobMatch(
            **JobSummary.model_validate(job).model_dump(),
            similarity=round(1 - float(dist), 4),
            also_posted_in=[
                loc for loc in unique_nonempty(also_posted.get(job.id, [])) if loc not in job.locations
            ],
        )
        for job, dist in rows
    ]
