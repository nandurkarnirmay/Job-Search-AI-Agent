from datetime import datetime, timedelta, timezone

from tests.conftest import job

from app.db import SessionLocal
from app.models import JobAlert
from app.services.alerts import due_alerts, run_alert


def chat(client, message, thread_id=None):
    body = {"message": message} | ({"thread_id": thread_id} if thread_id else {})
    r = client.post("/chat", json=body)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- conversation memory ----------

def test_follow_up_refines_previous_search(auth_client, sources):
    first = chat(auth_client, "python developer jobs in Bangalore")
    assert first["intent"] == "job_search"
    follow = chat(auth_client, "what about Pune?", first["thread_id"])
    assert follow["intent"] == "refine_search" and follow["thread_id"] == first["thread_id"]
    assert follow["params"]["keywords"] == "python developer" and follow["params"]["city"] == "Pune"
    assert all("Pune" in j["location"] or j["work_mode"] == "remote" for j in follow["jobs"])


def test_follow_up_without_thread_has_no_memory(auth_client, sources):
    chat(auth_client, "python developer jobs in Bangalore")
    assert chat(auth_client, "what about Pune?")["intent"] == "help"   # new thread, nothing to refine


def test_threads_are_listed_reloaded_and_private(client, auth_client, sources):
    t = chat(auth_client, "python developer jobs")["thread_id"]
    chat(auth_client, "only remote", t)
    assert [x["id"] for x in auth_client.get("/chat/threads").json()] == [t]
    msgs = auth_client.get(f"/chat/threads/{t}").json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert msgs[1]["payload"]["jobs"] and "description" not in msgs[1]["payload"]["jobs"][0]

    other = client.post("/auth/register", json={"email": "other@example.com", "password": "password123"})
    h = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert client.get(f"/chat/threads/{t}", headers=h).status_code == 404
    r = client.post("/chat", json={"message": "only remote", "thread_id": t}, headers=h)
    assert r.status_code == 404

    assert auth_client.delete(f"/chat/threads/{t}").status_code == 204
    assert auth_client.get("/chat/threads").json() == []


def test_bad_thread_id_rejected(auth_client, sources):
    r = auth_client.post("/chat", json={"message": "python jobs", "thread_id": "../../etc"})
    assert r.status_code == 422


# ---------- company research ----------

def test_company_research_by_name(auth_client, sources, no_external_tools):
    wiki, _ = no_external_tools
    wiki.pages["infosys"] = {"title": "Infosys", "description": "Indian multinational IT company",
                             "extract": "Infosys Limited is an Indian multinational IT company. Founded in 1981.",
                             "url": "https://en.wikipedia.org/wiki/Infosys"}
    sources[0]._jobs = [job(10, company="Infosys Limited", salary_min_lpa=4, salary_max_lpa=6),
                        job(11, company="Infosys Ltd", location="Pune, Maharashtra",
                            salary_min_lpa=6, salary_max_lpa=8),
                        job(12, company="Infosys", salary_min_lpa=5, salary_max_lpa=7),
                        job(13, company="Wipro")]
    sources[1]._jobs = []
    data = chat(auth_client, "tell me about Infosys")
    c = data["company"]
    assert data["intent"] == "company_research"
    assert c["wiki"]["title"] == "Infosys" and c["open_roles"] == 3          # Wipro excluded
    assert c["disclosed_salary"]["n"] == 3 and c["disclosed_salary"]["median"] == 6.0
    assert "Glassdoor" in data["reply"]                                      # honest about missing reviews


def test_company_research_from_earlier_result(auth_client, sources):
    sources[0]._jobs = [job(1, company="Acme Analytics"), job(2, company="Zoho Corporation")]
    sources[1]._jobs = []
    t = chat(auth_client, "python developer jobs")["thread_id"]
    data = chat(auth_client, "tell me about the second company", t)
    assert data["intent"] == "company_research" and data["company"]["name"] == "Zoho Corporation"
    assert "couldn't find a reliable public overview" in data["reply"]       # no wiki page: says so


def test_company_research_survives_job_sources_down(auth_client, sources):
    for s in sources:
        s.fail = True
    data = chat(auth_client, "tell me about Infosys")
    assert data["company"]["open_roles"] is None and "unavailable" in data["reply"]


# ---------- salary research ----------

