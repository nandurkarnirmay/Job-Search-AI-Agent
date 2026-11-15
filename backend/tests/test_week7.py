"""Week 7: encryption at rest, data export, retention, security headers, metrics token, service split, analytics."""
import importlib
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import text

from tests.conftest import register

from app.config import get_settings
from app.db import SessionLocal, engine
from app.models import ChatThread, SearchLog
from app.services.retention import purge_old_data


def _raw(sql: str):
    with engine.connect() as conn:
        return conn.execute(text(sql)).scalar()


def test_personal_text_is_encrypted_at_rest(auth_client, resume_pdf, sources):
    auth_client.post("/resume", files={"file": ("cv.pdf", resume_pdf, "application/pdf")})
    auth_client.post("/chat", json={"message": "python developer jobs"})
    a = auth_client.post("/applications", json={"title": "SDE", "company": "Zoho", "notes": "referred by Ravi"}).json()
    assert _raw("SELECT text FROM resumes").startswith("enc:v1:")
    assert _raw("SELECT content FROM chat_messages ORDER BY id LIMIT 1").startswith("enc:v1:")
    assert _raw(f"SELECT notes FROM applications WHERE id = {a['id']}").startswith("enc:v1:")
    assert "Ravi" not in _raw(f"SELECT notes FROM applications WHERE id = {a['id']}")
    assert auth_client.get("/applications").json()[0]["notes"] == "referred by Ravi"   # decrypted for its owner
    s = auth_client.post("/interview/sessions", json={"role": "Data Analyst"}).json()
    auth_client.post(f"/interview/sessions/{s['id']}/questions/q1/answer", json={"answer": "I am a final-year student"})
    raw = _raw("SELECT answers FROM interview_sessions")
    assert "final-year" not in raw and "_enc" in json.loads(raw)


def test_export_contains_everything_but_secrets(auth_client, resume_pdf):
    auth_client.post("/resume", files={"file": ("cv.pdf", resume_pdf, "application/pdf")})
    auth_client.post("/calendar/feed")
    r = auth_client.get("/me/export")
    data = r.json()
    assert "attachment" in r.headers["content-disposition"]
    assert data["account"]["email"] == "user@example.com" and "password_hash" not in data["account"]
    assert "calendar_token" not in data["account"] and "[email]" in data["resume"]["text"]


def test_retention_purges_only_old_data(auth_client, sources):
    auth_client.post("/chat", json={"message": "python developer jobs"})
    old = datetime.now(timezone.utc) - timedelta(days=400)
    with SessionLocal() as db:
        db.add(ChatThread(id="a" * 32, user_id=1, title="old", updated_at=old, created_at=old))
        db.add(SearchLog(user_id=1, channel="search", query="old", filters={}, result_count=1, latency_ms=1,
                         sources_ok=[], sources_failed=[], cache_hit=False, created_at=old))
        db.commit()
        out = purge_old_data(db)
        assert out["purged_threads"] == 1 and out["purged_search_logs"] == 1
        assert db.query(ChatThread).count() == 1 and db.query(SearchLog).count() == 1   # recent ones kept


def test_security_headers(client):
    h = client.get("/health").headers
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
    assert "default-src 'none'" in h["content-security-policy"]
    assert "content-security-policy" not in client.get("/docs").headers       # Swagger UI keeps working


def test_metrics_token(client, monkeypatch):
    assert client.get("/metrics").status_code == 200
    monkeypatch.setattr(get_settings(), "metrics_token", "m3trics")
    assert client.get("/metrics").status_code == 404
    assert client.get("/metrics", headers={"X-Metrics-Token": "m3trics"}).status_code == 200


def test_service_split_mounts_only_its_routers(monkeypatch):
    import app.main as main
    try:
        monkeypatch.setattr(get_settings(), "service", "resume")
        paths = set(importlib.reload(main).app.openapi()["paths"])
        assert "/resume" in paths and "/health" in paths
        assert "/chat" not in paths and "/auth/login" not in paths and "/interview/sessions" not in paths
        monkeypatch.setattr(get_settings(), "service", "auth")
        paths = set(importlib.reload(main).app.openapi()["paths"])
        assert "/auth/login" in paths and "/me/export" in paths and "/resume" not in paths
    finally:
        monkeypatch.setattr(get_settings(), "service", "all")
        importlib.reload(main)


def test_my_analytics_funnel(auth_client, sources):
    auth_client.get("/jobs/search", params={"q": "python"})
    a = auth_client.post("/applications", json={"title": "SDE", "company": "Zoho"}).json()
    b = auth_client.post("/applications", json={"title": "DA", "company": "TCS"}).json()
    auth_client.post("/applications", json={"title": "ML", "company": "Swiggy"})
    for s in ("applied", "interview", "rejected"):           # rejected AFTER an interview still counts as one
        auth_client.patch(f"/applications/{a['id']}", json={"status": s})
    auth_client.patch(f"/applications/{b['id']}", json={"status": "applied"})
    m = auth_client.get("/analytics/me").json()
    f = m["funnel"]
    assert (f["tracked"], f["applied"], f["interviews"], f["offers"]) == (3, 2, 1, 0)
    assert f["interview_rate"] == 0.5 and m["weekly"]["searches"][-1] == 1 and len(m["week_starts"]) == 8
    assert m["top_searches"][0]["keywords"] == "python"


def test_system_analytics_admin_only(client, auth_client, sources):
    auth_client.get("/jobs/search", params={"q": "python"})
    assert auth_client.get("/analytics/system").status_code == 403
    admin = register(client, "admin@example.com")
    r = client.get("/analytics/system", headers=admin).json()
    assert r["searches_7d"] == 1 and r["users"]["total"] == 2 and r["latency_ms"]["p50"] is not None


def test_login_attempts_capped_per_account_even_with_spoofed_ip(client, monkeypatch):
    import app.ratelimit as rl
    monkeypatch.setattr(rl, "time", SimpleNamespace(time=lambda: 1_800_000_000.0))  # one fixed window
    client.post("/auth/register", json={"email": "victim@example.com", "password": "correct-horse-1"})
    codes = [client.post("/auth/login", json={"email": "victim@example.com", "password": f"guess-{i:04d}"},
                         headers={"X-Forwarded-For": f"10.0.0.{i}"}).status_code for i in range(12)]
    assert codes[:10] == [401] * 10 and codes[10] == 429
