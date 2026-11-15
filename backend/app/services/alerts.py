"""Job alerts: saved searches re-run on a schedule; only jobs not sent before count as new.
Delivery (email or in-app digest) lives in app/services/alert_dispatch.py."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import JobListing, SearchParams
from app.models import JobAlert
from app.monitoring import ALERT_RUNS
from app.services.search_service import run_search
from app.sources.normalize import dedupe_key

INTERVALS = {"daily": timedelta(days=1), "weekly": timedelta(days=7)}
MAX_SEEN = 500  # cap per alert so the row doesn't grow forever


def _aware(dt: datetime | None) -> datetime | None:
    # SQLite returns naive datetimes even for timezone=True columns
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def job_key(job: JobListing) -> str:
    # same key the aggregator dedupes on, so a job re-listed by a different source isn't "new"
    return dedupe_key(job.title, job.company, job.location)


def new_jobs(alert: JobAlert, jobs: list[JobListing]) -> list[JobListing]:
    seen = set(alert.seen_keys or [])
    return [j for j in jobs if job_key(j) not in seen]


def record_seen(db: Session, alert: JobAlert, jobs: list[JobListing]) -> None:
    alert.seen_keys = ([job_key(j) for j in jobs] + list(alert.seen_keys or []))[:MAX_SEEN]
    alert.last_run_at = datetime.now(timezone.utc)
    db.commit()


def run_alert(db: Session, alert: JobAlert, *, mark_seen: bool = True) -> tuple[list[JobListing], int]:
    """Returns (new jobs, total matching). With mark_seen=False it's a preview that changes nothing."""
    outcome = run_search(SearchParams(**alert.params))
    fresh = new_jobs(alert, outcome.jobs)
    if mark_seen:
        record_seen(db, alert, fresh)
        ALERT_RUNS.labels("ok").inc()
    return fresh, len(outcome.jobs)


def due_alerts(db: Session, now: datetime | None = None) -> list[JobAlert]:
    now = now or datetime.now(timezone.utc)
    alerts = db.scalars(select(JobAlert).where(JobAlert.active.is_(True))).all()
    return [a for a in alerts if a.last_run_at is None or now - _aware(a.last_run_at) >= INTERVALS[a.frequency]]
