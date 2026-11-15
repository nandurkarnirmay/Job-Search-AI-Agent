"""Analytics dashboards: your own job-search funnel (any user) and system performance (admins)."""
import statistics
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_admin
from app.models import AlertRun, Application, ChatMessage, InterviewSession, JobAlert, SearchLog, User

router = APIRouter(prefix="/analytics", tags=["analytics"])
REACHED = {"applied": {"applied", "interview", "offer", "rejected"}, "interview": {"interview", "offer"},
           "offer": {"offer"}}
WEEKS = 8


def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _week_index(dt: datetime, now: datetime) -> int | None:
    i = WEEKS - 1 - (now - _aware(dt)).days // 7
    return i if 0 <= i < WEEKS else None


def funnel(apps: list[Application]) -> dict:
    """Stages are counted by what each application ever reached (from its status history), so a rejection
    after an interview still counts as an interview."""
    reached = Counter()
    days_to_apply = []
    for a in apps:
        statuses = {h["status"] for h in (a.history or [])} | {a.status}
        for stage, ok in REACHED.items():
            if statuses & ok:
                reached[stage] += 1
        saved = next((h["at"] for h in a.history or [] if h["status"] == "saved"), None)
        applied = next((h["at"] for h in a.history or [] if h["status"] == "applied"), None)
        if saved and applied:
            days_to_apply.append((datetime.fromisoformat(applied) - datetime.fromisoformat(saved)).days)
    applied, interviewed = reached["applied"], reached["interview"]
    return {
        "tracked": len(apps), "applied": applied, "interviews": interviewed, "offers": reached["offer"],
        "interview_rate": round(interviewed / applied, 2) if applied else None,
        "offer_rate": round(reached["offer"] / interviewed, 2) if interviewed else None,
        "median_days_saved_to_applied": statistics.median(days_to_apply) if days_to_apply else None,
    }


@router.get("/me")
def my_analytics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    since = now - timedelta(weeks=WEEKS)
    apps = list(user.applications)
    searches = db.scalars(select(SearchLog).where(SearchLog.user_id == user.id, SearchLog.created_at >= since)).all()
    weekly = {k: [0] * WEEKS for k in ("searches", "applications", "practice_sessions")}
    for s in searches:
        if (i := _week_index(s.created_at, now)) is not None:
            weekly["searches"][i] += 1
    for a in apps:
        if (i := _week_index(a.created_at, now)) is not None:
            weekly["applications"][i] += 1
    sessions = sorted(user.interviews, key=lambda s: s.id)
    for s in sessions:
        if (i := _week_index(s.created_at, now)) is not None:
            weekly["practice_sessions"][i] += 1
    practice = []
    for s in sessions[-10:]:
        scores = [a["feedback"]["score"] for a in (s.answers or {}).values() if a.get("feedback")]
        if scores:
            practice.append({"session": s.id, "role": s.role, "average": round(sum(scores) / len(scores), 1),
                             "answered": len(scores)})
    keywords = Counter(kw.lower() for s in searches if (kw := (s.filters or {}).get("keywords")))
    alert_ids = [a.id for a in user.alerts]
    runs = db.scalars(select(AlertRun).where(AlertRun.alert_id.in_(alert_ids))).all() if alert_ids else []
    return {
        "funnel": funnel(apps),
        "pipeline": dict(Counter(a.status for a in apps)),
        "weekly": weekly,
        "week_starts": [(now - timedelta(weeks=WEEKS - 1 - i)).date().isoformat() for i in range(WEEKS)],
        "practice_trend": practice,
        "top_searches": [{"keywords": k, "count": n} for k, n in keywords.most_common(5)],
        "alerts": {"active": sum(a.active for a in user.alerts), "runs": len(runs),
                   "new_jobs_found": sum(r.new_jobs for r in runs)},
        "skills": dict(Counter(p.status for p in user.skill_progress)),
    }


@router.get("/system")
def system_analytics(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    week = now - timedelta(days=7)
    logs = db.scalars(select(SearchLog).where(SearchLog.created_at >= week)).all()
    lat = sorted(s.latency_ms for s in logs)
    misses = sorted(s.latency_ms for s in logs if not s.cache_hit)
    failures = Counter(name for s in logs for name in (s.sources_failed or []))
    daily = Counter(_aware(s.created_at).date().isoformat() for s in logs)

    def pct(vals: list[int], q: float) -> int | None:
        return vals[min(len(vals) - 1, int(q * len(vals)))] if vals else None

    return {
        "users": {"total": db.scalar(select(func.count()).select_from(User)),
                  "new_7d": db.scalar(select(func.count()).select_from(User).where(User.created_at >= week)),
                  "active_7d": len({s.user_id for s in logs if s.user_id})},
        "searches_7d": len(logs),
        "searches_per_day": dict(sorted(daily.items())),
        "latency_ms": {"p50": pct(lat, 0.5), "p95": pct(lat, 0.95), "p95_uncached": pct(misses, 0.95)},
        "cache_hit_rate": round(sum(s.cache_hit for s in logs) / len(logs), 3) if logs else None,
        "zero_result_rate": round(sum(s.result_count == 0 for s in logs) / len(logs), 3) if logs else None,
        "source_failures_7d": dict(failures),
        "chat_intents_7d": dict(db.execute(select(ChatMessage.intent, func.count())
                                           .where(ChatMessage.role == "assistant", ChatMessage.created_at >= week)
                                           .group_by(ChatMessage.intent)).all()),
        "tracker": dict(db.execute(select(Application.status, func.count()).group_by(Application.status)).all()),
        "alerts_active": db.scalar(select(func.count()).select_from(JobAlert).where(JobAlert.active.is_(True))),
        "interview_sessions_7d": db.scalar(select(func.count()).select_from(InterviewSession)
                                           .where(InterviewSession.created_at >= week)),
    }
