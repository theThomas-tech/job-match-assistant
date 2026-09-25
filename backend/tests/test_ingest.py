"""Ingestion tests with fake job boards and the test database."""

from sqlmodel import select

from app.ingest import ingest
from app.models import Job
from app.sources import RawJob


class FakeSource:
    source = "fake"

    def __init__(self, jobs=(), error=None, company="Acme"):
        self.company = company
        self.jobs = list(jobs)
        self.error = error

    def fetch(self):
        if self.error:
            raise self.error
        return self.jobs


def raw(external_id, title="ML Engineer", description="Build models.", locations=("London",)):
    return RawJob(
        source="fake",
        external_id=external_id,
        company="Acme",
        title=title,
        description=description,
        locations=list(locations),
    )


def all_jobs(session):
    return session.exec(select(Job).order_by(Job.id)).all()


def test_new_jobs_are_saved(session):
    [result] = ingest(session, [FakeSource([raw("1"), raw("2", title="AI Engineer")])])

    assert result.new == 2
    assert [job.title for job in all_jobs(session)] == ["ML Engineer", "AI Engineer"]


def test_running_twice_does_not_duplicate(session):
    ingest(session, [FakeSource([raw("1")])])
    [result] = ingest(session, [FakeSource([raw("1")])])

    assert (result.new, result.updated) == (0, 0)
    assert len(all_jobs(session)) == 1


def test_changed_job_is_updated_in_place(session):
    ingest(session, [FakeSource([raw("1")])])
    [result] = ingest(session, [FakeSource([raw("1", title="Senior ML Engineer")])])

    [job] = all_jobs(session)
    assert result.updated == 1
    assert job.title == "Senior ML Engineer"


def test_cross_posted_job_becomes_one_row_with_all_locations(session):
    source = FakeSource([raw("1", locations=["London"]), raw("2", locations=["Toronto"])])

    [result] = ingest(session, [source])

    [job] = all_jobs(session)
    assert result.duplicates == 1
    assert job.locations == ["London", "Toronto"]


def test_job_removed_from_board_is_closed(session):
    ingest(session, [FakeSource([raw("1"), raw("2", title="AI Engineer")])])
    [result] = ingest(session, [FakeSource([raw("1")])])

    assert result.closed == 1
    assert [job.is_active for job in all_jobs(session)] == [True, False]


def test_failed_fetch_keeps_existing_jobs_open(session):
    ingest(session, [FakeSource([raw("1")])])
    [result] = ingest(session, [FakeSource(error=ConnectionError("board down"))])

    assert "board down" in result.error
    assert all_jobs(session)[0].is_active is True


def test_one_failing_board_does_not_stop_the_others(session):
    results = ingest(
        session,
        [FakeSource(error=ConnectionError("down"), company="Broken"), FakeSource([raw("1")])],
    )

    assert results[0].error is not None
    assert results[1].new == 1
