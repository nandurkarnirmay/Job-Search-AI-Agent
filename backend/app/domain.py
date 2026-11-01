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


class SalaryStats(BaseModel):
    """Salary distribution in LPA. `n` is the sample size; never show stats without it."""

    n: int
    p25: float
    median: float
    p75: float
    min: float
    max: float


class SalaryReport(BaseModel):
    role: str
    city: str | None = None
    experience_years: float | None = None
    listings: SalaryStats | None = Field(default=None, description="From salaries disclosed in current listings")
    market: SalaryStats | None = Field(default=None, description="Adzuna salary histogram (includes estimates)")
    notes: list[str] = Field(default_factory=list)


class CompanyWiki(BaseModel):
    title: str
    description: str | None = None
    extract: str = ""
    url: str | None = None


class CompanyRole(BaseModel):
    title: str
    location: str
    url: str


class CompanyReport(BaseModel):
    name: str
    wiki: CompanyWiki | None = None
    open_roles: int | None = Field(default=None, description="None = job sources unavailable")
    sample_roles: list[CompanyRole] = Field(default_factory=list)
    top_cities: list[str] = Field(default_factory=list)
    disclosed_salary: SalaryStats | None = None
    sources: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ParsedResume(BaseModel):
    text: str  # contact details redacted
    kind: Literal["pdf", "docx"]
    pages: int = 0
    word_count: int
    skills: list[str]
    sections: dict[str, bool]
    has_contact: bool
    warnings: list[str] = Field(default_factory=list)


class ATSMatch(BaseModel):
    """Transparent 0–100 score: skills 70 (required ×2, preferred ×1) + job title 15 + structure 15."""

    score: int
    skills_score: float
    title_score: float
    structure_score: float
    job_title: str
    company: str | None = None
    matched_required: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    matched_preferred: list[str] = Field(default_factory=list)
    missing_preferred: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SkillDemand(BaseModel):
    skill: str
    share: float  # fraction of sampled jobs mentioning the skill
    have: bool


class ResumeReview(BaseModel):
    role: str | None
    skills: list[str]
    warnings: list[str]
    sections: dict[str, bool]
    jobs_sampled: int = 0
    demand: list[SkillDemand] = Field(default_factory=list)  # most-demanded skills for the role
    notes: list[str] = Field(default_factory=list)


class InterviewQuestion(BaseModel):
    id: str
    text: str
    category: Literal["hr", "behavioural", "technical"]
    skill: str | None = None
    key_points: list[list[str]] = Field(default_factory=list)  # [[label, regex], ...] for technical questions
    source: Literal["bank", "llm"] = "bank"


class FeedbackItem(BaseModel):
    name: str
    score: float  # 0..1
    comment: str


class AnswerFeedback(BaseModel):
    """score 1-5 is computed by rules (reproducible); coach_comment is optional LLM text."""

    score: int
    word_count: int
    criteria: list[FeedbackItem]
    key_points_hit: list[str] = Field(default_factory=list)
    key_points_missed: list[str] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)
    coach_comment: str | None = None
