import os
import tempfile

# Must be set before the app is imported: tests use SQLite + in-memory cache + no LLM, no network.
_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ.update({
    # CI also runs the suite against a real Postgres via TEST_DATABASE_URL.
    "DATABASE_URL": os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_db.name}",
    "REDIS_URL": "", "GOOGLE_API_KEY": "", "SENTRY_DSN": "",
    "ADZUNA_APP_ID": "", "ADZUNA_APP_KEY": "", "RAPIDAPI_KEY": "", "RATE_LIMIT_PER_MINUTE": "1000",
    "JWT_SECRET": "test-secret", "ADMIN_EMAILS": "admin@example.com",
    "AUTO_MIGRATE": "false", "WIKIPEDIA_ENABLED": "false",  # tests build tables from models; no network
    "SMTP_HOST": "", "EMAIL_FROM": "", "CRON_TOKEN": "",     # email off unless a test turns it on
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.cache import get_cache  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.domain import JobListing, SearchParams  # noqa: E402
from app.main import app  # noqa: E402
from app.sources.aggregator import Aggregator  # noqa: E402
from app.sources.base import JobSource, SourceError  # noqa: E402


def job(i, **kw) -> JobListing:
    base = dict(id=f"fake:{i}", title=f"Python Developer {i}", company=f"Co{i}", location="Bengaluru, Karnataka",
                url=f"https://example.com/{i}", source="fake")
    base.update(kw)
    return JobListing(**base)


class FakeSource(JobSource):
    def __init__(self, name, jobs=None, fail=False):
        super().__init__()
        self.name, self._jobs, self.fail, self.calls = name, jobs or [], fail, 0

    def is_configured(self):
        return True

    def _request(self, params):  # not used
        raise NotImplementedError

    def _parse(self, payload):
        raise NotImplementedError

    def search(self, params: SearchParams):
        self.calls += 1
        if self.fail:
            raise SourceError(f"{self.name}: down")
        return list(self._jobs)


@pytest.fixture(autouse=True)
def clean_state():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    get_cache.cache_clear()
    yield


class FakeWiki:
    def __init__(self, pages=None):
        self.pages = pages or {}

    def lookup(self, name):
        from app.domain import CompanyWiki

        page = self.pages.get(name.lower())
        return CompanyWiki(**page) if page else None


class FakeSalary:
    def __init__(self, hist=None):
        self.hist = hist or {}

    def histogram(self, role, city=None):
        return self.hist


@pytest.fixture(autouse=True)
def no_external_tools(monkeypatch):
    """Company/salary tools must never hit the network in tests. Tests override these when needed."""
    wiki, salary = FakeWiki(), FakeSalary()
    monkeypatch.setattr("app.services.company_research.get_wiki_client", lambda: wiki)
    monkeypatch.setattr("app.services.salary_research.get_salary_client", lambda: salary)
    return wiki, salary


@pytest.fixture
def sources(monkeypatch):
    """Replace real job APIs with fakes. Returns the list so tests can tweak them."""
    srcs = [FakeSource("primary", [job(1), job(2, location="Pune, Maharashtra", salary_max_lpa=5),
                                   job(3, salary_min_lpa=10, salary_max_lpa=14, work_mode="remote")]),
            FakeSource("secondary", [job(1), job(4, experience_min_years=6)])]
    agg = Aggregator(srcs)
    for mod in ("app.services.search_service", "app.routers.health"):
        monkeypatch.setattr(f"{mod}.get_aggregator", lambda: agg)
    return srcs


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


FIXTURES = __import__("pathlib").Path(__file__).parent / "fixtures"


@pytest.fixture
def resume_pdf() -> bytes:
    return (FIXTURES / "sample_resume.pdf").read_bytes()


def register(client, email):
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def auth_client(client):
    r = client.post("/auth/register", json={"email": "user@example.com", "password": "password123"})
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return client
