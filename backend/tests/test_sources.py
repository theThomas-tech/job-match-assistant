"""Parser tests using small, hand-written copies of real API responses (no network needed)."""

from pathlib import Path

from app.config import settings
from app.sources import load_companies
from app.sources.ashby import parse_ashby
from app.sources.greenhouse import parse_greenhouse

ASHBY_PAYLOAD = {
    "jobs": [
        {
            "id": "abc-123",
            "title": "Senior ML Engineer ",
            "location": "Toronto",
            "secondaryLocations": [{"location": "London"}, {"location": "Toronto"}],
            "isListed": True,
            "isRemote": True,
            "workplaceType": "Remote",
            "department": "Engineering",
            "employmentType": "FullTime",
            "jobUrl": "https://jobs.ashbyhq.com/cohere/abc-123",
            "publishedAt": "2026-09-15T18:21:37.401+00:00",
            "descriptionPlain": "Who are we?\n\n\n\nWe build   models.",
            "shouldDisplayCompensationOnJobPostings": True,
            "compensation": {"scrapeableCompensationSalarySummary": "CA$215K - CA$310K"},
        },
        {"id": "hidden", "title": "Unlisted role", "isListed": False, "descriptionPlain": "x"},
        {
            "id": "html-only",
            "title": "Designer",
            "location": "Paris",
            "descriptionHtml": "<p>Design <b>things</b></p>",
            "shouldDisplayCompensationOnJobPostings": False,
            "compensation": {"scrapeableCompensationSalarySummary": "€100K"},
        },
    ]
}

GREENHOUSE_PAYLOAD = {
    "jobs": [
        {
            "id": 4461450008,
            "title": "Research Engineer",
            "location": {"name": "New York City, NY; San Francisco, CA | New York City, NY"},
            "departments": [{"name": "Research"}],
            "absolute_url": "https://job-boards.greenhouse.io/anthropic/jobs/4461450008",
            "first_published": "2024-12-20T13:53:38-05:00",
            "content": "&lt;h2&gt;About&lt;/h2&gt;&lt;p&gt;Make AI safe &amp;amp; useful.&lt;/p&gt;",
        },
        {
            "id": 42,
            "title": "Solutions Engineer",
            "location": {"name": "Remote-Friendly (Travel-Required)"},
            "content": "",
        },
    ]
}


def test_parse_ashby_normalizes_a_job():
    jobs = parse_ashby("Cohere", ASHBY_PAYLOAD)
    job = jobs[0]

    assert job.external_id == "abc-123"
    assert job.company == "Cohere"
    assert job.title == "Senior ML Engineer"
    assert job.locations == ["Toronto", "London"]
    assert job.is_remote is True
    assert job.salary == "CA$215K - CA$310K"
    assert job.description == "Who are we?\n\nWe build models."
    assert job.posted_at.year == 2026


def test_parse_ashby_skips_unlisted_jobs():
    ids = [job.external_id for job in parse_ashby("Cohere", ASHBY_PAYLOAD)]

    assert "hidden" not in ids


def test_parse_ashby_falls_back_to_html_and_hides_private_salary():
    job = parse_ashby("Cohere", ASHBY_PAYLOAD)[1]

    assert job.description == "Design things"
    assert job.salary is None


def test_parse_greenhouse_unescapes_html_and_splits_locations():
    job = parse_greenhouse("Anthropic", GREENHOUSE_PAYLOAD)[0]

    assert job.external_id == "4461450008"
    assert job.description == "About\n\nMake AI safe & useful."
    assert job.locations == ["New York City, NY", "San Francisco, CA"]
    assert job.is_remote is None
    assert job.department == "Research"


def test_parse_greenhouse_detects_remote_from_location():
    job = parse_greenhouse("Anthropic", GREENHOUSE_PAYLOAD)[1]

    assert job.is_remote is True


def test_companies_yaml_is_valid():
    companies = load_companies(Path(settings.companies_file))

    assert len(companies) >= 1
    assert len({c.slug for c in companies}) == len(companies), "duplicate slug in companies.yaml"
