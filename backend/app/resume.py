"""Turn a resume PDF into a structured profile with an AI model, and check the result.

Try it from the backend/ folder (takes a few minutes with a local model):
    uv run python -m app.resume ../resumes/your-resume.pdf
"""

import io
import re
import sys
import time

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlmodel import Session

from app.llm import LLMProvider, generate_structured
from app.llm.prompts import load_prompt
from app.models import Profile
from app.normalize import clean_text
from app.schemas import ResumeProfile

PROMPT_VERSION = "profile_v1"
MIN_RESUME_CHARS = 200


class ResumeUnreadableError(ValueError):
    """The file has no usable text (e.g. it's a scanned image or not a real PDF)."""


def extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = clean_text("\n".join(page.extract_text() or "" for page in reader.pages))
    except PdfReadError as exc:
        raise ResumeUnreadableError(f"Couldn't open this PDF: {exc}") from exc
    if len(text) < MIN_RESUME_CHARS:
        raise ResumeUnreadableError(
            "Couldn't read enough text from this PDF. If it's a scanned image, "
            "export it from Word/Google Docs as a text PDF instead."
        )
    return text


def extract_profile(session: Session, provider: LLMProvider, resume_text: str) -> ResumeProfile:
    return generate_structured(
        session,
        provider,
        output_model=ResumeProfile,
        system=load_prompt(PROMPT_VERSION),
        user=f"Resume:\n\n{resume_text}",
        purpose="resume_profile",
        prompt_version=PROMPT_VERSION,
    )


def add_project_technologies(profile: ResumeProfile) -> ResumeProfile:
    """Make sure every technology used in a project is also in the skills list.

    Small models often list only the resume's "Skills" section and miss tools named in
    projects (e.g. Java, PHP). Merging them in code is more reliable than asking in the prompt.
    """
    known = {_squash(skill) for skill in profile.skills}
    skills = list(profile.skills)
    for project in profile.projects:
        for tech in project.technologies:
            if _squash(tech) not in known:
                skills.append(tech)
                known.add(_squash(tech))
    return profile.model_copy(update={"skills": skills})


def _squash(text: str) -> str:
    """Lowercase and drop punctuation/spaces, so "Node.js" matches "NodeJS". Keeps + and # (C++, C#)."""
    return re.sub(r"[^a-z0-9+#]", "", text.lower())


def _appears_in(item: str, resume_text: str) -> bool:
    needle = _squash(item)
    if not needle:
        return True
    if len(needle) <= 2:
        # Very short names ("R", "Go", "C") would match inside other words; require a whole word.
        return re.search(rf"(?<![a-z0-9]){re.escape(item.lower())}(?![a-z0-9])", resume_text.lower()) is not None
    return needle in _squash(resume_text)


def check_grounding(profile: ResumeProfile, resume_text: str) -> list[str]:
    """List skills and organizations in the profile that don't appear anywhere in the resume.

    A cheap, non-AI check for invented content. A warning isn't always an error (the model may
    have reworded something), but it's worth a look.
    """
    warnings = [
        f'Skill "{skill}" isn\'t mentioned in the resume'
        for skill in profile.skills
        if not _appears_in(skill, resume_text)
    ]
    if profile.location and not _appears_in(profile.location, resume_text):
        warnings.append(f'Location "{profile.location}" isn\'t mentioned in the resume')
    for job in profile.experience:
        if not _appears_in(job.organization, resume_text):
            warnings.append(f'Organization "{job.organization}" isn\'t mentioned in the resume')
    for education in profile.education:
        if not _appears_in(education.institution, resume_text):
            warnings.append(f'Institution "{education.institution}" isn\'t mentioned in the resume')
    return warnings


def create_profile(
    session: Session, provider: LLMProvider, filename: str, pdf_bytes: bytes
) -> Profile:
    resume_text = extract_pdf_text(pdf_bytes)
    extracted = add_project_technologies(extract_profile(session, provider, resume_text))
    profile = Profile(
        source_filename=filename,
        resume_text=resume_text,
        data=extracted.model_dump(),
        model=provider.model,
        prompt_version=PROMPT_VERSION,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


if __name__ == "__main__":
    from pathlib import Path

    from app.db import engine
    from app.llm import get_provider

    if len(sys.argv) != 2:
        sys.exit("Usage: uv run python -m app.resume path/to/resume.pdf")
    path = Path(sys.argv[1])
    provider = get_provider()
    print(f"Reading {path.name} with {provider.name}:{provider.model} (this can take a few minutes)...")

    started = time.perf_counter()
    with Session(engine) as session:
        profile = create_profile(session, provider, path.name, path.read_bytes())
        data = ResumeProfile.model_validate(profile.data)
        print(data.model_dump_json(indent=2))
        warnings = check_grounding(data, profile.resume_text)
        print(f"\nSaved as profile #{profile.id} in {time.perf_counter() - started:.0f}s")
        print("Grounding check:", "all items found in the resume" if not warnings else "")
        for warning in warnings:
            print(" -", warning)
