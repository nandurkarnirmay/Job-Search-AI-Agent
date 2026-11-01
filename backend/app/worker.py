"""Celery worker + beat for scheduled jobs (local docker-compose, or any host with a worker process).
Run: celery -A app.worker worker --beat --loglevel=info
On free hosting without workers, GitHub Actions calls POST /internal/alerts/dispatch instead (same function)."""
from celery import Celery

from app.config import get_settings
from app.db import SessionLocal
from app.services.alert_dispatch import dispatch_due_alerts

broker = get_settings().redis_url or "redis://localhost:6379/0"
celery_app = Celery("jobagent", broker=broker)
celery_app.conf.update(
    timezone="Asia/Kolkata",
    task_ignore_result=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={"dispatch-alerts-hourly": {"task": "alerts.dispatch", "schedule": 3600.0}},
)


@celery_app.task(name="alerts.dispatch")
def dispatch_alerts() -> dict:
    with SessionLocal() as db:
        return dispatch_due_alerts(db)
