import json
import logging
import time

from sqlalchemy.orm import Session

from app.cache import get_cache
from app.config import get_settings
from app.domain import JobListing, SearchOutcome, SearchParams
from app.errors import AllSourcesFailedError
from app.models import SearchLog
from app.monitoring import SEARCH_RESULTS, SEARCHES
from app.services.filters import apply_filters
from app.sources.aggregator import Aggregator, get_aggregator

log = logging.getLogger("app.search")
JOB_TTL_SECONDS = 86400


def get_job(job_id: str) -> JobListing | None:
    """A job seen in a search within the last day, with its full description; None if expired/unknown."""
    cached = get_cache().get(f"job:{job_id}")
    return JobListing(**json.loads(cached)) if cached else None


def run_search(params: SearchParams, aggregator: Aggregator | None = None) -> SearchOutcome:
    """Raw source results are cached by query only, then filters are applied, so changing a filter
    in the UI does not burn another API call."""
    aggregator = aggregator or get_aggregator()
    start = time.perf_counter()
    cache = get_cache()
    raw_key = SearchParams(keywords=params.keywords.lower(), city=params.city, page=params.page,
                           work_mode="remote" if params.work_mode == "remote" else None).cache_key()

    cached = cache.get(raw_key)
    if cached:
        data = json.loads(cached)
        jobs = [JobListing(**j) for j in data["jobs"]]
        ok, failed, hit = data["ok"], [], True
    else:
        jobs, ok, failed = aggregator.search(params)
        hit = False
        if not ok:
            reason = "no job source is configured" if not failed else "all job sources failed"
            raise AllSourcesFailedError(f"Job search is temporarily unavailable ({reason}). Try again in a minute.")
        cache.set(raw_key, json.dumps({"jobs": [j.model_dump() for j in jobs], "ok": ok}),
                  get_settings().search_cache_ttl_seconds)
        # remember each job by id for a day: resume matching / tracking / interview prep look it up later
        cache.set_many({f"job:{j.id}": j.model_dump_json() for j in jobs}, JOB_TTL_SECONDS)

    filtered = apply_filters(jobs, params)
    return SearchOutcome(params=params, jobs=filtered, total_before_filters=len(jobs), sources_ok=ok,
                         sources_failed=failed, cache_hit=hit,
                         latency_ms=round((time.perf_counter() - start) * 1000))


def record(db: Session, outcome: SearchOutcome, *, user_id: int | None, channel: str, query: str) -> None:
    SEARCHES.labels(channel, "hit" if outcome.cache_hit else "miss").inc()
    SEARCH_RESULTS.observe(len(outcome.jobs))
    try:
        db.add(SearchLog(user_id=user_id, channel=channel, query=query[:500],
                         filters=outcome.params.model_dump(exclude_none=True), result_count=len(outcome.jobs),
                         latency_ms=outcome.latency_ms, sources_ok=outcome.sources_ok,
                         sources_failed=outcome.sources_failed, cache_hit=outcome.cache_hit))
        db.commit()
    except Exception:  # analytics must never break a search
        db.rollback()
        log.exception("failed to write search log")
