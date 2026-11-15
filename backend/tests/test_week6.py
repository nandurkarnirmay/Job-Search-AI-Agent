"""Week 6: calendar integration (events, ICS feed, reminders) and voice mock interviews with follow-ups."""
from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import job, register

from app.config import get_settings
from app.db import SessionLocal
from app.models import CalendarEvent
from app.services import reminders
from app.services.email import EmailError

IST = timezone(timedelta(hours=5, minutes=30))


def soon(hours: float) -> str:
    return (datetime.now(IST) + timedelta(hours=hours)).isoformat()


def test_event_crud_and_validation(auth_client):
    r = auth_client.post("/calendar/events", json={"title": "Interview: Data Analyst, Infosys",
                                                   "starts_at": "2026-12-01T15:00:00+05:30",
                                                   "location": "https://meet.example.com/x"})
    e = r.json()
    assert r.status_code == 201 and e["starts_at"].startswith("2026-12-01T09:30")      # stored in UTC
    assert e["google_calendar_url"].startswith("https://calendar.google.com/calendar/render?action=TEMPLATE")
    assert auth_client.post("/calendar/events", json={"title": "x y", "starts_at": "2026-12-01T15:00:00"}) \
        .status_code == 422                                                              # timezone required
    moved = auth_client.patch(f"/calendar/events/{e['id']}", json={"starts_at": "2026-12-02T11:00:00+05:30"}).json()
    assert moved["starts_at"].startswith("2026-12-02T05:30")
    ics = auth_client.get(f"/calendar/events/{e['id']}.ics")
    assert ics.headers["content-type"].startswith("text/calendar") and "DTSTART:20261202T053000Z" in ics.text
    assert "\r\n" in ics.text and "BEGIN:VALARM" in ics.text
    assert auth_client.delete(f"/calendar/events/{e['id']}").status_code == 204


def test_events_are_private_and_linked_apps_checked(client, auth_client):
    e = auth_client.post("/calendar/events", json={"title": "Interview", "starts_at": soon(48)}).json()
    other = register(client, "other@example.com")
    assert client.patch(f"/calendar/events/{e['id']}", json={"title": "hack"}, headers=other).status_code == 404
    app_id = client.post("/applications", json={"title": "SDE", "company": "X"}, headers=other).json()["id"]
    r = auth_client.post("/calendar/events", json={"title": "Interview", "starts_at": soon(48),
                                                   "application_id": app_id})
    assert r.status_code == 404


def test_private_feed_includes_events_and_tracker_dates(client, auth_client):
    auth_client.post("/calendar/events", json={"title": "Interview: Zoho, round 1", "starts_at": soon(30)})
    a = auth_client.post("/applications", json={"title": "Data Analyst", "company": "TCS"}).json()
    auth_client.patch(f"/applications/{a['id']}", json={"next_action_on": "2026-12-05"})
    feed = auth_client.post("/calendar/feed").json()
    assert feed["webcal_url"].startswith("webcal://")
    token_path = feed["feed_url"].split("/calendar/")[1]
    ics = client.get(f"/calendar/{token_path}")                         # no login: the token is the credential
    assert ics.status_code == 200 and "Interview: Zoho\\, round 1" in ics.text
    assert "DTSTART;VALUE=DATE:20261205" in ics.text and "Next step: Data Analyst at TCS" in ics.text
    auth_client.post("/calendar/feed")                                   # rotate: old link stops working
    assert client.get(f"/calendar/{token_path}").status_code == 404
    assert client.get("/calendar/feed/short.ics").status_code == 404


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    s = get_settings()
    monkeypatch.setattr(s, "smtp_host", "smtp.test")
    monkeypatch.setattr(s, "email_from", "alerts@test")

    def fake_send(to, subject, text, html=None, headers=None):
        if getattr(fake_send, "fail", False):
            raise EmailError("550")
        sent.append((to, subject, text))
        return True

    monkeypatch.setattr(reminders, "send_email", fake_send)
    return sent, fake_send


def test_reminders_sent_once_and_retried_on_failure(auth_client, outbox):
    sent, fake_send = outbox
    auth_client.post("/calendar/events", json={"title": "Interview: Zoho", "starts_at": soon(20)})
    auth_client.post("/calendar/events", json={"title": "Later interview", "starts_at": soon(72)})
    auth_client.post("/calendar/events", json={"title": "No reminder", "starts_at": soon(5), "remind": False})
    fake_send.fail = True
    with SessionLocal() as db:
        assert reminders.dispatch_reminders(db)["reminder_errors"] == 1
    fake_send.fail = False
    with SessionLocal() as db:
        assert reminders.dispatch_reminders(db)["reminders"] == 1
        assert reminders.dispatch_reminders(db)["reminders"] == 0            # not sent twice
        assert db.query(CalendarEvent).filter(CalendarEvent.reminder_sent_at.isnot(None)).count() == 1
    assert sent[0][1] == "Tomorrow: Interview: Zoho" and "IST" in sent[0][2]


