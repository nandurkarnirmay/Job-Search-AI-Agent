import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.errors import AppError
from app.models import Application, CalendarEvent, User
from app.schemas import EventIn, EventOut, EventPatch, FeedOut
from app.services.calendar_ics import calendar, google_link, vevent

router = APIRouter(prefix="/calendar", tags=["calendar"])
MAX_EVENTS = 300
ICS = "text/calendar; charset=utf-8"


def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _out(e: CalendarEvent) -> EventOut:
    start = _aware(e.starts_at)
    return EventOut(id=e.id, kind=e.kind, title=e.title, starts_at=start, duration_minutes=e.duration_minutes,
                    location=e.location, notes=e.notes, remind=e.remind, application_id=e.application_id,
                    google_calendar_url=google_link(e.title, start, e.duration_minutes, e.location, e.notes))


def _own(db: Session, user: User, eid: int) -> CalendarEvent:
    e = db.get(CalendarEvent, eid)
    if e is None or e.user_id != user.id:
        raise AppError("Event not found.", code="not_found", status_code=404)
    return e


def _event_lines(e: CalendarEvent) -> list[str]:
    app_url = get_settings().public_app_url.rstrip("/")
    prep = f"Practise: {app_url}/interview" if e.kind == "interview" else f"Tracker: {app_url}/applications"
    desc = "\n".join(x for x in [e.notes, prep] if x)
    return vevent(f"event-{e.id}@job-search-agent", e.title, _aware(e.starts_at), minutes=e.duration_minutes,
                  location=e.location, description=desc, alarms=(1440, 60) if e.remind else ())


@router.get("/events", response_model=list[EventOut])
def list_events(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=30)
    rows = db.scalars(select(CalendarEvent).where(CalendarEvent.user_id == user.id, CalendarEvent.starts_at >= since)
                      .order_by(CalendarEvent.starts_at)).all()
    return [_out(e) for e in rows]


@router.post("/events", response_model=EventOut, status_code=201)
def create_event(body: EventIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.scalar(select(func.count()).select_from(CalendarEvent).where(CalendarEvent.user_id == user.id)) >= MAX_EVENTS:
        raise AppError("Too many events; delete old ones first.", code="event_limit", status_code=409)
    if body.application_id is not None:
        a = db.get(Application, body.application_id)
        if a is None or a.user_id != user.id:
            raise AppError("Application not found.", code="not_found", status_code=404)
    e = CalendarEvent(user_id=user.id, **body.model_dump())
    e.starts_at = body.starts_at.astimezone(timezone.utc)
    db.add(e)
    db.commit()
    return _out(e)


@router.patch("/events/{eid}", response_model=EventOut)
def update_event(eid: int, body: EventPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = _own(db, user, eid)
    data = body.model_dump(exclude_unset=True)
    if "starts_at" in data and data["starts_at"] is not None:
        if data["starts_at"].tzinfo is None:
            raise AppError("starts_at: include a timezone offset, e.g. +05:30", code="validation_error",
                           status_code=422)
        data["starts_at"] = data["starts_at"].astimezone(timezone.utc)
        e.reminder_sent_at = None  # rescheduled: remind again
    for k, v in data.items():
        setattr(e, k, v)
    db.commit()
    return _out(e)


@router.delete("/events/{eid}", status_code=204)
def delete_event(eid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_own(db, user, eid))
    db.commit()


@router.get("/events/{eid}.ics")
def event_ics(eid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = _own(db, user, eid)
    return Response(calendar([_event_lines(e)], e.title), media_type=ICS,
                    headers={"Content-Disposition": f'attachment; filename="event-{e.id}.ics"'})


def _feed_urls(token: str) -> FeedOut:
    url = f"{get_settings().public_api_url.rstrip('/')}/calendar/feed/{token}.ics"
    return FeedOut(feed_url=url, webcal_url="webcal://" + url.split("://", 1)[1])


@router.post("/feed", response_model=FeedOut)
def create_feed(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create or rotate the private feed URL (rotating revokes the old one)."""
    user.calendar_token = secrets.token_urlsafe(32)
    db.commit()
    return _feed_urls(user.calendar_token)


@router.delete("/feed", status_code=204)
def revoke_feed(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.calendar_token = None
    db.commit()


@router.get("/feed/{token}.ics", include_in_schema=False)
def feed(token: str, db: Session = Depends(get_db)):
    """Subscribed to by Google/Outlook/Apple Calendar. The unguessable token is the credential (like a private
    iCal link); rotate it from the app if it leaks."""
    user = db.scalar(select(User).where(User.calendar_token == token)) if len(token) >= 32 else None
    if user is None:
        raise AppError("Calendar feed not found.", code="not_found", status_code=404)
    since = datetime.now(timezone.utc) - timedelta(days=30)
    events = [_event_lines(e) for e in user.events if _aware(e.starts_at) >= since]
    for a in user.applications:  # tracker "next step" dates as all-day items
        if a.next_action_on and a.status not in ("rejected", "withdrawn", "offer"):
            events.append(vevent(f"app-{a.id}@job-search-agent", f"Next step: {a.title} at {a.company} ({a.status})",
                                 a.next_action_on, alarms=(540,)))
    return Response(calendar(events, "Job search"), media_type=ICS, headers={"Cache-Control": "private, max-age=900"})
