from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import job

from app.config import get_settings
from app.db import SessionLocal
from app.domain import JobListing
from app.models import AlertRun, JobAlert
from app.services import alert_dispatch as ad
from app.services.email import EmailError

ALERT = {"name": "Python BLR", "params": {"keywords": "python developer", "city": "Bengaluru"}, "frequency": "daily"}


@pytest.fixture
def outbox(monkeypatch):
    """Turn email on and capture messages instead of sending."""
    sent = []
    s = get_settings()
    monkeypatch.setattr(s, "smtp_host", "smtp.test")
    monkeypatch.setattr(s, "email_from", "alerts@test")

    def fake_send(to, subject, text, html=None, headers=None):
        if getattr(fake_send, "fail", False):
            raise EmailError("550 rejected")
        sent.append({"to": to, "subject": subject, "text": text, "html": html, "headers": headers})
        return True

    monkeypatch.setattr(ad, "send_email", fake_send)
    return sent, fake_send


def _alert(auth_client) -> int:
    return auth_client.post("/alerts", json=ALERT).json()["id"]


def test_email_disabled_keeps_in_app_digest(auth_client, sources):
    aid = _alert(auth_client)
    with SessionLocal() as db:
        summary = ad.dispatch_due_alerts(db)
    assert summary["alerts"] == 1 and summary["emailed"] == 0 and summary["new_jobs"] > 0
    runs = auth_client.get(f"/alerts/{aid}/runs").json()
    assert runs[0]["emailed"] is False and runs[0]["digest"] and runs[0]["error"] is None
    with SessionLocal() as db:
        assert ad.dispatch_due_alerts(db)["alerts"] == 0            # ran today: daily alert not due again


def test_email_sent_with_unsubscribe(auth_client, sources, outbox):
    sent, _ = outbox
    aid = _alert(auth_client)
    with SessionLocal() as db:
        assert ad.dispatch_due_alerts(db)["emailed"] == 1
    msg = sent[0]
    assert msg["to"] == "user@example.com" and "new job" in msg["subject"]
    assert "List-Unsubscribe" in msg["headers"] and "unsubscribe?token=" in msg["text"]
    token = msg["text"].split("unsubscribe?token=")[1].split()[0]
    assert ad.read_unsubscribe_token(token) == aid


def test_failed_email_is_retried_not_lost(auth_client, sources, outbox):
    _, fake_send = outbox
    aid = _alert(auth_client)
    fake_send.fail = True
    with SessionLocal() as db:
        assert ad.dispatch_due_alerts(db)["errors"] == 1
        alert = db.get(JobAlert, aid)
        assert alert.seen_keys == [] and alert.last_run_at is None    # nothing marked as sent
    fake_send.fail = False
    with SessionLocal() as db:
        assert ad.dispatch_due_alerts(db)["emailed"] == 1             # still due, delivered on the retry


def test_sources_down_is_retried(auth_client, sources):
    aid = _alert(auth_client)
    for s in sources:
        s.fail = True
    with SessionLocal() as db:
        assert ad.dispatch_due_alerts(db)["errors"] == 1
        assert db.get(JobAlert, aid).last_run_at is None
        assert "unavailable" in db.query(AlertRun).one().error


def test_no_new_jobs_means_no_email(auth_client, sources, outbox):
    sent, _ = outbox
    aid = _alert(auth_client)
    with SessionLocal() as db:
        ad.dispatch_due_alerts(db)
        db.get(JobAlert, aid).last_run_at = datetime.now(timezone.utc) - timedelta(days=2)
        db.commit()
        assert ad.dispatch_due_alerts(db)["new_jobs"] == 0
    assert len(sent) == 1


def test_lock_prevents_double_dispatch(auth_client, sources):
    _alert(auth_client)
    from app.cache import get_cache
    get_cache().incr(ad.LOCK_KEY, 60)                                 # another dispatcher is running
    with SessionLocal() as db:
        assert "skipped" in ad.dispatch_due_alerts(db)


def test_cron_endpoint_requires_token(client, monkeypatch, sources):
    assert client.post("/internal/alerts/dispatch").status_code == 404          # disabled without CRON_TOKEN
    monkeypatch.setattr(get_settings(), "cron_token", "s3cret")
    assert client.post("/internal/alerts/dispatch", headers={"X-Cron-Token": "wrong"}).status_code == 401
    r = client.post("/internal/alerts/dispatch", headers={"X-Cron-Token": "s3cret"})
    assert r.status_code == 200 and r.json()["alerts"] == 0


def test_unsubscribe_link(client, auth_client):
    aid = _alert(auth_client)
    r = client.get("/alerts/unsubscribe", params={"token": ad.unsubscribe_token(aid)})
    assert r.status_code == 200 and "Unsubscribed" in r.text
    assert auth_client.get("/alerts").json()[0]["active"] is False
    assert client.get("/alerts/unsubscribe", params={"token": "forged"}).status_code == 404


def test_email_escapes_third_party_html():
    alert = JobAlert(id=1, name="<b>x</b>", params={}, frequency="daily")
    evil = JobListing(id="1", title="<script>alert(1)</script>", company="A&B", location="Pune",
                      url="javascript:alert(1)", source="s")
    subject, text, html_body, _ = ad.render_email(alert, [evil, job(2)])
    assert "<script>" not in html_body and "&lt;script&gt;" in html_body
    assert 'href="javascript' not in html_body and "A&amp;B" in html_body
