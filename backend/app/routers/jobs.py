from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import rate_limited
from app.domain import SearchParams
from app.models import User
from app.schemas import SearchOut
from app.services.search_service import record, run_search

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/search", response_model=SearchOut)
def search_jobs(
    q: str = Query(min_length=2, max_length=100, description="Role or skills"),
    city: str | None = Query(default=None, max_length=60),
    max_experience_years: float | None = Query(default=None, ge=0, le=50),
    min_salary_lpa: float | None = Query(default=None, ge=0, le=500),
    work_mode: Literal["remote", "hybrid", "onsite"] | None = None,
    notice_period_days: int | None = Query(default=None, ge=0, le=180),
    page: int = Query(default=1, ge=1, le=10),
    user: User = Depends(rate_limited),
    db: Session = Depends(get_db),
):
    params = SearchParams(keywords=q.strip(), city=city or None, max_experience_years=max_experience_years,
                          min_salary_lpa=min_salary_lpa, work_mode=work_mode,
                          notice_period_days=notice_period_days, page=page)
    outcome = run_search(params)
    record(db, outcome, user_id=user.id, channel="search", query=q)
    return SearchOut(params=outcome.params, jobs=outcome.jobs, count=len(outcome.jobs),
                     sources_ok=outcome.sources_ok, sources_failed=outcome.sources_failed,
                     cache_hit=outcome.cache_hit, latency_ms=outcome.latency_ms)
