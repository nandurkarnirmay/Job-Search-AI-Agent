from tests.conftest import job, register


def test_save_from_search_uses_server_side_job_details(auth_client, sources):
    sources[0]._jobs = [job(70, title="Backend Engineer", company="Zoho", salary_min_lpa=8, salary_max_lpa=12)]
    auth_client.get("/jobs/search", params={"q": "backend"})
    a = auth_client.post("/applications", json={"job_id": "fake:70", "title": "Spoofed", "company": "Spoofed"}).json()
    assert (a["title"], a["company"], a["salary_max_lpa"], a["status"]) == ("Backend Engineer", "Zoho", 12, "saved")
    dup = auth_client.post("/applications", json={"job_id": "fake:70"})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "already_tracked"


def test_manual_entry_and_url_validation(auth_client):
    ok = auth_client.post("/applications", json={"title": "SDE-1", "company": "Flipkart", "url": "https://x.com/1"})
    assert ok.status_code == 201
    bad = auth_client.post("/applications", json={"title": "SDE", "company": "Acme", "url": "javascript:alert(1)"})
    assert bad.status_code == 422
    assert auth_client.post("/applications", json={"title": "SDE"}).status_code == 422
    assert auth_client.post("/applications", json={"job_id": "fake:expired"}).json()["error"]["code"] == "job_expired"


def test_status_history_pipeline_and_filter(auth_client):
    a = auth_client.post("/applications", json={"title": "Data Analyst", "company": "TCS"}).json()
    auth_client.post("/applications", json={"title": "ML Engineer", "company": "Swiggy"})
    r = auth_client.patch(f"/applications/{a['id']}", json={"status": "applied", "next_action_on": "2026-11-15",
                                                            "notes": "Referred by a senior"}).json()
    assert [h["status"] for h in r["history"]] == ["saved", "applied"] and r["next_action_on"] == "2026-11-15"
    auth_client.patch(f"/applications/{a['id']}", json={"notes": "follow up"})      # no status change: no history
    assert len(auth_client.get("/applications", params={"status": "applied"}).json()[0]["history"]) == 2
    p = auth_client.get("/applications/pipeline").json()
    assert p["applied"] == 1 and p["saved"] == 1 and p["offer"] == 0
    assert auth_client.patch(f"/applications/{a['id']}", json={"status": "hired"}).status_code == 422


def test_applications_are_private(client, auth_client):
    a = auth_client.post("/applications", json={"title": "Data Analyst", "company": "TCS"}).json()
    other = register(client, "other@example.com")
    assert client.patch(f"/applications/{a['id']}", json={"status": "offer"}, headers=other).status_code == 404
    assert client.get("/applications", headers=other).json() == []
    assert auth_client.delete(f"/applications/{a['id']}").status_code == 204
