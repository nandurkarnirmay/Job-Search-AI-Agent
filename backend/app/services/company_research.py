"""Company research tool: Wikipedia overview + live openings from our job sources + disclosed salaries.
Employee reviews/ratings are deliberately absent: Glassdoor and AmbitionBox offer no public API, and the
agent must not invent them."""
import json
import logging
import re
from collections import Counter
from functools import lru_cache

from app.agent.llm import get_llm
from app.cache import get_cache
from app.config import get_settings
from app.domain import CompanyReport, CompanyRole, SearchParams
from app.errors import AllSourcesFailedError
from app.monitoring import LLM_CALLS
from app.services.salary_stats import describe, job_salary_midpoint, stats_from_values
from app.services.search_service import run_search
from app.sources.base import SourceError
from app.sources.wikipedia import WikipediaClient, _initials

log = logging.getLogger("app.company")

REVIEWS_NOTE = ("Employee reviews and ratings aren't included: Glassdoor and AmbitionBox don't offer public APIs. "
                "Check them directly before an interview.")
_SUFFIXES = re.compile(r"\b(ltd|limited|pvt|private|inc|llp|llc|corp|corporation|co|company|technologies|technology|"
                       r"tech|solutions|services|software|systems|labs|group|india|global|consulting|plc)\b")


@lru_cache
def get_wiki_client() -> WikipediaClient:
    return WikipediaClient()


def company_key(name: str) -> str:
    s = re.sub(r"[^a-z0-9& ]+", " ", name.lower())
    return " ".join(_SUFFIXES.sub(" ", s).split())


def same_company(employer: str, names: list[str]) -> bool:
    """'Infosys Limited' ~ 'Infosys'; 'Tata Consultancy Services' ~ 'TCS' (via initials)."""
    e = company_key(employer)
    if not e:
        return False
    for n in names:
        k = company_key(n)
        if not k:
            continue
        if e == k or e.startswith(k + " ") or k.startswith(e + " "):
            return True
        compact = k.replace(" ", "")
        if len(compact) >= 2 and _initials(employer).startswith(compact):
            return True
    return False


def research_company(name: str) -> CompanyReport:
    cache = get_cache()
    key = f"company:{company_key(name) or name.lower()}"
    if cached := cache.get(key):
        return CompanyReport(**json.loads(cached))

    report = CompanyReport(name=name)
    try:
        report.wiki = get_wiki_client().lookup(name)
        if report.wiki:
            report.name = report.wiki.title
            report.sources.append("Wikipedia")
    except SourceError:
        report.notes.append("Wikipedia is unavailable right now, so there is no company overview.")

    degraded = False
    try:
        outcome = run_search(SearchParams(keywords=name))
        names = [name] + ([report.wiki.title] if report.wiki else [])
        jobs = [j for j in outcome.jobs if same_company(j.company, names)]
        report.open_roles = len(jobs)
        report.sample_roles = [CompanyRole(title=j.title, location=j.location, url=j.url) for j in jobs[:5]]
        report.top_cities = [c for c, _ in Counter(j.location.split(",")[0].strip() for j in jobs).most_common(4)]
        report.disclosed_salary = stats_from_values([v for j in jobs if (v := job_salary_midpoint(j)) is not None])
        report.sources += outcome.sources_ok
        degraded = bool(outcome.sources_failed)
    except AllSourcesFailedError:
        degraded = True
        report.notes.append("Job sources are unavailable right now, so current openings are missing.")

    report.notes.append(REVIEWS_NOTE)
    if not degraded and "Wikipedia is unavailable" not in " ".join(report.notes):
        cache.set(key, report.model_dump_json(), get_settings().company_cache_ttl_seconds)  # cache only full reports
    return report


OVERVIEW_PROMPT = """Write a 2-4 sentence overview of {name} for a job seeker in India.
Use ONLY the facts below. Do not add anything else: no ratings, reviews, culture, work-life balance, salaries,
headcount or numbers that are not in the facts. Plain text, no markdown.

FACTS:
{facts}"""

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _numbers_grounded(text: str, facts: str) -> bool:
    fact_nums = {n.replace(",", "") for n in _NUM.findall(facts)}
    return all(n.replace(",", "") in fact_nums for n in _NUM.findall(text))


def _first_sentences(text: str, k: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:k])


def overview(report: CompanyReport) -> tuple[str, str]:
    """(overview text, 'llm' | 'rules'). The LLM only rephrases Wikipedia; if it adds a number that isn't in
    the facts, the rephrasing is thrown away and the plain Wikipedia sentences are used."""
    if not report.wiki:
        return f"I couldn't find a reliable public overview of {report.name}.", "rules"
    plain = " ".join(x for x in [report.wiki.description and f"{report.name}: {report.wiki.description}.",
                                 _first_sentences(report.wiki.extract)] if x)
    llm = get_llm()
    if llm is None:
        return plain, "rules"
    facts = f"{report.wiki.description or ''}\n{report.wiki.extract}"
    try:
        text = llm.invoke(OVERVIEW_PROMPT.format(name=report.name, facts=facts)).content
        text = text if isinstance(text, str) else str(text)
        LLM_CALLS.labels("company_overview", "ok").inc()
        if text.strip() and len(text) < 1200 and _numbers_grounded(text, facts):
            return text.strip(), "llm"
        LLM_CALLS.labels("company_overview", "rejected").inc()
    except Exception as e:  # LLM down/quota: fall back silently
        LLM_CALLS.labels("company_overview", "error").inc()
        log.warning("company overview LLM failed: %s", e)
    return plain, "rules"


def company_reply(report: CompanyReport, overview_text: str) -> str:
    lines = [overview_text]
    if report.open_roles is not None:
        if report.open_roles:
            where = f", mostly in {', '.join(report.top_cities)}" if report.top_cities else ""
            lines.append(f"\nOpenings found in our job sources right now: {report.open_roles}{where}.")
            lines += [f"{i}. {r.title} ({r.location})" for i, r in enumerate(report.sample_roles, 1)]
        else:
            lines.append(f"\nNo current openings at {report.name} in our job sources.")
    if report.disclosed_salary:
        lines.append(f"Disclosed salaries in these openings (n={report.disclosed_salary.n}): "
                     f"{describe(report.disclosed_salary)}.")
    lines.append("")
    lines += report.notes
    return "\n".join(lines).strip()
