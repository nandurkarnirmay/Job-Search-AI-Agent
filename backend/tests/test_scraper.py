from bs4 import BeautifulSoup

from app.domain import SearchParams
from app.sources.scraper import (
    IndianScraperSource,
    RateLimiter,
    get_curated_indian_listings,
)


def test_rate_limiter_throttles():
    limiter = RateLimiter(min_interval_seconds=0.05, jitter_range=(0.01, 0.02))
    assert limiter.total_requests == 0
    limiter.throttle()
    assert limiter.total_requests == 1
    wait = limiter.throttle()
    assert limiter.total_requests == 2
    assert wait >= 0.0


def test_curated_indian_listings_returns_valid_jobs():
    jobs = get_curated_indian_listings("python developer", "Bengaluru")
    assert len(jobs) > 0
    j = jobs[0]
    assert j.title
    assert j.company
    assert "Bengaluru" in j.location or j.work_mode == "remote"
    assert j.source == "naukri-indeed-scraper"
    assert j.salary_min_lpa is not None or j.salary_max_lpa is not None


def test_scraper_source_is_configured_and_searches():
    source = IndianScraperSource()
    assert source.is_configured() is True
    jobs = source.search(SearchParams(keywords="python", city="Bengaluru"))
    assert len(jobs) > 0
    assert any("Bengaluru" in j.location or j.work_mode == "remote" for j in jobs)


def test_bs4_parses_sample_indeed_html():
    sample_html = """
    <div class="job_seen_beacon">
        <h2 class="jobTitle"><span>Senior Python Engineer</span></h2>
        <span class="companyName">TechCorp India</span>
        <div class="companyLocation">Bengaluru, Karnataka</div>
        <div class="job-snippet">Building high throughput APIs. 3-5 years experience. Remote.</div>
        <div class="metadata salary-snippet-container">₹12,00,000 - ₹18,00,000 a year</div>
        <a class="jcs-JobTitle" href="/rc/clk?jk=123456">Apply</a>
    </div>
    """
    soup = BeautifulSoup(sample_html, "html.parser")
    card = soup.select_one(".job_seen_beacon")
    assert card is not None

    title = card.select_one("h2.jobTitle span").get_text(strip=True)
    company = card.select_one(".companyName").get_text(strip=True)
    loc = card.select_one(".companyLocation").get_text(strip=True)
    salary = card.select_one(".metadata.salary-snippet-container").get_text(strip=True)

    assert title == "Senior Python Engineer"
    assert company == "TechCorp India"
    assert loc == "Bengaluru, Karnataka"
    assert "12,00,000" in salary
