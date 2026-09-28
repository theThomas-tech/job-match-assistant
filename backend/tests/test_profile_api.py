import json

import httpx
import pytest
from sqlmodel import select

from app.llm import get_provider
from app.main import app
from app.models import LLMCall
from tests.fakes import PROFILE, RESUME_LINES, FakeProvider, make_pdf

RESUME_PDF = make_pdf(RESUME_LINES)


@pytest.fixture
def use_model():
    """Make the API use a FakeProvider with the given replies."""

    def install(*replies):
        provider = FakeProvider(*replies)
        app.dependency_overrides[get_provider] = lambda: provider
        return provider

    return install


def upload(client, content=RESUME_PDF, filename="resume.pdf"):
    return client.post("/profile", files={"file": (filename, content, "application/pdf")})


def test_upload_resume_creates_profile(client, session, use_model):
    use_model(json.dumps(PROFILE))

    response = upload(client)

    assert response.status_code == 201
    body = response.json()
    assert body["source_filename"] == "resume.pdf"
    assert body["data"]["experience"][0]["organization"] == "Hubtel"
    assert body["warnings"] == []
    assert body["edited_by_user"] is False
    assert len(session.exec(select(LLMCall)).all()) == 1


def test_upload_rejects_non_pdf(client, use_model):
    use_model()

    assert upload(client, b"hello", filename="resume.docx").status_code == 400


def test_upload_rejects_pdf_without_text(client, use_model):
    use_model()

    response = upload(client, make_pdf(["Only a name"]))

    assert response.status_code == 422


def test_upload_explains_when_model_is_not_running(client, use_model):
    use_model(httpx.ConnectError("refused"))

    response = upload(client)

    assert response.status_code == 503
    assert "Is it running?" in response.json()["detail"]


def test_get_profile_before_upload_is_404(client):
    assert client.get("/profile").status_code == 404


def test_edit_profile_marks_it_edited_and_rechecks_grounding(client, use_model):
    use_model(json.dumps(PROFILE))
    upload(client)

    edited = PROFILE | {"skills": ["Python", "Kubernetes"]}
    response = client.put("/profile", json=edited)

    body = response.json()
    assert body["edited_by_user"] is True
    assert body["data"]["skills"] == ["Python", "Kubernetes"]
    assert body["warnings"] == ['Skill "Kubernetes" isn\'t mentioned in the resume']
    assert client.get("/profile").json()["data"]["skills"] == ["Python", "Kubernetes"]
