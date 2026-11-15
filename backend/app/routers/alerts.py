from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user, rate_limited
from app.errors import AppError, ConflictError
from app.models import JobAlert, User
from app.schemas import AlertIn, AlertOut, AlertPatch, AlertPreview, AlertRunOut
from app.services.alert_dispatch import read_unsubscribe_token
from app.services.alerts import run_alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _own(db: Session, user: User, alert_id: int) -> JobAlert:
    alert = db.get(JobAlert, alert_id)
    if alert is None or alert.user_id != user.id:  # 404 for other users' alerts too: don't leak existence
        raise AppError("Alert not found.", code="not_found", status_code=404)
    return alert


def _out(a: JobAlert) -> AlertOut:
    return AlertOut.model_validate(a, from_attributes=True)


@router.get("/unsubscribe", response_class=HTMLResponse, include_in_schema=False)
def unsubscribe(token: str = Query(max_length=500), db: Session = Depends(get_db)):
    """One-click unsubscribe from the email link (no login needed; the signed token identifies the alert)."""
    alert_id = read_unsubscribe_token(token)
    alert = db.get(JobAlert, alert_id) if alert_id else None
    if alert is None:
        return HTMLResponse("<p>This unsubscribe link is invalid or the alert was deleted.</p>", status_code=404)
    alert.active = False
    db.commit()
    return HTMLResponse("<p>Unsubscribed: this alert is paused. You can resume it on the Alerts page.</p>")


@router.get("", response_model=list[AlertOut])
def list_alerts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(JobAlert).where(JobAlert.user_id == user.id).order_by(JobAlert.id)).all()
    return [_out(a) for a in rows]


@router.post("", response_model=AlertOut, status_code=201)
def create_alert(body: AlertIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    limit = get_settings().max_alerts_per_user
    count = db.scalar(select(func.count()).select_from(JobAlert).where(JobAlert.user_id == user.id))
    if count >= limit:
        raise ConflictError(f"You can have at most {limit} alerts. Delete one first.", code="alert_limit")
    alert = JobAlert(user_id=user.id, name=body.name.strip(), frequency=body.frequency, active=True, seen_keys=[],
                     params=body.params.model_dump(exclude_none=True))
    db.add(alert)
    db.commit()
    return _out(alert)


@router.patch("/{alert_id}", response_model=AlertOut)
def update_alert(alert_id: int, body: AlertPatch, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    alert = _own(db, user, alert_id)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(alert, key, value)
    db.commit()
    return _out(alert)


@router.delete("/{alert_id}", status_code=204)
def delete_alert(alert_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_own(db, user, alert_id))
    db.commit()


@router.post("/{alert_id}/preview", response_model=AlertPreview)
def preview_alert(alert_id: int, user: User = Depends(rate_limited), db: Session = Depends(get_db)):
    """What the next alert would contain. Doesn't mark anything as sent."""
    fresh, total = run_alert(db, _own(db, user, alert_id), mark_seen=False)
    return AlertPreview(total=total, new=len(fresh), jobs=fresh[:20])


@router.get("/{alert_id}/runs", response_model=list[AlertRunOut])
def alert_runs(alert_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Recent scheduled runs, including the digest of new jobs (the in-app inbox when email is off)."""
    return [AlertRunOut.model_validate(r, from_attributes=True) for r in _own(db, user, alert_id).runs[:10]]
