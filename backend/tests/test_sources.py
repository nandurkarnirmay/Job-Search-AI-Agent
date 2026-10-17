import httpx
import pytest

from app.config import get_settings
from app.domain import SearchParams
from app.sources import base
from app.sources.adzuna import AdzunaSource
from app.sources.base import SourceError
from app.sources.jsearch import JSearchSource


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(base.time, "sleep", lambda s: None)
    s = get_settings()
    monkeypatch.setattr(s, "adzuna_app_id", "id")
    monkeypatch.setattr(s, "adzuna_app_key", "key")
    monkeypatch.setattr(s, "rapidapi_key", "key")


def adzuna_with(handler):
    return AdzunaSource(client=httpx.Client(transport=httpx.MockTransport(handler)))


ADZUNA_OK = {"results": [
    {"id": 1, "title": "Python Developer", "company": {"display_name": "Acme"},
     "location": {"display_name": "Bangalore, Karnataka"}, "redirect_url": "https://x/1",
     "description": "2-4 years experience. Hybrid. Immediate joiners.", "salary_min": 800000, "salary_max": 1200000},
    {"id": 2, "title": "Data Analyst", "company": {"display_name": "Beta"}, "location": {"display_name": "Pune"},
     "redirect_url": "https://x/2", "description": "Freshers", "salary_min": 300000, "salary_is_predicted": "1"},
]}


def test_adzuna_parses_indian_fields():
    src = adzuna_with(lambda req: httpx.Response(200, json=ADZUNA_OK))
    jobs = src.search(SearchParams(keywords="python", city="Bengaluru"))
    a, b = jobs
    assert (a.salary_min_lpa, a.salary_max_lpa) == (8.0, 12.0)
    assert (a.experience_min_years, a.work_mode, a.notice_period_days) == (2.0, "hybrid", 0)
    assert b.salary_min_lpa is None            # Adzuna's predicted salary is not shown as real
    assert b.experience_min_years == 0.0


def test_retries_then_succeeds():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] < 3 else httpx.Response(200, json=ADZUNA_OK)

    assert len(adzuna_with(handler).search(SearchParams(keywords="python"))) == 2
    assert calls["n"] == 3


def test_bad_keys_not_retried():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(401)

    with pytest.raises(SourceError):
        adzuna_with(handler).search(SearchParams(keywords="python"))
    assert calls["n"] == 1


def test_circuit_opens_after_repeated_failures():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        raise httpx.ConnectTimeout("timeout")

    src = adzuna_with(handler)
    src.min_interval_seconds = 0
    for _ in range(3):
        with pytest.raises(SourceError):
            src.search(SearchParams(keywords="python"))
    before = calls["n"]
    with pytest.raises(SourceError, match="temporarily disabled"):
        src.search(SearchParams(keywords="python"))
    assert calls["n"] == before                # no network call while the circuit is open


def test_jsearch_monthly_salary_and_remote():
    payload = {"data": [{"job_id": "j1", "job_title": "Backend Engineer", "employer_name": "Gamma",
                         "job_city": "Hyderabad", "job_state": "Telangana", "job_apply_link": "https://x",
                         "job_description": "Build APIs", "job_is_remote": True, "job_min_salary": 50000,
                         "job_max_salary": 80000, "job_salary_period": "MONTH",
                         "job_required_experience": {"required_experience_in_months": 24}}]}
    src = JSearchSource(client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))))
    j = src.search(SearchParams(keywords="backend"))[0]
    assert (j.salary_min_lpa, j.salary_max_lpa, j.work_mode, j.experience_min_years) == (6.0, 9.6, "remote", 2.0)


def test_unconfigured_source_raises(monkeypatch):
    monkeypatch.setattr(get_settings(), "rapidapi_key", "")
    with pytest.raises(SourceError, match="not configured"):
        JSearchSource().search(SearchParams(keywords="x"))
