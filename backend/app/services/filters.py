"""Filtering and ranking. Policy: a job with UNKNOWN salary/experience is kept (Indian listings often omit
them) but ranked below jobs that are KNOWN to match. A job KNOWN to violate a filter is removed."""
from app.domain import JobListing, SearchParams
from app.sources.normalize import canonical_city


def _city_ok(job: JobListing, city: str | None) -> bool:
    if not city:
        return True
    c = canonical_city(city)
    loc = job.location.lower()
    return c in loc or city.lower() in loc or (job.work_mode == "remote")


def apply_filters(jobs: list[JobListing], p: SearchParams) -> list[JobListing]:
    kept: list[tuple[int, int, JobListing]] = []
    for i, j in enumerate(jobs):
        if not _city_ok(j, p.city):
            continue
        known = 0
        if p.max_experience_years is not None and j.experience_min_years is not None:
            # allow a 1-year stretch: "2-4 years" roles are realistic for someone with 1.5
            if j.experience_min_years > p.max_experience_years + 1:
                continue
            known += 1
        if p.min_salary_lpa is not None and (j.salary_max_lpa or j.salary_min_lpa) is not None:
            if (j.salary_max_lpa or j.salary_min_lpa) < p.min_salary_lpa:
                continue
            known += 1
        if p.work_mode is not None and j.work_mode is not None:
            if j.work_mode != p.work_mode:
                continue
            known += 1
        if p.notice_period_days is not None and j.notice_period_days is not None:
            if j.notice_period_days < p.notice_period_days:
                continue
            known += 1
        kept.append((-known, i, j))  # more confirmed matches first, then original (relevance) order
    return [j for _, _, j in sorted(kept)]
