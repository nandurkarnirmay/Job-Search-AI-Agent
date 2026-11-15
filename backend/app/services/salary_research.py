"""Salary research tool. Numbers are computed here and never pass through the LLM."""
import json
import logging
from functools import lru_cache

from app.cache import get_cache
from app.domain import BandStats, JobListing, SalaryReport, SearchParams
from app.errors import AllSourcesFailedError
from app.services.filters import apply_filters
from app.services.salary_stats import describe, job_salary_midpoint, stats_from_histogram, stats_from_values
from app.services.search_service import run_search
from app.sources.adzuna_salary import AdzunaSalaryClient
from app.sources.base import SourceError

log = logging.getLogger("app.salary")
HISTOGRAM_TTL = 6 * 3600


@lru_cache
def get_salary_client() -> AdzunaSalaryClient:
    return AdzunaSalaryClient()


def _histogram(role: str, city: str | None) -> dict[float, int]:
    key = f"salaryhist:{role.lower()}|{(city or '').lower()}"
    cache = get_cache()
    if cached := cache.get(key):
        return {float(k): v for k, v in json.loads(cached).items()}
    hist = get_salary_client().histogram(role, city)
    if hist:
        cache.set(key, json.dumps(hist), HISTOGRAM_TTL)
    return hist


BANDS = [(0, 1, "0-1", "0–1 yrs (fresher)"), (1, 3, "1-3", "1–3 yrs"), (3, 6, "3-6", "3–6 yrs"),
         (6, 10, "6-10", "6–10 yrs"), (10, 99, "10+", "10+ yrs")]


def band_for(years: float) -> str:
    return next(code for lo, hi, code, _ in BANDS if lo <= years < hi)


def experience_bands(jobs: list[JobListing]) -> list[BandStats]:
    """Salary distribution per required-experience band ('2-4 years' counts in the 1–3 band by its minimum).
    Jobs that don't state experience or salary are left out; bands with < 3 salaries get no stats."""
    values: dict[str, list[float]] = {code: [] for *_, code, _ in BANDS}
    for j in jobs:
        v = job_salary_midpoint(j)
        if v is not None and j.experience_min_years is not None:
            values[band_for(j.experience_min_years)].append(v)
    return [BandStats(band=code, label=label, stats=stats_from_values(values[code]), n=len(values[code]))
            for _, _, code, label in BANDS]


def research_salary(params: SearchParams) -> SalaryReport:
    role, city = params.keywords, params.city
    report = SalaryReport(role=role, city=city, experience_years=params.max_experience_years)

    try:
        everyone = run_search(SearchParams(keywords=role, city=city)).jobs
        report.bands = experience_bands(everyone)
        jobs = apply_filters(everyone, SearchParams(keywords=role, max_experience_years=params.max_experience_years))
        values = [v for j in jobs if (v := job_salary_midpoint(j)) is not None]
        report.listings = stats_from_values(values)
        if values and report.listings is None:
            report.notes.append(f"Only {len(values)} current listing(s) disclose a salary: too few for a range.")
    except AllSourcesFailedError:
        report.notes.append("Job listings are unavailable right now, so advertised salaries are missing.")

    try:
        report.market = stats_from_histogram(_histogram(role, city))
    except SourceError:
        report.notes.append("The salary-market source is unavailable right now.")
    return report


def salary_reply(r: SalaryReport) -> str:
    where = f" in {r.city}" if r.city else " across India"
    exp = "" if r.experience_years is None else (
        " for freshers" if r.experience_years == 0 else f" for ~{r.experience_years:g} yrs experience")
    lines = [f"Salary for {r.role}{where}{exp}:"]
    if r.listings:
        lines.append(f"• Advertised in current listings (n={r.listings.n}): {describe(r.listings)}.")
    with_stats = [b for b in r.bands if b.stats]
    if with_stats:
        lines.append("• By required experience: " + "; ".join(
            f"{b.label}: median ₹{b.stats.median:g} LPA (n={b.stats.n})" for b in with_stats))
    if r.market:
        lines.append(f"• Market estimate from Adzuna (n={r.market.n}, includes estimated salaries): "
                     f"{describe(r.market)}.")
    if not r.listings and not r.market:
        lines.append("Not enough salary data to give a reliable figure. Try a broader role name or another city.")
    lines += r.notes
    if r.experience_years is None and (r.listings or r.market):
        lines.append("Add your experience (e.g. 'with 2 years') to narrow the range.")
    return "\n".join(lines)
