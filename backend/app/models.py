from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    # cascades so DELETE /auth/me removes everything the user owns, on any database
    threads: Mapped[list["ChatThread"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    alerts: Mapped[list["JobAlert"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    resume: Mapped["Resume"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    interviews: Mapped[list["InterviewSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(120))
    current_city: Mapped[str | None] = mapped_column(String(80))
    preferred_cities: Mapped[list] = mapped_column(JSON, default=list)
    experience_years: Mapped[float | None] = mapped_column(Float)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    expected_lpa: Mapped[float | None] = mapped_column(Float)
    notice_period_days: Mapped[int | None] = mapped_column(Integer)
    work_mode: Mapped[str | None] = mapped_column(String(10))  # remote | hybrid | onsite | any
    # Week 3: career goals
    career_goal: Mapped[str | None] = mapped_column(Text)
    target_roles: Mapped[list | None] = mapped_column(JSON)
    open_to_relocation: Mapped[bool | None] = mapped_column(Boolean)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped[User] = relationship(back_populates="profile")


class SearchLog(Base):
    """One row per search: feeds the search-performance and engagement monitoring."""

    __tablename__ = "search_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    channel: Mapped[str] = mapped_column(String(10))  # "search" | "chat"
    query: Mapped[str] = mapped_column(Text)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    sources_ok: Mapped[list] = mapped_column(JSON, default=list)
    sources_failed: Mapped[list] = mapped_column(JSON, default=list)
    cache_hit: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class ChatThread(Base):
    """A conversation. Keeps the last search and results so follow-up questions have context."""

    __tablename__ = "chat_threads"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # uuid4 hex
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(80))
    last_params: Mapped[dict | None] = mapped_column(JSON)
    last_jobs: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, index=True)

    user: Mapped[User] = relationship(back_populates="threads")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="thread", cascade="all, delete-orphan",
                                                         order_by="ChatMessage.id")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    thread_id: Mapped[str] = mapped_column(ForeignKey("chat_threads.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(20))
    payload: Mapped[dict | None] = mapped_column(JSON)  # jobs / company / salary shown with the message
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    thread: Mapped[ChatThread] = relationship(back_populates="messages")


class JobAlert(Base):
    """Saved search that is re-run on a schedule. Week 3: storage, API and new-job detection.
    Week 4: Celery beat runs due alerts and emails the new jobs."""

    __tablename__ = "job_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    params: Mapped[dict] = mapped_column(JSON)
    frequency: Mapped[str] = mapped_column(String(10))  # daily | weekly
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    seen_keys: Mapped[list] = mapped_column(JSON, default=list)  # dedupe keys of jobs already sent
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="alerts")
    runs: Mapped[list["AlertRun"]] = relationship(back_populates="alert", cascade="all, delete-orphan",
                                                  order_by="AlertRun.id.desc()")


class AlertRun(Base):
    """One scheduled run of an alert: what was found and whether it was emailed (in-app digest otherwise)."""

    __tablename__ = "alert_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("job_alerts.id", ondelete="CASCADE"), index=True)
    ran_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    new_jobs: Mapped[int] = mapped_column(Integer, default=0)
    emailed: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(String(300))
    digest: Mapped[list] = mapped_column(JSON, default=list)

    alert: Mapped[JobAlert] = relationship(back_populates="runs")


class Resume(Base):
    """One active resume per user. The uploaded file is NOT stored: only redacted text + parsed fields."""

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    filename: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(10))
    pages: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)  # emails/phone numbers redacted
    word_count: Mapped[int] = mapped_column(Integer)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    sections: Mapped[dict] = mapped_column(JSON, default=dict)
    has_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="resume")


class Application(Base):
    """Application tracker entry: saved -> applied -> interview -> offer | rejected | withdrawn."""

    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "job_key", name="uq_applications_user_job"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_key: Mapped[str] = mapped_column(String(16))  # dedupe key: same job from two sources is one entry
    job_id: Mapped[str | None] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(200))
    company: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(200), default="")
    url: Mapped[str | None] = mapped_column(String(1000))
    salary_min_lpa: Mapped[float | None] = mapped_column(Float)
    salary_max_lpa: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(12), default="saved", index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    next_action_on: Mapped[date | None] = mapped_column(Date)  # e.g. follow-up or interview date
    history: Mapped[list] = mapped_column(JSON, default=list)  # [{"status", "at"}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped[User] = relationship(back_populates="applications")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(120))
    company: Mapped[str | None] = mapped_column(String(200))
    questions: Mapped[list] = mapped_column(JSON)  # [InterviewQuestion]
    answers: Mapped[dict] = mapped_column(JSON, default=dict)  # {question_id: {"answer", "feedback"}}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="interviews")
