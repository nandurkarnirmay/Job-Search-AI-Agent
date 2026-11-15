"""Day-before email reminders for calendar events (interviews, follow-ups, deadlines)."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import get_cache
from app.config import get_settings
from app.models import CalendarEvent
from app.services.email import EmailError, email_enabled, send_email

log = logging.getLogger("app.reminders")
IST = timezone(timedelta(hours=5, minutes=30), "IST")  # India has no DST, so a fixed offset is exact


def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def due_reminders(db: Session, now: datetime | None = None) -> list[CalendarEvent]:
    now = now or datetime.now(timezone.utc)
    rows = db.scalars(select(CalendarEvent).where(CalendarEvent.remind.is_(True),
                                                  CalendarEvent.reminder_sent_at.is_(None))).all()
    return [e for e in rows if now <= _aware(e.starts_at) <= now + timedelta(hours=24)]


def dispatch_reminders(db: Session, now: datetime | None = None) -> dict:
    summary = {"reminders": 0, "reminder_errors": 0}
    if not email_enabled():
        return summary  # nothing to send with; the calendar feed's own alarms still fire
    cache = get_cache()
    if cache.incr("lock:reminders", 900) > 1:  # Celery beat and the cron endpoint must not double-send
        return {**summary, "reminders_skipped": "another dispatch is running"}
    try:
        _send_due(db, now, summary)
    finally:
        cache.delete("lock:reminders")
    return summary


def _send_due(db: Session, now: datetime | None, summary: dict) -> None:
    app_url = get_settings().public_app_url.rstrip("/")
    for e in due_reminders(db, now):
        when = _aware(e.starts_at).astimezone(IST).strftime("%a %d %b, %I:%M %p IST")
        body = [f"Reminder: {e.title}", f"When: {when}"]
        if e.location:
            body.append(f"Where: {e.location}")
        if e.kind == "interview":
            body.append(f"Practise questions for this role: {app_url}/interview")
        body.append(f"Your tracker: {app_url}/applications")
        try:
            send_email(e.user.email, f"Tomorrow: {e.title}", "\n".join(body))
            e.reminder_sent_at = datetime.now(timezone.utc)
            db.commit()
            summary["reminders"] += 1
        except EmailError as err:
            log.warning("reminder %s failed: %s", e.id, err)
            summary["reminder_errors"] += 1  # not marked sent: retried next run
