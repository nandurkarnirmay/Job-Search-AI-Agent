"""Core data shapes shared by sources, services and the agent (pydantic only, no framework imports)."""
from typing import Literal

from pydantic import BaseModel, Field

WorkMode = Literal["remote", "hybrid", "onsite"]


class JobListing(BaseModel):
    id: str
    title: str
    company: str
    location: str
    url: str
    source: str
    description: str = ""
    salary_min_lpa: float | None = None
    salary_max_lpa: float | None = None
    experience_min_years: float | None = None
    experience_max_years: float | None = None
    work_mode: WorkMode | None = None
    notice_period_days: int | None = None
    posted_at: str | None = None


class SearchParams(BaseModel):
    """Structured search request. The chat agent produces this from free text."""

    keywords: str = Field(default="", description="Role or skills, e.g. 'python developer'")
    city: str | None = Field(default=None, description="Single Indian city, e.g. 'Bengaluru'")
    max_experience_years: float | None = Field(default=None, ge=0, le=50,
                                               description="Candidate's experience; 0 for freshers")
    min_salary_lpa: float | None = Field(default=None, ge=0, le=500, description="Minimum salary in LPA")
    work_mode: WorkMode | None = None
    notice_period_days: int | None = Field(default=None, ge=0, le=180,
                                           description="Candidate's notice period; hides 'immediate joiner' jobs")
    page: int = Field(default=1, ge=1, le=10)

    def cache_key(self) -> str:
        return "search:" + self.model_dump_json(exclude_none=True)


class SearchOutcome(BaseModel):
    params: SearchParams
    jobs: list[JobListing]
    total_before_filters: int
    sources_ok: list[str]
    sources_failed: list[str]
    cache_hit: bool = False
    latency_ms: int = 0
