"""Jooble job search API: fallback tier. Free key (https://jooble.org/api/about), 100 requests/day per key,
so the aggregator only calls it when the primary sources fail or return too few jobs.
POST {JOOBLE_API_URL}{key} with {"keywords", "location", "page", "ResultOnPage"}."""
import html
import re

import httpx

from app.config import get_settings
from app.domain import JobListing, SearchParams
from app.sources import normalize as nz
from app.sources.base import JobSource

_TAGS = re.compile(r"<[^>]+>")


def _clean(text: str | None) -> str:
    return html.unescape(_TAGS.sub(" ", text or "")).replace("\xa0", " ").strip()


class JoobleSource(JobSource):
    name = "jooble"
    max_retries = 1          # every retry spends daily quota
    min_interval_seconds = 1.0

    def is_configured(self) -> bool:
        return bool(get_settings().jooble_api_key)

    def _request(self, params: SearchParams) -> httpx.Request:
        s = get_settings()
        body = {"keywords": params.keywords or "jobs", "location": params.city or "India",
                "page": params.page, "ResultOnPage": 30}
        return self._client.build_request("POST", f"{s.jooble_api_url.rstrip('/')}/{s.jooble_api_key}", json=body,
                                          headers={"Content-Type": "application/json"})

    def _parse(self, payload: dict) -> list[JobListing]:
        jobs = []
        for r in payload.get("jobs") or []:
            title, snippet = _clean(r.get("title")), _clean(r.get("snippet"))
            text = f"{title} {snippet}"
            smin, smax = nz.salary_lpa_from_inr_text(r.get("salary") or "")
            if smin is None:
                smin, smax = nz.salary_lpa_from_text(text)
            emin, emax = nz.experience_from_text(text)
            jobs.append(JobListing(
                id=f"jooble:{r.get('id')}",
                title=title,
                company=_clean(r.get("company")) or "Unknown",
                location=_clean(r.get("location")) or "India",
                url=r.get("link") or "",
                source=self.name,
                description=snippet[:2000],
                salary_min_lpa=smin, salary_max_lpa=smax,
                experience_min_years=emin, experience_max_years=emax,
                work_mode=nz.work_mode_from_text(f"{text} {r.get('type') or ''}"),
                notice_period_days=nz.notice_period_from_text(text),
                posted_at=r.get("updated"),
            ))
        return jobs
