"""Adzuna salary histogram for a role/city in India: GET /v1/api/jobs/in/histogram?what=&where=
Response: {"histogram": {"<bucket lower bound, INR per year>": <count>, ...}}.
Adzuna mixes advertised and *estimated* salaries here, so the UI labels this 'market estimate'."""

from app.config import get_settings
from app.sources.base import ResilientAPI

URL = "https://api.adzuna.com/v1/api/jobs/in/histogram"


class AdzunaSalaryClient(ResilientAPI):
    name = "adzuna_histogram"

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.adzuna_app_id and s.adzuna_app_key)

    def histogram(self, role: str, city: str | None = None) -> dict[float, int]:
        """{bucket_lower_bound_inr: count}; empty dict when not configured or no data."""
        if not self.is_configured():
            return {}
        s = get_settings()
        q = {"app_id": s.adzuna_app_id, "app_key": s.adzuna_app_key, "what": role}
        if city:
            q["where"] = city

        def parse(p: dict) -> dict[float, int]:
            return {float(k): int(v) for k, v in (p.get("histogram") or {}).items() if int(v) > 0}

        return self._call(lambda: self._client.build_request("GET", URL, params=q,
                                                             headers={"Accept": "application/json"}), parse) or {}
