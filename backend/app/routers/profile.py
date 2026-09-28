"""Endpoints for uploading a resume and viewing or correcting the extracted profile."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlmodel import Session, col, select

from app.db import get_session
from app.llm import LLMOutputError, LLMProvider, get_provider
from app.models import Profile, utcnow
from app.resume import ResumeUnreadableError, check_grounding, create_profile
from app.schemas import ProfileRead, ResumeProfile

router = APIRouter(prefix="/profile", tags=["profile"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _to_read(profile: Profile) -> ProfileRead:
    data = ResumeProfile.model_validate(profile.data)
    return ProfileRead(
        **profile.model_dump(exclude={"data", "resume_text", "embedding"}),
        data=data,
        warnings=check_grounding(data, profile.resume_text),
    )


def _latest(session: Session) -> Profile:
    profile = session.exec(select(Profile).order_by(col(Profile.id).desc())).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile yet. Upload a resume first.")
    return profile


# A plain `def` (not `async def`): FastAPI runs it in a worker thread, so the minutes spent
# waiting for the AI model don't freeze the rest of the API.
@router.post("", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
def upload_resume(
    file: UploadFile,
    session: Session = Depends(get_session),
    provider: LLMProvider = Depends(get_provider),
):
    """Upload a resume PDF. The AI extracts a profile; with a local model this takes minutes."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
    pdf_bytes = file.file.read()
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The file is larger than 5 MB.")

    try:
        profile = create_profile(session, provider, file.filename, pdf_bytes)
    except ResumeUnreadableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503, detail=f"Can't reach the AI model ({provider.name}). Is it running?"
        ) from exc
    except LLMOutputError as exc:
        raise HTTPException(status_code=502, detail=f"The AI model gave an invalid answer: {exc}") from exc
    return _to_read(profile)


@router.get("", response_model=ProfileRead)
def get_profile(session: Session = Depends(get_session)):
    """The current (most recent) profile."""
    return _to_read(_latest(session))


@router.put("", response_model=ProfileRead)
def update_profile(body: ResumeProfile, session: Session = Depends(get_session)):
    """Replace the current profile with corrected data (e.g. after fixing an AI mistake)."""
    profile = _latest(session)
    profile.data = body.model_dump()
    profile.embedding = None  # recomputed from the new data at the next search
    profile.edited_by_user = True
    profile.updated_at = utcnow()
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return _to_read(profile)
