"""Tiered multi-source search.

Tier 1 (primary): Adzuna + JSearch, queried in parallel on every search.
Tier 2 (fallback): Jooble, queried only when tier 1 fails or returns fewer than FALLBACK_MIN_RESULTS jobs.
It has a 100-requests/day quota, so spending it only when needed keeps it available when it matters.
(Tier 3, stale cache, lives in search_service: last good results when every source is down.)

Results are merged and de-duplicated across sources; one source failing is never fatal."""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from app.config import get_settings
from app.domain import JobListing, SearchParams
from app.monitoring import SOURCE_CALLS
from app.sources.adzuna import AdzunaSource
from app.sources.base import JobSource, SourceError
from app.sources.jooble import JoobleSource
from app.sources.jsearch import JSearchSource
from app.sources.normalize import dedupe_key


def _run(sources: list[JobSource], params: SearchParams) -> tuple[list[JobListing], list[str], list[str]]:
    active = [s for s in sources if s.is_configured()]
    ok: list[str] = []
    failed: list[str] = []
    merged: list[JobListing] = []
    if not active:
        return merged, ok, failed
    with ThreadPoolExecutor(max_workers=len(active)) as pool:
        futures = {s.name: pool.submit(s.search, params) for s in active}
        for name, fut in futures.items():
            try:
                merged.extend(fut.result())
                ok.append(name)
            except SourceError:
                failed.append(name)
    return merged, ok, failed


def dedupe(jobs: list[JobListing]) -> list[JobListing]:
    seen, unique = set(), []
    for job in jobs:
        k = dedupe_key(job.title, job.company, job.location)
        if k not in seen:
            seen.add(k)
            unique.append(job)
    return unique


class Aggregator:
    def __init__(self, sources: list[JobSource], fallback: list[JobSource] | None = None,
                 min_results: int | None = None):
        self.sources = sources
        self.fallback = fallback or []
        self.min_results = min_results

    @property
    def all_sources(self) -> list[JobSource]:
        return self.sources + self.fallback

    def search(self, params: SearchParams) -> tuple[list[JobListing], list[str], list[str]]:
        jobs, ok, failed = _run(self.sources, params)
        jobs = dedupe(jobs)
        threshold = self.min_results if self.min_results is not None else get_settings().fallback_min_results
        if self.fallback and (failed or not ok or len(jobs) < threshold):
            more, ok2, failed2 = _run(self.fallback, params)
            for name in ok2:
                SOURCE_CALLS.labels(name, "fallback_used").inc()
            jobs, ok, failed = dedupe(jobs + more), ok + ok2, failed + failed2
        return jobs, ok, failed


@lru_cache
def get_aggregator() -> Aggregator:
    return Aggregator([AdzunaSource(), JSearchSource()], fallback=[JoobleSource()])
