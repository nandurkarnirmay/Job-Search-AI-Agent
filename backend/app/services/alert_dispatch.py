"""Scheduled alert delivery. One function, two schedulers: Celery beat (app/worker.py, when a worker is
running) and a GitHub Actions cron hitting POST /internal/alerts/dispatch (free tier, no worker needed).

Delivery rule: jobs are marked as 'sent' only after the email succeeded (or when email is disabled and the
digest is stored for in-app viewing), so a failed send is retried on the next run instead of being lost."""
import html
import logging
from datetime import datetime, timezone

import jwt
from sqlalchemy.orm import Session

from app.cache import get_cache
from app.config import get_settings
from app.domain import JobListing
from app.errors import AllSourcesFailedError
from app.models import AlertRun, JobAlert
from app.monitoring import ALERT_RUNS
from app.services.alerts import due_alerts, record_seen, run_alert
from app.services.email import EmailError, email_enabled, send_email

log = logging.getLogger("app.alert_dispatch")
LOCK_KEY, LOCK_TTL = "lock:alert-dispatch", 900
MAX_JOBS_PER_EMAIL = 15


def unsubscribe_token(alert_id: int) -> str:
    return jwt.encode({"alert": alert_id, "purpose": "unsubscribe"}, get_settings().jwt_secret, algorithm="HS256")


def read_unsubscribe_token(token: str) -> int | None:
    try:
        data = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
        return int(data["alert"]) if data.get("purpose") == "unsubscribe" else None
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


def _salary(j: JobListing) -> str:
    lo, hi = j.salary_min_lpa, j.salary_max_lpa
    if lo is None and hi is None:
        return ""
    lo, hi = lo or hi, hi or lo
    return f" · ₹{lo:g} LPA" if lo == hi else f" · ₹{lo:g}–{hi:g} LPA"


def render_email(alert: JobAlert, jobs: list[JobListing]) -> tuple[str, str, str, str]:
    """(subject, text, html, unsubscribe_url). All job fields are HTML-escaped (they come from third parties)."""
    s = get_settings()
    unsub = f"{s.public_api_url.rstrip('/')}/alerts/unsubscribe?token={unsubscribe_token(alert.id)}"
    shown = jobs[:MAX_JOBS_PER_EMAIL]
    more = len(jobs) - len(shown)
    subject = f"{len(jobs)} new job{'s' if len(jobs) != 1 else ''}: {alert.name}"
    lines = [f"{len(jobs)} new jobs for your alert '{alert.name}':", ""]
    lines += [f"- {j.title} at {j.company}, {j.location}{_salary(j)}\n  {j.url}" for j in shown]
    if more:
        lines.append(f"...and {more} more: {s.public_app_url}/alerts")
    lines += ["", f"Manage alerts: {s.public_app_url}/alerts", f"Unsubscribe from this alert: {unsub}"]
    e = html.escape

    def link(j: JobListing) -> str:  # only http(s) links: job URLs come from third-party APIs
        return f'<a href="{e(j.url, quote=True)}">{e(j.title)}</a>' if j.url.startswith(("https://", "http://")) \
            else e(j.title)

    items = "".join(
        f'<li style="margin-bottom:10px">{link(j)}<br>'
        f'<span style="color:#555">{e(j.company)} · {e(j.location)}{e(_salary(j))}</span></li>' for j in shown)
    body = (f'<p>{len(jobs)} new jobs for your alert <b>{e(alert.name)}</b>:</p><ul>{items}</ul>'
            + (f'<p>…and {more} more on <a href="{e(s.public_app_url)}/alerts">your alerts page</a>.</p>'
               if more else "")
            + f'<p style="color:#777;font-size:12px"><a href="{e(s.public_app_url)}/alerts">Manage alerts</a> · '
              f'<a href="{e(unsub, quote=True)}">Unsubscribe from this alert</a></p>')
    return subject, "\n".join(lines), body, unsub


def deliver(db: Session, alert: JobAlert) -> AlertRun:
    run = AlertRun(alert_id=alert.id, ran_at=datetime.now(timezone.utc), new_jobs=0, emailed=False, digest=[])
    try:
        fresh, _ = run_alert(db, alert, mark_seen=False)
    except AllSourcesFailedError:
        run.error = "job sources unavailable; will retry next run"
        ALERT_RUNS.labels("sources_down").inc()
        db.add(run)
        db.commit()
        return run  # last_run_at untouched, so it's still due next time
    run.new_jobs = len(fresh)
    run.digest = [j.model_dump(include={"id", "title", "company", "location", "url", "salary_min_lpa",
                                        "salary_max_lpa"}) for j in fresh[:30]]
    if fresh and email_enabled():
        subject, text, body, unsub = render_email(alert, fresh)
        try:
            run.emailed = send_email(alert.user.email, subject, text, body,
                                     headers={"List-Unsubscribe": f"<{unsub}>"})
        except EmailError as e:
            run.error = f"email failed: {e}"[:300]
            ALERT_RUNS.labels("email_error").inc()
            db.add(run)
            db.commit()
            return run  # not marked as seen: retried next run
    record_seen(db, alert, fresh)  # also sets last_run_at and commits
    db.add(run)
    db.commit()
    ALERT_RUNS.labels("emailed" if run.emailed else "in_app").inc()
    return run


def dispatch_due_alerts(db: Session, now: datetime | None = None) -> dict:
    """Run every due alert once. A cache lock stops Celery beat and the cron endpoint double-sending."""
    cache = get_cache()
    if cache.incr(LOCK_KEY, LOCK_TTL) > 1:
        return {"skipped": "another dispatch is running"}
    summary = {"alerts": 0, "new_jobs": 0, "emailed": 0, "errors": 0}
    try:
        for alert in due_alerts(db, now):
            run = deliver(db, alert)
            summary["alerts"] += 1
            summary["new_jobs"] += run.new_jobs
            summary["emailed"] += int(run.emailed)
            summary["errors"] += int(run.error is not None)
    finally:
        cache.delete(LOCK_KEY)
    log.info("alert dispatch finished: %s", summary)
    return summary
