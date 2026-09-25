"""Greenhouse public job board API (used by Anthropic, Databricks, Scale AI, ...).

Docs: https://developers.greenhouse.io/job-board.html
"""

import html
import re

import httpx

from app.normalize import html_to_text, unique_nonempty
from app.sources.base import RawJob

API_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


class GreenhouseSource:
    source = "greenhouse"

    def __init__(self, company: str, slug: str, client: httpx.Client) -> None:
        self.company = company
        self.slug = slug
        self.client = client

    def fetch(self) -> list[RawJob]:
        # content=true includes each job's full description in the same response.
        response = self.client.get(API_URL.format(slug=self.slug), params={"content": "true"})
        response.raise_for_status()
        return parse_greenhouse(self.company, response.json())


def parse_greenhouse(company: str, payload: dict) -> list[RawJob]:
    """Turn Greenhouse's JSON response into RawJobs. Kept separate from fetch() so it can be tested offline."""
    jobs = []
    for item in payload.get("jobs", []):
        # Several locations arrive in one string, e.g. "New York City, NY; San Francisco, CA | New York City, NY"
        location_text = (item.get("location") or {}).get("name") or ""
        departments = item.get("departments") or []

        jobs.append(
            RawJob(
                source="greenhouse",
                external_id=str(item["id"]),
                company=company,
                title=item["title"].strip(),
                # The description arrives as escaped HTML ("&lt;p&gt;"): unescape it, then strip the tags.
                description=html_to_text(html.unescape(item.get("content") or "")),
                locations=unique_nonempty(re.split(r"[;|]", location_text)),
                # Greenhouse has no remote flag; only mark remote when the location says so.
                is_remote=True if "remote" in location_text.lower() else None,
                department=departments[0].get("name") if departments else None,
                url=item.get("absolute_url"),
                posted_at=item.get("first_published") or item.get("updated_at"),
            )
        )
    return jobs
