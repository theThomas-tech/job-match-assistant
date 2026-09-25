from datetime import UTC, datetime

from app.models import Job

DESCRIPTION = (
    "Zof AI is seeking a Generative AI Engineer to build product features on top of "
    "frontier model APIs, including RAG pipelines and agent orchestration."
)

PASTED_JOB = {
    "company": "Zof AI",
    "title": "Generative AI Engineer",
    "description": DESCRIPTION,
    "location": "Accra, Ghana",
    "url": "https://zof.ai/careers/accra/generative-ai-engineer",
}


def test_paste_a_job(client):
    response = client.post("/jobs/manual", json=PASTED_JOB)

    assert response.status_code == 201
    job = response.json()
    assert job["source"] == "manual"
    assert job["locations"] == ["Accra, Ghana"]
    assert job["description"] == DESCRIPTION


def test_pasting_the_same_job_twice_returns_the_existing_one(client):
    first = client.post("/jobs/manual", json=PASTED_JOB).json()
    second = client.post("/jobs/manual", json=PASTED_JOB | {"title": " Generative AI Engineer "})

    assert second.status_code == 200
    assert second.json()["id"] == first["id"]


def test_pasted_job_needs_a_real_description(client):
    response = client.post("/jobs/manual", json=PASTED_JOB | {"description": "too short"})

    assert response.status_code == 422


def test_list_and_get_jobs(client):
    created = client.post("/jobs/manual", json=PASTED_JOB).json()

    listed = client.get("/jobs", params={"q": "generative"}).json()
    detail = client.get(f"/jobs/{created['id']}").json()

    assert [job["id"] for job in listed] == [created["id"]]
    assert "description" not in listed[0]
    assert detail["description"] == DESCRIPTION


def test_list_filters_by_company(client):
    client.post("/jobs/manual", json=PASTED_JOB)

    assert client.get("/jobs", params={"company": "zof ai"}).json() != []
    assert client.get("/jobs", params={"company": "Other"}).json() == []


def test_pasted_job_is_listed_by_when_it_was_added(client, session):
    session.add(
        Job(
            source="ashby", external_id="old", company="Acme", title="Old AI Engineer",
            description="x", content_hash="old", posted_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
    )
    session.commit()
    pasted = client.post("/jobs/manual", json=PASTED_JOB).json()

    listed = client.get("/jobs").json()

    assert listed[0]["id"] == pasted["id"]


def test_unknown_job_is_404(client):
    assert client.get("/jobs/999999").status_code == 404
