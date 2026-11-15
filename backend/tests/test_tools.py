import httpx
import pytest

from app.config import get_settings
from app.domain import CompanyReport, CompanyWiki, JobListing
from app.services import company_research as cr
from app.services.salary_stats import job_salary_midpoint, stats_from_histogram, stats_from_values
from app.sources import base
from app.sources.adzuna_salary import AdzunaSalaryClient
from app.sources.base import SourceError
from app.sources.wikipedia import WikipediaClient, title_matches


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(base.time, "sleep", lambda s: None)


def test_stats_from_values_needs_enough_data_and_drops_junk():
    assert stats_from_values([5, 6]) is None
    s = stats_from_values([4, 5, 6, 7, 8, 0.1, 999])          # 0.1 and 999 LPA are parse errors
    assert (s.n, s.median, s.min, s.max) == (5, 6.0, 4.0, 8.0)


def test_histogram_percentiles():
    s = stats_from_histogram({200000: 10, 400000: 30, 600000: 40, 800000: 20})
    assert (s.n, s.p25, s.median, s.min, s.max) == (100, 5.0, 6.5, 2.0, 10.0)
    assert stats_from_histogram({500000: 3}) is None


def test_midpoint():
    j = JobListing(id="1", title="a", company="c", location="l", url="u", source="s",
                   salary_min_lpa=6, salary_max_lpa=10)
    assert job_salary_midpoint(j) == 8
    assert job_salary_midpoint(j.model_copy(update={"salary_min_lpa": None})) == 10


@pytest.mark.parametrize("company,title,ok", [
    ("TCS", "Tata Consultancy Services", True), ("L&T", "Larsen & Toubro", True), ("HCL", "HCLTech", True),
    ("Infosys", "Infosys", True), ("TCS", "Tata Steel", False), ("Ola", "Motorola", False),
])
def test_wikipedia_title_matching(company, title, ok):
    assert title_matches(company, title) is ok


@pytest.mark.parametrize("employer,names,ok", [
    ("Infosys Limited", ["Infosys"], True), ("Tata Consultancy Services", ["TCS"], True),
    ("Zoho Corporation Pvt Ltd", ["Zoho"], True), ("Wipro", ["Infosys"], False), ("Tata Steel", ["TCS"], False),
])
def test_same_company(employer, names, ok):
    assert cr.same_company(employer, names) is ok


def wiki_client(handler):
    return WikipediaClient(client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_wikipedia_lookup_skips_wrong_and_non_company_pages(monkeypatch, no_sleep):
    monkeypatch.setattr(get_settings(), "wikipedia_enabled", True)

    def handler(req: httpx.Request):
        if req.url.path.endswith("/w/api.php"):
            assert "User-Agent" in req.headers and "JobSearchAIAgent" in req.headers["User-Agent"]
            return httpx.Response(200, json={"query": {"search": [
                {"title": "Tata Steel"}, {"title": "Tata Consultancy Services (film)"},
                {"title": "Tata Consultancy Services"}]}})
        if "film" in req.url.path:
            return httpx.Response(200, json={"type": "standard", "title": "TCS (film)", "description": "2019 film",
                                             "extract": "A movie."})
        return httpx.Response(200, json={
            "type": "standard", "title": "Tata Consultancy Services",
            "description": "Indian multinational IT services company", "extract": "TCS is ...",
            "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Tata_Consultancy_Services"}}})

    wiki = wiki_client(handler).lookup("TCS")
    assert wiki.title == "Tata Consultancy Services" and wiki.url.endswith("Tata_Consultancy_Services")


def test_wikipedia_404_is_not_an_error(monkeypatch, no_sleep):
    monkeypatch.setattr(get_settings(), "wikipedia_enabled", True)

    def handler(req):
        if req.url.path.endswith("/w/api.php"):
            return httpx.Response(200, json={"query": {"search": [{"title": "Acme"}]}})
        return httpx.Response(404)

    client = wiki_client(handler)
    assert client.lookup("Acme") is None
    assert client.breaker.failures == 0


def test_parse_error_counts_as_source_failure(monkeypatch, no_sleep):
    s = get_settings()
    monkeypatch.setattr(s, "adzuna_app_id", "id")
    monkeypatch.setattr(s, "adzuna_app_key", "key")
    client = AdzunaSalaryClient(client=httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json={"histogram": {"abc": "x"}}))))
    with pytest.raises(SourceError):
        client.histogram("python")
    assert client.breaker.failures == 1


def test_overview_rejects_llm_numbers_not_in_facts(monkeypatch):
    class FakeLLM:
        def __init__(self, text):
            self.text = text

        def invoke(self, prompt):
            return type("R", (), {"content": self.text})()

    report = CompanyReport(name="Infosys", wiki=CompanyWiki(
        title="Infosys", description="Indian IT company", extract="Infosys was founded in 1981 in Pune."))
    monkeypatch.setattr(cr, "get_llm", lambda: FakeLLM("Infosys, founded in 1981, has 300,000 employees."))
    text, how = cr.overview(report)
    assert how == "rules" and "300,000" not in text          # invented headcount thrown away
    monkeypatch.setattr(cr, "get_llm", lambda: FakeLLM("Infosys is an Indian IT company founded in 1981."))
    assert cr.overview(report)[1] == "llm"
