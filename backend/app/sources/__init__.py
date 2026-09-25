"""Builds the list of job sources from companies.yaml."""

from pathlib import Path
from typing import Literal

import httpx
import yaml
from pydantic import BaseModel

from app.sources.ashby import AshbySource
from app.sources.base import JobSource, RawJob
from app.sources.greenhouse import GreenhouseSource

SOURCE_TYPES = {"ashby": AshbySource, "greenhouse": GreenhouseSource}


class CompanyConfig(BaseModel):
    name: str
    ats: Literal["ashby", "greenhouse"]
    slug: str


def load_companies(path: Path) -> list[CompanyConfig]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [CompanyConfig(**entry) for entry in data.get("companies", [])]


def load_sources(path: Path, client: httpx.Client) -> list[JobSource]:
    return [
        SOURCE_TYPES[company.ats](company.name, company.slug, client)
        for company in load_companies(path)
    ]


__all__ = ["JobSource", "RawJob", "CompanyConfig", "load_companies", "load_sources"]
