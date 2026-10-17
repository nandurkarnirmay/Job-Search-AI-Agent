"""Adzuna jobs API, India endpoint. Free keys: https://developer.adzuna.com/"""
import httpx

from app.config import get_settings
from app.domain import JobListing, SearchParams
from app.sources import normalize as nz
from app.sources.base import JobSource

URL = "https://api.adzuna.com/v1/api/jobs/in/search/{page}"


class AdzunaSource(JobSource):
    name = "adzuna"

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.adzuna_app_id and s.adzuna_app_key)

    def _request(self, params: SearchParams) -> httpx.Request:
        s = get_settings()
        q = {"app_id": s.adzuna_app_id, "app_key": s.adzuna_app_key, "results_per_page": 50,
             "what": params.keywords or "jobs"}
        if params.city:
            q["where"] = params.city
        return self._client.build_request("GET", URL.format(page=params.page), params=q,
                                          headers={"Accept": "application/json"})

    def _parse(self, payload: dict) -> list[JobListing]:
        jobs = []
        for r in payload.get("results", []):
            text = f"{r.get('title', '')} {r.get('description', '')}"
            # Adzuna fills in *estimated* salaries when the ad has none; showing them as real would mislead.
            predicted = str(r.get("salary_is_predicted", "0")) == "1"
            smin = None if predicted else nz.rupees_to_lpa(r.get("salary_min"))
            smax = None if predicted else nz.rupees_to_lpa(r.get("salary_max"))
            if smin is None:
                smin, smax = nz.salary_lpa_from_text(text)
            emin, emax = nz.experience_from_text(text)
            jobs.append(JobListing(
                id=f"adzuna:{r.get('id')}",
                title=r.get("title", "").strip(),
                company=(r.get("company") or {}).get("display_name", "Unknown"),
                location=(r.get("location") or {}).get("display_name", "India"),
                url=r.get("redirect_url", ""),
                source=self.name,
                description=r.get("description", ""),
                salary_min_lpa=smin, salary_max_lpa=smax,
                experience_min_years=emin, experience_max_years=emax,
                work_mode=nz.work_mode_from_text(text),
                notice_period_days=nz.notice_period_from_text(text),
                posted_at=r.get("created"),
            ))
        return jobs
