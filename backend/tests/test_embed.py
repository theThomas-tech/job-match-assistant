from sqlmodel import select

from app.embed import embed_jobs, job_embedding_text, mark_near_duplicates, role_sections
from app.models import Job
from tests.fakes import FakeEmbedder

DESCRIPTION = """About Acme
Acme is on a mission to build safe AI for everyone.

About the role
You will build retrieval pipelines for our assistant.

Responsibilities
- Ship LLM features in Python
- Own evals

Benefits
Great health insurance and snacks.
"""


def make_job(session, external_id, title="ML Engineer", description=DESCRIPTION, **fields):
    job = Job(
        source="test", external_id=external_id, company=fields.pop("company", "Acme"),
        title=title, description=description, content_hash=f"hash-{external_id}", **fields,
    )
    session.add(job)
    session.commit()
    return job


def test_role_sections_keeps_the_role_and_drops_boilerplate():
    text = role_sections(DESCRIPTION)

    assert "retrieval pipelines" in text
    assert "Ship LLM features" in text
    assert "mission" not in text
    assert "health insurance" not in text


def test_role_sections_puts_requirements_first():
    description = "About the role\nBuild APIs.\n\nMinimum qualifications\n- 3 years of Python\n"

    assert role_sections(description) == "- 3 years of Python\nBuild APIs."


def test_role_sections_falls_back_to_full_text_without_headings():
    plain = "We need a Python engineer to build APIs and data pipelines for our platform."

    assert role_sections(plain) == plain


def test_embedding_text_has_title_and_company_but_not_location(session):
    job = make_job(session, "1", locations=["London, UK"])

    text = job_embedding_text(job)

    assert text.startswith("ML Engineer at Acme\n")
    assert "London" not in text


def test_embed_jobs_only_processes_new_or_changed_jobs(session):
    make_job(session, "1")
    job2 = make_job(session, "2", title="AI Engineer")
    embedder = FakeEmbedder()

    assert embed_jobs(session, embedder) == 2
    assert embed_jobs(session, embedder) == 0  # nothing changed

    job2.content_hash = "hash-2-edited"  # the posting changed on its board
    session.commit()
    assert embed_jobs(session, embedder) == 1


def test_closed_jobs_are_not_embedded(session):
    make_job(session, "1", is_active=False)

    assert embed_jobs(session, FakeEmbedder()) == 0


def test_same_job_posted_twice_is_linked_to_the_oldest(session):
    first = make_job(session, "1", locations=["Paris"])
    second = make_job(session, "2", locations=["Madrid"])
    embed_jobs(session, FakeEmbedder())

    assert mark_near_duplicates(session) == 1

    session.refresh(second)
    assert second.duplicate_of_id == first.id


def test_same_title_with_different_content_is_not_a_duplicate(session):
    make_job(session, "1", description="Build GPU inference kernels in CUDA and C++.")
    make_job(session, "2", description="Design marketing campaigns and manage social media.")
    embed_jobs(session, FakeEmbedder())

    assert mark_near_duplicates(session) == 0


def test_different_titles_are_never_duplicates(session):
    make_job(session, "1", title="ML Engineer")
    make_job(session, "2", title="ML Engineer, Codex")
    embed_jobs(session, FakeEmbedder())

    assert mark_near_duplicates(session) == 0


def test_duplicate_links_are_recomputed_each_run(session):
    make_job(session, "1")
    second = make_job(session, "2")
    embed_jobs(session, FakeEmbedder())
    mark_near_duplicates(session)

    second.is_active = False  # the copy was removed from the board
    session.commit()
    mark_near_duplicates(session)

    session.refresh(second)
    assert second.duplicate_of_id is None
    assert len(session.exec(select(Job).where(Job.duplicate_of_id != None)).all()) == 0  # noqa: E711
