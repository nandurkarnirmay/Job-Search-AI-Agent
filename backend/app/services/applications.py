"""Application tracker helpers shared by the API and the chat agent."""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import AppError, ConflictError
from app.models import Application
from app.services.search_service import get_job
from app.sources.normalize import dedupe_key

STATUSES = ["saved", "applied", "interview", "offer", "rejected", "withdrawn"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def find_existing(db: Session, user_id: int, key: str) -> Application | None:
    return db.scalar(select(Application).where(Application.user_id == user_id, Application.job_key == key))


def add_application(db: Session, user_id: int, *, job_id: str | None = None, title: str | None = None,
                    company: str | None = None, location: str = "", url: str | None = None,
                    status: str = "saved", notes: str | None = None) -> Application:
    """From a recently seen job (job_id: details come from our cache, not the client) or entered manually."""
    salary_min = salary_max = None
    if job_id:
        job = get_job(job_id)
        if job is None and not (title and company):
            raise AppError("That job is no longer in recent results. Search again, then save it.",
                           code="job_expired", status_code=404)
        if job is not None:
            title, company, location, url = job.title, job.company, job.location, job.url
            salary_min, salary_max = job.salary_min_lpa, job.salary_max_lpa
    if not (title and company):
        raise AppError("Give a job_id from a search, or a title and company.", code="validation_error",
                       status_code=422)
    if url and not url.startswith(("https://", "http://")):
        url = None
    key = dedupe_key(title, company, location)
    if existing := find_existing(db, user_id, key):
        raise ConflictError(f"Already in your tracker as '{existing.status}'.", code="already_tracked")
    app = Application(user_id=user_id, job_key=key, job_id=job_id, title=title[:200], company=company[:200],
                      location=(location or "")[:200], url=url, salary_min_lpa=salary_min, salary_max_lpa=salary_max,
                      status=status, notes=notes, history=[{"status": status, "at": _now_iso()}])
    db.add(app)
    db.commit()
    return app


def set_status(app: Application, status: str) -> None:
    if status != app.status:
        app.status = status
        app.history = list(app.history or []) + [{"status": status, "at": _now_iso()}]


def pipeline(db: Session, user_id: int) -> dict[str, int]:
    rows = db.execute(select(Application.status, func.count()).where(Application.user_id == user_id)
                      .group_by(Application.status)).all()
    counts = dict(rows)
    return {s: counts.get(s, 0) for s in STATUSES}
