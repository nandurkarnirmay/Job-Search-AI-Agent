"""Admin-only search performance & engagement numbers from search_logs.
(Admin-only because queries can contain personal details. Feeds the Week 7 analytics dashboard.)"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models import ChatMessage, SearchLog, User

router = APIRouter(prefix="/stats", tags=["monitoring"])


@router.get("/search")
def search_stats(days: int = Query(default=7, ge=1, le=90), _: User = Depends(require_admin),
                 db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    base = select(SearchLog).where(SearchLog.created_at >= since).subquery()
    total, avg_ms, zero, hits, users = db.execute(select(
        func.count(), func.avg(base.c.latency_ms),
        func.sum(case((base.c.result_count == 0, 1), else_=0)),
        func.sum(case((base.c.cache_hit.is_(True), 1), else_=0)),
        func.count(func.distinct(base.c.user_id)),
    ).select_from(base)).one()
    by_channel = dict(db.execute(select(base.c.channel, func.count()).group_by(base.c.channel)).all())
    top = db.execute(select(base.c.query, func.count().label("n")).group_by(base.c.query)
                     .order_by(func.count().desc()).limit(10)).all()
    intents = dict(db.execute(select(ChatMessage.intent, func.count())
                              .where(ChatMessage.role == "assistant", ChatMessage.created_at >= since)
                              .group_by(ChatMessage.intent)).all())
    total = total or 0
    return {
        "days": days, "searches": total, "active_users": users or 0, "by_channel": by_channel,
        "avg_latency_ms": round(avg_ms or 0), "zero_result_rate": round((zero or 0) / total, 3) if total else 0,
        "cache_hit_rate": round((hits or 0) / total, 3) if total else 0,
        "top_queries": [{"query": q, "count": n} for q, n in top],
        "chat_intents": intents,
    }
