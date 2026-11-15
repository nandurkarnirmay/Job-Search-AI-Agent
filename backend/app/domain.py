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
    stale: bool = False  # True = every source was down; these are the last good results (up to a day old)
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
    bands: list["BandStats"] = Field(default_factory=list, description="Listing salaries by required experience")
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
    source: Literal["bank", "llm", "followup"] = "bank"
    parent_id: str | None = None  # follow-ups point at the question they dig into


class FeedbackItem(BaseModel):
    name: str
    score: float  # 0..1
    comment: str


class SpeechMetrics(BaseModel):
    """Delivery metrics for spoken answers (transcribed in the browser)."""

    duration_seconds: float
    words_per_minute: int
    filler_per_100_words: float
    long_pauses: int


class AnswerFeedback(BaseModel):
    """score 1-5 is computed by rules (reproducible); coach_comment is optional LLM text."""

    score: int
    word_count: int
    criteria: list[FeedbackItem]
    key_points_hit: list[str] = Field(default_factory=list)
    key_points_missed: list[str] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)
    coach_comment: str | None = None
    speech: SpeechMetrics | None = None


class RepoSummary(BaseModel):
    name: str
    url: str
    language: str | None = None
    stars: int = 0
    description: str | None = None
    pushed_at: str | None = None


class GitHubReport(BaseModel):
    username: str
    profile_url: str
    name: str | None = None
    bio: str | None = None
    public_repos: int = 0
    original_repos: int = 0
    followers: int = 0
    account_years: float = 0
    active_repos_6m: int = 0
    total_stars: int = 0
    languages: dict[str, int] = Field(default_factory=dict)  # language -> number of original repos
    skills: list[str] = Field(default_factory=list)          # taxonomy skills evidenced on GitHub
    top_repos: list[RepoSummary] = Field(default_factory=list)
    missing_from_resume: list[str] = Field(default_factory=list)   # shown on GitHub, not on the resume
    unproven_on_github: list[str] = Field(default_factory=list)    # on the resume, no public project shows it
    checks: list[FeedbackItem] = Field(default_factory=list)       # profile hygiene checklist
    notes: list[str] = Field(default_factory=list)


class BandStats(BaseModel):
    band: str          # "1-3"
    label: str         # "1–3 yrs"
    stats: SalaryStats | None = None
    n: int = 0         # listings in this band that disclose a salary


class NegotiationAdvice(BaseModel):
    role: str
    city: str | None = None
    experience_years: float | None = None
    offer_lpa: float
    benchmark: SalaryStats | None = None
    benchmark_source: str | None = None
    offer_percentile: int | None = None
    verdict: Literal["below market", "around market", "above market", "no data"] = "no data"
    counter_lpa: float | None = None
    hike_pct: float | None = None
    talking_points: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    script: str = ""
    notes: list[str] = Field(default_factory=list)


SalaryReport.model_rebuild()


class Resource(BaseModel):
    title: str
    url: str


class RoadmapStep(BaseModel):
    skill: str
    demand_share: float | None = None  # share of current postings asking for it
    weeks: int
    status: Literal["todo", "learning", "done"] = "todo"
    resources: list[Resource] = Field(default_factory=list)
    project: str | None = None


class CareerPath(BaseModel):
    role: str
    family: str | None = None
    ladder: list[dict] = Field(default_factory=list)       # [{"title", "years"}]
    adjacent_roles: list[str] = Field(default_factory=list)
    have: list[str] = Field(default_factory=list)          # required skills already on the resume
    phases: list[list[RoadmapStep]] = Field(default_factory=list)  # ~4-8 week phases
    jobs_sampled: int = 0
    notes: list[str] = Field(default_factory=list)


class InterviewReport(BaseModel):
    answered: int
    total: int
    average_score: float | None = None
    by_category: dict[str, float] = Field(default_factory=dict)
    strongest: list[dict] = Field(default_factory=list)   # [{"question", "score"}]
    weakest: list[dict] = Field(default_factory=list)
    average_wpm: int | None = None
    recurring_tips: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
