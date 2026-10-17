"""JSearch on RapidAPI (aggregates Google for Jobs: LinkedIn, Indeed, Naukri listings and more).
Key: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch"""
import httpx

from app.config import get_settings
from app.domain import JobListing, SearchParams
from app.sources import normalize as nz
from app.sources.base import JobSource

URL = "https://jsearch.p.rapidapi.com/search"
HOST = "jsearch.p.rapidapi.com"


class JSearchSource(JobSource):
    name = "jsearch"
    timeout_seconds = 20.0  # JSearch is slower than Adzuna

    def is_configured(self) -> bool:
        return bool(get_settings().rapidapi_key)

    def _request(self, params: SearchParams) -> httpx.Request:
        where = f"{params.city}, India" if params.city else "India"
        query = f"{params.keywords or 'jobs'} in {where}"
        q = {"query": query, "page": params.page, "num_pages": 1, "country": "in", "date_posted": "month"}
        if params.work_mode == "remote":
            q["work_from_home"] = "true"
        headers = {"X-RapidAPI-Key": get_settings().rapidapi_key, "X-RapidAPI-Host": HOST}
        return self._client.build_request("GET", URL, params=q, headers=headers)

    def _parse(self, payload: dict) -> list[JobListing]:
        jobs = []
        for r in payload.get("data") or []:
            text = f"{r.get('job_title', '')} {r.get('job_description', '')}"
            currency = r.get("job_salary_currency")
            period = {"YEAR": "year", "MONTH": "month"}.get((r.get("job_salary_period") or "").upper())
            smin = smax = None
            if currency in (None, "INR") and period:
                smin = nz.rupees_to_lpa(r.get("job_min_salary"), period)
                smax = nz.rupees_to_lpa(r.get("job_max_salary"), period)
            if smin is None and smax is None:
                smin, smax = nz.salary_lpa_from_text(text)

            months = (r.get("job_required_experience") or {}).get("required_experience_in_months")
            if months is not None:
                emin, emax = round(months / 12, 1), None
            else:
                emin, emax = nz.experience_from_text(text)

            location = ", ".join(p for p in (r.get("job_city"), r.get("job_state")) if p) or "India"
            jobs.append(JobListing(
                id=f"jsearch:{r.get('job_id')}",
                title=(r.get("job_title") or "").strip(),
                company=r.get("employer_name") or "Unknown",
                location=location,
                url=r.get("job_apply_link") or r.get("job_google_link") or "",
                source=self.name,
                description=(r.get("job_description") or "")[:2000],
                salary_min_lpa=smin, salary_max_lpa=smax,
                experience_min_years=emin, experience_max_years=emax,
                work_mode=nz.work_mode_from_text(text, r.get("job_is_remote")),
                notice_period_days=nz.notice_period_from_text(text),
                posted_at=r.get("job_posted_at_datetime_utc"),
            ))
        return jobs
