"""Week 5: tiered sources + stale fallback, GitHub analysis, salary bands, negotiation, career roadmaps."""
import httpx
import pytest

from tests.conftest import FakeSource, job

from app.cache import get_cache
from app.config import get_settings
from app.domain import SalaryStats, SearchParams
from app.services.negotiation import parse_offer_message, percentile_of
from app.services.search_service import run_search
from app.sources import base
from app.sources.aggregator import Aggregator
from app.sources.jooble import JoobleSource


# ---------- sources & fallbacks ----------

def test_jooble_parsing(monkeypatch):
    monkeypatch.setattr(base.time, "sleep", lambda s: None)
    monkeypatch.setattr(get_settings(), "jooble_api_key", "k")
    payload = {"totalCount": 1, "jobs": [{
        "id": 42, "title": "<b>Data Analyst</b>", "company": "Acme &amp; Co", "location": "Pune, Maharashtra",
        "snippet": "Need SQL &amp; Power BI. 1-3 years. Hybrid.", "salary": "₹25,000 - ₹35,000 a month",
        "link": "https://jooble.org/x", "type": "Full-time", "updated": "2026-11-10T00:00:00"}]}

    def handler(req: httpx.Request):
        assert req.method == "POST" and req.url.path.endswith("/k")
        return httpx.Response(200, json=payload)

    j = JoobleSource(client=httpx.Client(transport=httpx.MockTransport(handler))).search(SearchParams(keywords="da"))[0]
    assert (j.title, j.company, j.work_mode) == ("Data Analyst", "Acme & Co", "hybrid")
    assert (j.salary_min_lpa, j.salary_max_lpa, j.experience_min_years) == (3.0, 4.2, 1.0)


def test_fallback_tier_only_when_needed():
    primary = FakeSource("primary", [job(i) for i in range(12)])
    fallback = FakeSource("fallback", [job(100)])
    agg = Aggregator([primary], fallback=[fallback], min_results=10)
    _, ok, _ = agg.search(SearchParams(keywords="x"))
    assert ok == ["primary"] and fallback.calls == 0                 # enough results: quota saved

    primary._jobs = [job(1)]
    jobs, ok, _ = agg.search(SearchParams(keywords="x"))
    assert ok == ["primary", "fallback"] and len(jobs) == 2           # too few: fallback used

    primary.fail = True
    jobs, ok, failed = agg.search(SearchParams(keywords="x"))
    assert (ok, failed, len(jobs)) == (["fallback"], ["primary"], 1)  # primary down: fallback saves the search


def test_stale_results_when_every_source_is_down(sources, auth_client):
    p = SearchParams(keywords="python")
    assert run_search(p).stale is False
    raw_key = SearchParams(keywords="python", page=1).cache_key()
    get_cache().delete(raw_key)                                        # fresh cache expired
    for s in sources:
        s.fail = True
    out = run_search(p)
    assert out.stale is True and out.jobs and out.sources_ok == []
    r = auth_client.post("/chat", json={"message": "python developer jobs"})  # never cached under this key
    assert r.status_code == 200 and "unavailable" in r.json()["reply"]


# ---------- GitHub ----------

def _gh_user(fake_github):
    fake_github.users["asha-dev"] = {"login": "asha-dev", "html_url": "https://github.com/asha-dev", "bio": None,
                                     "public_repos": 2, "followers": 1, "created_at": "2024-01-01T00:00:00Z"}
    fake_github.repo_lists["asha-dev"] = [
        {"name": "sales-dashboard", "html_url": "https://github.com/asha-dev/s", "language": "Jupyter Notebook",
         "stargazers_count": 2, "description": "Pandas + Power BI analysis", "pushed_at": "2026-10-01T00:00:00Z",
         "fork": False},
        {"name": "cpython", "html_url": "u", "language": "Python", "stargazers_count": 0, "description": "fork",
         "pushed_at": "2026-10-01T00:00:00Z", "fork": True}]


def test_github_analysis_and_profile_link(auth_client, fake_github):
    _gh_user(fake_github)
    r = auth_client.post("/github/analyse", json={"username": "@asha-dev"}).json()
    assert r["original_repos"] == 1 and {"Python", "Pandas", "Power BI"} <= set(r["skills"])   # fork excluded
    assert auth_client.get("/me/profile").json()["github_username"] == "asha-dev"
    data = auth_client.post("/chat", json={"message": "review my github"}).json()       # remembered username
    assert data["intent"] == "github_review" and data["extras"]["github"]["username"] == "asha-dev"


@pytest.mark.parametrize("username,status", [("-bad-", 422), ("nobody", 404)])
def test_github_errors(auth_client, username, status):
    assert auth_client.post("/github/analyse", json={"username": username}).status_code == status


