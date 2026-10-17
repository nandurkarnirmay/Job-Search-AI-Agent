"""Query every configured source in parallel, merge, de-duplicate. One source failing is not fatal."""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from app.domain import JobListing, SearchParams
from app.sources.adzuna import AdzunaSource
from app.sources.base import JobSource, SourceError
from app.sources.jsearch import JSearchSource
from app.sources.normalize import dedupe_key
from app.sources.scraper import IndianScraperSource


class Aggregator:
    def __init__(self, sources: list[JobSource]):
        self.sources = sources

    def search(self, params: SearchParams) -> tuple[list[JobListing], list[str], list[str]]:
        active = [s for s in self.sources if s.is_configured()]
        ok, failed, merged = [], [], []
        if not active:
            return [], ok, failed
        with ThreadPoolExecutor(max_workers=len(active)) as pool:
            futures = {s.name: pool.submit(s.search, params) for s in active}
            for name, fut in futures.items():
                try:
                    merged.extend(fut.result())
                    ok.append(name)
                except SourceError:
                    failed.append(name)
        seen, unique = set(), []
        for job in merged:
            k = dedupe_key(job.title, job.company, job.location)
            if k not in seen:
                seen.add(k)
                unique.append(job)
        return unique, ok, failed


@lru_cache
def get_aggregator() -> Aggregator:
    return Aggregator([AdzunaSource(), JSearchSource(), IndianScraperSource()])