def test_salary_research_combines_listings_and_market(auth_client, sources, no_external_tools):
    _, salary = no_external_tools
    salary.hist.update({200000: 10, 400000: 30, 600000: 40, 800000: 20})
    sources[0]._jobs = [job(i, salary_min_lpa=lo, salary_max_lpa=hi) for i, (lo, hi) in
                        enumerate([(4, 6), (5, 7), (6, 8), (8, 10)])]
    data = chat(auth_client, "average salary of python developer in Bangalore")
    s = data["salary"]
    assert data["intent"] == "salary_research"
    assert s["listings"]["n"] == 4 and s["market"]["median"] == 6.5
    assert "n=4" in data["reply"] and "includes estimated" in data["reply"]


def test_salary_research_refuses_to_guess_without_data(auth_client, sources):
    sources[0]._jobs, sources[1]._jobs = [job(1, salary_min_lpa=5)], []
    data = chat(auth_client, "how much does a python developer earn")
    assert data["salary"]["listings"] is None and "Not enough salary data" in data["reply"]


# ---------- profile goals ----------

def test_target_role_drives_generic_search(auth_client, sources):
    auth_client.put("/me/profile", json={"target_roles": ["Python Developer", "python developer"],
                                         "career_goal": "Backend engineer at a product company"})
    p = auth_client.get("/me/profile").json()
    assert p["target_roles"] == ["Python Developer"] and p["career_goal"].startswith("Backend")
    data = chat(auth_client, "show me jobs")
    assert data["intent"] == "job_search" and data["params"]["keywords"] == "Python Developer"


# ---------- job alerts ----------

ALERT = {"name": "Python BLR", "params": {"keywords": "python developer", "city": "Bengaluru"}, "frequency": "daily"}


def test_alert_crud_and_limit(auth_client, sources):
    r = auth_client.post("/alerts", json=ALERT)
    assert r.status_code == 201 and r.json()["active"] is True
    aid = r.json()["id"]
    assert auth_client.patch(f"/alerts/{aid}", json={"active": False}).json()["active"] is False
    for i in range(4):
        assert auth_client.post("/alerts", json={**ALERT, "name": f"a{i}"}).status_code == 201
    r = auth_client.post("/alerts", json={**ALERT, "name": "one too many"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "alert_limit"
    assert auth_client.delete(f"/alerts/{aid}").status_code == 204
    assert len(auth_client.get("/alerts").json()) == 4


def test_alert_needs_a_role(auth_client):
    r = auth_client.post("/alerts", json={**ALERT, "params": {"keywords": " "}})
    assert r.status_code == 422


def test_alerts_are_private(client, auth_client):
    aid = auth_client.post("/alerts", json=ALERT).json()["id"]
    other = client.post("/auth/register", json={"email": "o@example.com", "password": "password123"})
    h = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert client.delete(f"/alerts/{aid}", headers=h).status_code == 404


def test_alert_only_reports_new_jobs(auth_client, sources):
    aid = auth_client.post("/alerts", json=ALERT).json()["id"]
    preview = auth_client.post(f"/alerts/{aid}/preview").json()
    assert preview["new"] == preview["total"] > 0

    with SessionLocal() as db:
        alert = db.get(JobAlert, aid)
        first, _ = run_alert(db, alert)
        assert len(first) == preview["new"]
        again, total = run_alert(db, alert)
        assert again == [] and total == preview["total"]                     # nothing new the second time

    from app.cache import get_cache
    get_cache.cache_clear()                                                  # simulate the next day's search
    sources[0]._jobs.append(job(99, title="Python Developer New"))
    with SessionLocal() as db:
        fresh, _ = run_alert(db, db.get(JobAlert, aid))
        assert [j.id for j in fresh] == ["fake:99"]


def test_due_alerts_respects_frequency(auth_client):
    a = auth_client.post("/alerts", json=ALERT).json()["id"]
    b = auth_client.post("/alerts", json={**ALERT, "name": "weekly", "frequency": "weekly"}).json()["id"]
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        assert {x.id for x in due_alerts(db, now)} == {a, b}                # never run yet
        for alert_id in (a, b):
            db.get(JobAlert, alert_id).last_run_at = now - timedelta(days=2)
        db.commit()
        assert {x.id for x in due_alerts(db, now)} == {a}                   # weekly one isn't due yet


def test_account_deletion_removes_threads_and_alerts(auth_client, sources):
    chat(auth_client, "python developer jobs")
    auth_client.post("/alerts", json=ALERT)
    assert auth_client.delete("/auth/me").status_code == 204
    with SessionLocal() as db:
        assert db.query(JobAlert).count() == 0
