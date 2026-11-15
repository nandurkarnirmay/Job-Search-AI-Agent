"""API request/response bodies."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.domain import (
    AnswerFeedback,
    ATSMatch,
    CareerPath,
    GitHubReport,
    NegotiationAdvice,
    CompanyReport,
    InterviewQuestion,
    JobListing,
    ResumeReview,
    SalaryReport,
    SearchParams,
)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr


class ProfileIn(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    current_city: str | None = Field(default=None, max_length=80)
    preferred_cities: list[str] = Field(default_factory=list, max_length=10)
    experience_years: float | None = Field(default=None, ge=0, le=50)
    skills: list[str] = Field(default_factory=list, max_length=50)
    expected_lpa: float | None = Field(default=None, ge=0, le=500)
    notice_period_days: int | None = Field(default=None, ge=0, le=180)
    work_mode: Literal["remote", "hybrid", "onsite", "any"] | None = None
    career_goal: str | None = Field(default=None, max_length=500)
    target_roles: list[str] = Field(default_factory=list, max_length=5)
    open_to_relocation: bool | None = None
    github_username: str | None = Field(default=None, max_length=39, pattern=r"^[A-Za-z0-9-]*$")

    @field_validator("preferred_cities", "skills", "target_roles", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        return [] if v is None else v


class ProfileOut(ProfileIn):
    pass


class SearchOut(BaseModel):
    params: SearchParams
    jobs: list[JobListing]
    count: int
    sources_ok: list[str]
    sources_failed: list[str]
    cache_hit: bool
    stale: bool = False
    latency_ms: int


class ChatIn(BaseModel):
    message: str = Field(min_length=2, max_length=500)
    thread_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")


Intent = Literal["job_search", "refine_search", "company_research", "salary_research", "resume_review",
                 "resume_match", "interview_prep", "track_application", "applications_status", "salary_negotiation",
                 "career_path", "github_review", "help"]


class ChatOut(BaseModel):
    thread_id: str
    reply: str
    intent: Intent
    params: SearchParams | None
    jobs: list[JobListing]
    company: CompanyReport | None = None
    salary: SalaryReport | None = None
    extras: "ChatExtras | None" = None
    parser: Literal["llm", "rules"]


class ThreadSummary(BaseModel):
    id: str
    title: str
    updated_at: datetime


class MessageOut(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    intent: str | None
    payload: dict | None
    created_at: datetime


class ThreadOut(ThreadSummary):
    messages: list[MessageOut]


Frequency = Literal["daily", "weekly"]


class AlertIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    params: SearchParams
    frequency: Frequency = "daily"

    @field_validator("params")
    @classmethod
    def _needs_role(cls, v: SearchParams) -> SearchParams:
        if len(v.keywords.strip()) < 2:
            raise ValueError("an alert needs a role or skills to search for")
        return v.model_copy(update={"page": 1})


class AlertPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    frequency: Frequency | None = None
    active: bool | None = None


class AlertOut(BaseModel):
    id: int
    name: str
    params: SearchParams
    frequency: Frequency
    active: bool
    last_run_at: datetime | None
    created_at: datetime


class AlertPreview(BaseModel):
    total: int
    new: int
    jobs: list[JobListing]


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str | None = None


# ---------- Week 4 ----------

AppStatus = Literal["saved", "applied", "interview", "offer", "rejected", "withdrawn"]


class ResumeOut(BaseModel):
    filename: str
    kind: str
    pages: int
    word_count: int
    skills: list[str]
    sections: dict[str, bool]
    has_contact: bool
    warnings: list[str]
    uploaded_at: datetime


class MatchIn(BaseModel):
    """Match against a job from a recent search (job_id) or a pasted description."""

    job_id: str | None = Field(default=None, max_length=120)
    job_title: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=20000)


class ApplicationIn(BaseModel):
    job_id: str | None = Field(default=None, max_length=120)  # from a recent search: details filled server-side
    title: str | None = Field(default=None, min_length=2, max_length=200)
    company: str | None = Field(default=None, min_length=1, max_length=200)
    location: str = Field(default="", max_length=200)
    url: str | None = Field(default=None, max_length=1000, pattern=r"^https?://")
    status: AppStatus = "saved"
    notes: str | None = Field(default=None, max_length=2000)


class ApplicationPatch(BaseModel):
    status: AppStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)
    next_action_on: date | None = None


class ApplicationOut(BaseModel):
    id: int
    job_id: str | None
    title: str
    company: str
    location: str
    url: str | None
    salary_min_lpa: float | None
    salary_max_lpa: float | None
    status: AppStatus
    notes: str | None
    next_action_on: date | None
    history: list[dict]
    created_at: datetime
    updated_at: datetime


class InterviewIn(BaseModel):
    role: str | None = Field(default=None, min_length=2, max_length=120)
    company: str | None = Field(default=None, max_length=200)
    job_id: str | None = Field(default=None, max_length=120)


class InterviewOut(BaseModel):
    id: int
    role: str
    company: str | None
    questions: list[InterviewQuestion]
    answers: dict[str, dict]
    notes: list[str] = Field(default_factory=list)
    created_at: datetime


class AnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=5000)
    # spoken answers (transcribed in the browser): speaking time and pauses longer than 2 s
    duration_seconds: float | None = Field(default=None, gt=0, le=900)
    long_pauses: int = Field(default=0, ge=0, le=200)


class AnswerOut(BaseModel):
    question_id: str
    feedback: AnswerFeedback
    followup: InterviewQuestion | None = None


class AlertRunOut(BaseModel):
    id: int
    ran_at: datetime
    new_jobs: int
    emailed: bool
    error: str | None
    digest: list[dict]


class ChatExtras(BaseModel):
    """Week 4 cards shown under a chat reply."""

    ats: ATSMatch | None = None
    resume_review: ResumeReview | None = None
    interview: InterviewOut | None = None
    application: ApplicationOut | None = None
    pipeline: dict[str, int] | None = None
    negotiation: "NegotiationAdvice | None" = None
    career: "CareerPath | None" = None
    github: "GitHubReport | None" = None


ChatExtras.model_rebuild()
ChatOut.model_rebuild()


# ---------- Week 5-6 ----------
EventKind = Literal["interview", "follow_up", "deadline", "other"]


class EventIn(BaseModel):
    kind: EventKind = "interview"
    title: str = Field(min_length=2, max_length=200)
    starts_at: datetime  # send with timezone, e.g. 2026-11-20T15:00:00+05:30
    duration_minutes: int = Field(default=60, ge=5, le=600)
    location: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)
    remind: bool = True
    application_id: int | None = None

    @field_validator("starts_at")
    @classmethod
    def _aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("include a timezone offset, e.g. +05:30")
        return v


class EventPatch(BaseModel):
    kind: EventKind | None = None
    title: str | None = Field(default=None, min_length=2, max_length=200)
    starts_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=600)
    location: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)
    remind: bool | None = None


class EventOut(BaseModel):
    id: int
    kind: EventKind
    title: str
    starts_at: datetime
    duration_minutes: int
    location: str | None
    notes: str | None
    remind: bool
    application_id: int | None
    google_calendar_url: str


class FeedOut(BaseModel):
    feed_url: str
    webcal_url: str


class NegotiationIn(BaseModel):
    role: str = Field(min_length=2, max_length=100)
    offer_lpa: float = Field(gt=0, le=500)
    city: str | None = Field(default=None, max_length=60)
    experience_years: float | None = Field(default=None, ge=0, le=50)
    current_lpa: float | None = Field(default=None, gt=0, le=500)
    competing_offer_lpa: float | None = Field(default=None, gt=0, le=500)
    notice_period_days: int | None = Field(default=None, ge=0, le=180)


class SkillStatusIn(BaseModel):
    skill: str = Field(min_length=1, max_length=60)
    status: Literal["todo", "learning", "done"]


class GitHubIn(BaseModel):
    username: str = Field(min_length=1, max_length=39)
