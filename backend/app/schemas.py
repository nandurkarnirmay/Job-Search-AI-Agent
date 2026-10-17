"""API request/response bodies."""
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.domain import JobListing, SearchParams


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


class ProfileOut(ProfileIn):
    pass


class SearchOut(BaseModel):
    params: SearchParams
    jobs: list[JobListing]
    count: int
    sources_ok: list[str]
    sources_failed: list[str]
    cache_hit: bool
    latency_ms: int


class ChatIn(BaseModel):
    message: str = Field(min_length=2, max_length=500)


class ChatOut(BaseModel):
    reply: str
    params: SearchParams | None
    jobs: list[JobListing]
    parser: Literal["llm", "rules"]


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str | None = None