def test_github_down(auth_client, fake_github):
    fake_github.down = True
    r = auth_client.post("/github/analyse", json={"username": "asha-dev"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "github_unavailable"


# ---------- salary & negotiation ----------

def _salary_jobs(sources):
    sources[0]._jobs = [job(i, salary_min_lpa=lo, salary_max_lpa=hi, experience_min_years=e) for i, (lo, hi, e) in
                        enumerate([(3, 4, 0), (3.5, 4.5, 0), (4, 5, 0.5), (5, 7, 1), (6, 8, 2), (6, 9, 2), (7, 9, 1.5),
                                   (9, 12, 3), (10, 14, 4), (12, 15, 5)])]
    sources[1]._jobs = []


def test_benchmark_by_experience_band(auth_client, sources):
    _salary_jobs(sources)
    r = auth_client.get("/salary/benchmark", params={"role": "data analyst"}).json()
    bands = {b["band"]: b for b in r["bands"]}
    assert bands["0-1"]["n"] == 3 and bands["1-3"]["stats"]["median"] == 7.2 and bands["6-10"]["stats"] is None


@pytest.mark.parametrize("offer,verdict,counter", [(6.5, "below market", 7.5), (7.5, "around market", 8.5),
                                                    (9, "above market", None)])
def test_negotiation_rules(auth_client, sources, offer, verdict, counter):
    _salary_jobs(sources)
    a = auth_client.post("/salary/negotiate", json={"role": "data analyst", "offer_lpa": offer,
                                                    "experience_years": 2}).json()
    assert (a["verdict"], a["counter_lpa"]) == (verdict, counter)
    assert a["benchmark_source"].startswith("current listings for 1–3")
    assert "Regards" in a["script"] and len(a["checklist"]) >= 5


def test_competing_offer_beats_cap_and_no_data_is_honest(auth_client, sources):
    _salary_jobs(sources)
    a = auth_client.post("/salary/negotiate", json={"role": "data analyst", "offer_lpa": 6, "experience_years": 2,
                                                    "competing_offer_lpa": 9}).json()
    assert a["counter_lpa"] == 9
    sources[0]._jobs = []  # different role below, so the cached "data analyst" results aren't reused
    b = auth_client.post("/salary/negotiate", json={"role": "data scientist", "offer_lpa": 6}).json()
    assert b["verdict"] == "no data" and b["counter_lpa"] is None
    assert not any("already strong" in p for p in b["talking_points"])


def test_percentile_and_offer_parsing():
    s = SalaryStats(n=10, p25=5, median=7, p75=9, min=3, max=13)
    assert [percentile_of(v, s) for v in (2, 5, 8, 13, 20)] == [0, 25, 62, 100, 100]
    assert parse_offer_message("offer of 8 LPA, current CTC 6 LPA, another offer of 9 LPA") == \
        {"offer_lpa": 8.0, "current_lpa": 6.0, "competing_lpa": 9.0}


def test_negotiation_via_chat(auth_client, sources):
    _salary_jobs(sources)
    data = auth_client.post("/chat", json={"message": "I got an offer of 6.5 LPA for data analyst with 2 years"}).json()
    assert data["intent"] == "salary_negotiation" and data["extras"]["negotiation"]["counter_lpa"] == 7.5


# ---------- career path ----------

def test_career_path_and_progress(auth_client, sources, resume_pdf):
    sources[0]._jobs = [job(i, description=d) for i, d in enumerate(
        ["SQL Excel Power BI", "SQL Tableau Python", "Excel SQL", "Python SQL statistics", "SQL Tableau", "Tableau"])]
    sources[1]._jobs = []
    assert auth_client.get("/career/path").status_code == 422                 # no role, no target role
    auth_client.post("/resume", files={"file": ("cv.pdf", resume_pdf, "application/pdf")})
    p = auth_client.get("/career/path", params={"role": "data analyst"}).json()
    planned = [s["skill"] for phase in p["phases"] for s in phase]
    assert p["family"] == "data_analyst" and "Tableau" in planned and "SQL" in p["have"]
    assert all(s["resources"] for phase in p["phases"] for s in phase if s["skill"] == "Tableau")
    done = auth_client.put("/career/progress", json={"skill": "Tableau", "status": "done"}).json()
    assert done == {"Tableau": "done"}
    p2 = auth_client.get("/career/path", params={"role": "data analyst"}).json()
    assert "Tableau" not in [s["skill"] for phase in p2["phases"] for s in phase]
    data = auth_client.post("/chat", json={"message": "roadmap to become a data analyst"}).json()
    assert data["intent"] == "career_path" and data["extras"]["career"]["family"] == "data_analyst"