def test_reminders_skip_without_email(auth_client):
    auth_client.post("/calendar/events", json={"title": "Interview", "starts_at": soon(3)})
    with SessionLocal() as db:
        assert reminders.dispatch_reminders(db) == {"reminders": 0, "reminder_errors": 0}


# ---------- voice mock interview ----------

def _session(auth_client, sources):
    sources[0]._jobs = [job(60, title="Data Analyst", company="Infosys", description="SQL and Python, Power BI")]
    auth_client.get("/jobs/search", params={"q": "data analyst"})
    return auth_client.post("/interview/sessions", json={"job_id": "fake:60"}).json()


def test_spoken_answer_metrics_and_followup(auth_client, sources):
    s = _session(auth_client, sources)
    sql = next(q for q in s["questions"] if q["skill"] == "SQL")
    r = auth_client.post(f"/interview/sessions/{s['id']}/questions/{sql['id']}/answer", json={
        "answer": "Um so basically WHERE filters rows, like, you know, and HAVING is for, uh, groups I think",
        "duration_seconds": 6, "long_pauses": 3}).json()
    sp = r["feedback"]["speech"]
    assert sp["words_per_minute"] > 160 and sp["filler_per_100_words"] > 10
    assert {"Pace", "Fluency"} <= {c["name"] for c in r["feedback"]["criteria"]}
    fu = r["followup"]
    assert fu["id"] == f"{sql['id']}f" and fu["parent_id"] == sql["id"] and fu["source"] == "followup"
    ids = [q["id"] for q in auth_client.get(f"/interview/sessions/{s['id']}").json()["questions"]]
    assert ids[ids.index(sql["id"]) + 1] == fu["id"]                         # inserted right after its parent
    again = auth_client.post(f"/interview/sessions/{s['id']}/questions/{sql['id']}/answer",
                             json={"answer": "Second attempt: WHERE filters rows before grouping."}).json()
    assert again["followup"] is None                                          # one follow-up per question
    deeper = auth_client.post(f"/interview/sessions/{s['id']}/questions/{fu['id']}/answer",
                              json={"answer": "HAVING filters after GROUP BY using aggregates like SUM."}).json()
    assert deeper["followup"] is None                                         # follow-ups don't nest


def test_session_report(auth_client, sources):
    s = _session(auth_client, sources)
    assert auth_client.get(f"/interview/sessions/{s['id']}/report").json()["answered"] == 0
    for q in s["questions"][:3]:
        auth_client.post(f"/interview/sessions/{s['id']}/questions/{q['id']}/answer",
                         json={"answer": "During my internship I built a dashboard and reporting time dropped 40%.",
                               "duration_seconds": 8})
    rep = auth_client.get(f"/interview/sessions/{s['id']}/report").json()
    assert rep["answered"] == 3 and rep["average_score"] is not None and rep["average_wpm"] is not None
    assert rep["next_steps"] and set(rep["by_category"]) <= {"hr", "technical", "behavioural"}


def test_ics_escaping_and_folding():
    from app.services.calendar_ics import calendar, vevent
    start = datetime(2026, 12, 2, 5, 30, tzinfo=timezone.utc)
    desc = "Line one\nBring ID, résumé " + "x" * 120
    ev = calendar([vevent("u1", "Interview; round 1, HR", start, description=desc, now=start)])
    lines = ev.split("\r\n")
    assert r"SUMMARY:Interview\; round 1\, HR" in lines
    assert all(len(line.encode()) <= 75 for line in lines)                 # RFC 5545 octet limit
    assert any(line.startswith(" ") for line in lines)                     # long description folded
    assert ev.count("BEGIN:VALARM") == 2 and "TRIGGER:-PT1440M" in ev


@pytest.mark.parametrize("text,expected", [
    ("₹25,000 - ₹35,000 a month", (3.0, 4.2)),
    ("Rs. 6L - 9L per annum", (6.0, 9.0)),
    ("Call 9876543210 to apply", (None, None)),
])
def test_indian_salary_text(text, expected):
    from app.sources.normalize import salary_lpa_from_inr_text
    assert salary_lpa_from_inr_text(text) == expected
