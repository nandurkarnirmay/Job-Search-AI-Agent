"""User data rights: download everything we hold about you (account deletion is DELETE /auth/me)."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import SearchLog, User

router = APIRouter(prefix="/me", tags=["privacy"])


def _row(obj, exclude: set[str] = frozenset()) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns if c.name not in exclude}


@router.get("/export")
def export(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "account": _row(user, {"password_hash", "calendar_token"}),
        "profile": _row(user.profile) if user.profile else None,
        "resume": _row(user.resume) if user.resume else None,
        "applications": [_row(a) for a in user.applications],
        "alerts": [_row(a, {"seen_keys"}) for a in user.alerts],
        "conversations": [{**_row(t), "messages": [_row(m) for m in t.messages]} for t in user.threads],
        "interview_sessions": [_row(s) for s in user.interviews],
        "calendar_events": [_row(e) for e in user.events],
        "skill_progress": [_row(p) for p in user.skill_progress],
        "search_history": [_row(s) for s in db.scalars(select(SearchLog).where(SearchLog.user_id == user.id)
                                                       .order_by(SearchLog.id.desc()).limit(500))],
    }
    body = json.dumps(data, default=str, indent=2, ensure_ascii=False)
    return Response(body, media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="my-job-search-data.json"'})
