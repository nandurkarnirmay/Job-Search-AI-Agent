"""Data minimisation: delete what we no longer need. Runs with the scheduled dispatch."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AlertRun, ChatThread, SearchLog


def purge_old_data(db: Session, now: datetime | None = None) -> dict:
    s, now = get_settings(), now or datetime.now(timezone.utc)
    chats_before = now - timedelta(days=s.retention_days_chats)
    logs_before = now - timedelta(days=s.retention_days_search_logs)
    threads = db.scalars(select(ChatThread).where(ChatThread.updated_at < chats_before)).all()
    for t in threads:  # ORM delete so messages cascade on every database
        db.delete(t)
    logs = db.execute(delete(SearchLog).where(SearchLog.created_at < logs_before)).rowcount or 0
    runs = db.execute(delete(AlertRun).where(AlertRun.ran_at < now - timedelta(days=60))).rowcount or 0
    db.commit()
    return {"purged_threads": len(threads), "purged_search_logs": logs, "purged_alert_runs": runs}
