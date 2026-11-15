"""GitHub REST API (public data only). Unauthenticated: 60 requests/hour per IP; with GITHUB_TOKEN 5,000/hour.
A profile analysis costs 2 requests (user + repos) and is cached for a day."""
from app.config import get_settings
from app.sources.base import ResilientAPI

API = "https://api.github.com"


class GitHubClient(ResilientAPI):
    name = "github"
    max_retries = 1
    min_interval_seconds = 0.2

    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
             "User-Agent": "JobSearchAIAgent"}
        if token := get_settings().github_token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def user(self, username: str) -> dict | None:
        return self._call(lambda: self._client.build_request("GET", f"{API}/users/{username}", headers=self._headers()),
                          lambda p: p if isinstance(p, dict) and p.get("login") else None, not_found_ok=True)

    def repos(self, username: str) -> list[dict]:
        params = {"per_page": 100, "sort": "pushed", "type": "owner"}
        return self._call(
            lambda: self._client.build_request("GET", f"{API}/users/{username}/repos", params=params,
                                               headers=self._headers()),
            lambda p: p if isinstance(p, list) else [], not_found_ok=True) or []
