import pytest

from app.embed import embed_jobs, mark_near_duplicates
from app.embeddings import get_embedder
from app.main import app
from app.models import Job, Profile
from tests.fakes import PROFILE, FakeEmbedder


@pytest.fixture
def embedder(client):
    fake = FakeEmbedder()
    app.dependency_overrides[get_embedder] = lambda: fake
    return fake


def add_job(session, external_id, title, description, locations=("London",), **fields):
    session.add(
        Job(
            source="test", external_id=external_id, company="Acme", title=title,
            description=description, locations=list(locations), content_hash=f"h{external_id}",
            **fields,
        )
    )
    session.commit()


def add_profile(session):
    session.add(
        Profile(source_filename="cv.pdf", resume_text="...", data=PROFILE, model="m", prompt_version="v")
    )
    session.commit()


@pytest.fixture
def jobs(session, embedder):
    add_job(session, "1", "Backend Engineer", "Python FastAPI PostgreSQL Docker backend APIs")
    add_job(session, "2", "Sales Manager", "Enterprise sales quotas pipeline negotiation")
    add_job(session, "3", "Backend Engineer", "Python FastAPI PostgreSQL Docker backend APIs", locations=["Toronto"])
    add_job(session, "4", "Backend Engineer II", "Python FastAPI PostgreSQL backend", is_active=False)
    embed_jobs(session, embedder)
    mark_near_duplicates(session)


def test_search_by_profile_ranks_relevant_jobs_first(client, session, jobs):
    add_profile(session)

    results = client.get("/search/jobs").json()

    assert [r["title"] for r in results] == ["Backend Engineer", "Sales Manager"]
    assert results[0]["similarity"] > results[1]["similarity"]


def test_search_merges_near_duplicates_and_skips_closed_jobs(client, session, jobs):
    add_profile(session)

    results = client.get("/search/jobs").json()

    backend = results[0]
    assert backend["locations"] == ["London"]
    assert backend["also_posted_in"] == ["Toronto"]
    assert "Backend Engineer II" not in [r["title"] for r in results]


def test_search_by_free_text(client, jobs):
    results = client.get("/search/jobs", params={"q": "enterprise sales"}).json()

    assert results[0]["title"] == "Sales Manager"


def test_search_without_profile_or_query_is_404(client, embedder):
    assert client.get("/search/jobs").status_code == 404


def test_editing_the_profile_changes_the_results(client, session, jobs):
    add_profile(session)
    assert client.get("/search/jobs").json()[0]["title"] == "Backend Engineer"

    sales_profile = PROFILE | {
        "headline": "Enterprise sales manager",
        "skills": ["enterprise sales", "negotiation", "pipeline", "quotas"],
        "experience": [], "projects": [], "education": [],
    }
    client.put("/profile", json=sales_profile)

    assert client.get("/search/jobs").json()[0]["title"] == "Sales Manager"
