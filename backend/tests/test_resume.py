import pytest

from app.resume import (
    ResumeUnreadableError,
    add_project_technologies,
    check_grounding,
    extract_pdf_text,
)
from app.schemas import ResumeProfile
from tests.fakes import PROFILE, RESUME_LINES, make_pdf

RESUME_TEXT = "\n".join(RESUME_LINES)


def profile_with(**changes):
    return ResumeProfile.model_validate(PROFILE | changes)


def test_extracts_text_from_pdf():
    text = extract_pdf_text(make_pdf(RESUME_LINES))

    assert "Hubtel" in text
    assert "University of Ghana" in text


def test_pdf_without_enough_text_is_rejected():
    with pytest.raises(ResumeUnreadableError):
        extract_pdf_text(make_pdf(["Just a name"]))


def test_file_that_is_not_a_pdf_is_rejected():
    with pytest.raises(ResumeUnreadableError):
        extract_pdf_text(b"this is not a pdf")


def test_grounding_accepts_items_found_in_the_resume():
    # "NodeJS" in the profile matches "Node.js" in the resume.
    assert check_grounding(profile_with(), RESUME_TEXT) == []


def test_grounding_flags_invented_skills():
    warnings = check_grounding(profile_with(skills=["Python", "Kubernetes"]), RESUME_TEXT)

    assert warnings == ['Skill "Kubernetes" isn\'t mentioned in the resume']


def test_grounding_short_skill_names_must_match_a_whole_word():
    text = "Worked at Google on search. Skills: Rust"

    profile = profile_with(skills=["Go", "Rust"], location=None, experience=[], education=[])

    warnings = check_grounding(profile, text)

    assert warnings == ['Skill "Go" isn\'t mentioned in the resume']


def test_grounding_flags_invented_location():
    # The resume mentions "University of Ghana" but never says where the person lives.
    warnings = check_grounding(profile_with(location="Kumasi, Ghana"), RESUME_TEXT)

    assert warnings == ['Location "Kumasi, Ghana" isn\'t mentioned in the resume']


def test_project_technologies_are_added_to_skills():
    project = {"name": "App", "summary": "An app.", "technologies": ["Java", "python", "Node.js"]}
    profile = profile_with(skills=["Python", "NodeJS"], projects=[project])

    assert add_project_technologies(profile).skills == ["Python", "NodeJS", "Java"]


def test_grounding_flags_invented_organizations():
    job = PROFILE["experience"][0] | {"organization": "MTN Ghana"}

    warnings = check_grounding(profile_with(experience=[job]), RESUME_TEXT)

    assert warnings == ['Organization "MTN Ghana" isn\'t mentioned in the resume']
