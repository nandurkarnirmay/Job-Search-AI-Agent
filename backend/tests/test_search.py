from app.config import get_settings


def test_search_merges_dedupes_and_filters(auth_client, sources):
    r = auth_client.get("/jobs/search", params={"q": "python developer", "city": "Bangalore"})
    data = r.json()
    assert r.status_code == 200
    ids = [j["id"] for j in data["jobs"]]
    assert "fake:2" not in ids                      # Pune job filtered out by city alias
    assert len(ids) == len(set(ids))                # job 1 came from both sources, kept once
    assert data["sources_ok"] == ["primary", "secondary"]


def test_salary_and_experience_filters(auth_client, sources):
    r = auth_client.get("/jobs/search", params={"q": "python", "min_salary_lpa": 8, "max_experience_years": 2})
    jobs = r.json()["jobs"]
    ids = [j["id"] for j in jobs]
    assert "fake:2" not in ids and "fake:4" not in ids   # known to pay too little / need too much experience
    assert ids[0] == "fake:3"                            # the job KNOWN to match ranks first


def test_second_call_hits_cache(auth_client, sources):
    auth_client.get("/jobs/search", params={"q": "python"})
    r = auth_client.get("/jobs/search", params={"q": "python", "min_salary_lpa": 10})
    assert r.json()["cache_hit"] is True and sources[0].calls == 1


def test_one_source_down_still_returns_results(auth_client, sources):
    sources[1].fail = True
    data = auth_client.get("/jobs/search", params={"q": "python"}).json()
    assert data["sources_failed"] == ["secondary"] and data["count"] > 0


def test_all_sources_down_gives_clean_503(auth_client, sources):
    for s in sources:
        s.fail = True
    r = auth_client.get("/jobs/search", params={"q": "python"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "job_sources_unavailable"


def test_rate_limit(auth_client, sources, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_per_minute", 2)
    codes = [auth_client.get("/jobs/search", params={"q": "python"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_chat_uses_agent_and_profile_defaults(auth_client, sources):
    auth_client.put("/me/profile", json={"preferred_cities": ["Pune"]})
    r = auth_client.post("/chat", json={"message": "python developer jobs"})
    data = r.json()
    assert r.status_code == 200 and data["parser"] == "rules"
    assert data["params"]["city"] == "Pune"            # filled from profile
    assert all("Pune" in j["location"] or j["work_mode"] == "remote" for j in data["jobs"])
    assert "Found" in data["reply"]


def test_chat_asks_for_role_when_missing(auth_client, sources):
    data = auth_client.post("/chat", json={"message": "show me jobs"}).json()
    assert "what role" in data["reply"].lower() and data["jobs"] == []


def test_stats_admin_only(client, auth_client, sources):
    auth_client.get("/jobs/search", params={"q": "python"})
    assert auth_client.get("/stats/search").status_code == 403
    tok = client.post("/auth/register", json={"email": "admin@example.com", "password": "password123"})
    r = client.get("/stats/search", headers={"Authorization": f"Bearer {tok.json()['access_token']}"})
    assert r.status_code == 200 and r.json()["searches"] == 1


def test_health_and_metrics(client, sources):
    h = client.get("/health").json()
    assert h["database"] is True and h["cache"]["backend"] == "memory"
    assert "http_requests_total" in client.get("/metrics").text
