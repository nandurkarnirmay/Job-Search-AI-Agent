"""Endpoints for schedulers, not users. Protected by a shared secret, not JWT."""
import hmac

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import AppError
from app.services.alert_dispatch import dispatch_due_alerts

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


def _check(token: str | None) -> None:
    expected = get_settings().cron_token
    if not expected:  # disabled unless configured: don't advertise that it exists
        raise AppError("Not found.", code="not_found", status_code=404)
    if not token or not hmac.compare_digest(token, expected):
        raise AppError("Invalid cron token.", code="unauthorized", status_code=401)


@router.post("/alerts/dispatch")
def dispatch(x_cron_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    _check(x_cron_token)
    return dispatch_due_alerts(db)
