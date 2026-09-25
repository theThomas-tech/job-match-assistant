"""Ashby public job board API (used by OpenAI, Cohere, ElevenLabs and many AI startups).

Docs: https://developers.ashbyhq.com/docs/public-job-posting-api
"""

import httpx

from app.normalize import clean_text, html_to_text, unique_nonempty
from app.sources.base import RawJob

API_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


class AshbySource:
    source = "ashby"

    def __init__(self, company: str, slug: str, client: httpx.Client) -> None:
        self.company = company
        self.slug = slug
        self.client = client

    def fetch(self) -> list[RawJob]:
        response = self.client.get(
            API_URL.format(slug=self.slug), params={"includeCompensation": "true"}
        )
        response.raise_for_status()
        return parse_ashby(self.company, response.json())


def parse_ashby(company: str, payload: dict) -> list[RawJob]:
    """Turn Ashby's JSON response into RawJobs. Kept separate from fetch() so it can be tested offline."""
    jobs = []
    for item in payload.get("jobs", []):
        if not item.get("isListed", True):
            continue

        secondary = [loc.get("location") for loc in item.get("secondaryLocations") or []]
        description = item.get("descriptionPlain") or html_to_text(item.get("descriptionHtml") or "")

        # Only keep salary information the company chose to show publicly.
        comp = item.get("compensation") or {}
        salary = None
        if item.get("shouldDisplayCompensationOnJobPostings"):
            salary = comp.get("scrapeableCompensationSalarySummary") or comp.get(
                "compensationTierSummary"
            )

        jobs.append(
            RawJob(
                source="ashby",
                external_id=item["id"],
                company=company,
                title=item["title"].strip(),
                description=clean_text(description),
                locations=unique_nonempty([item.get("location"), *secondary]),
                is_remote=item.get("isRemote"),
                workplace_type=item.get("workplaceType"),
                department=item.get("department"),
                employment_type=item.get("employmentType"),
                salary=salary,
                url=item.get("jobUrl"),
                posted_at=item.get("publishedAt"),
            )
        )
    return jobs
