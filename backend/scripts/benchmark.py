"""Latency benchmark against a running deployment (local or live). Creates a throwaway account, measures each
endpoint N times, prints a Markdown table for docs/BENCHMARKS.md, then deletes the account.

  python -m scripts.benchmark --base http://localhost:8000 --runs 20
  python -m scripts.benchmark --base https://<your-app>.vercel.app/api --runs 20

Note: the first search for each keyword is a cache MISS (calls the job APIs); repeats are cache HITS.
Run a warm-up request first on Render's free tier, or the first number will include a ~1 min cold start."""
import argparse
import statistics
import time
import uuid

import httpx

ROLES = ["data analyst", "java developer", "python developer", "mechanical design engineer", "devops engineer",
         "sales executive", "business analyst", "react developer", "quality engineer", "data scientist"]


def pct(values: list[float], q: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(q * len(s)))]


def timed(client: httpx.Client, method: str, url: str, **kw) -> tuple[float, int]:
    t = time.perf_counter()
    r = client.request(method, url, **kw)
    return (time.perf_counter() - t) * 1000, r.status_code


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--runs", type=int, default=20)
    a = ap.parse_args()
    base = a.base.rstrip("/")
    results: dict[str, list[float]] = {}
    errors: dict[str, int] = {}
    with httpx.Client(timeout=90) as c:
        c.get(f"{base}/health")  # warm-up (cold start on free hosting)
        email = f"bench-{uuid.uuid4().hex[:8]}@example.com"
        token = c.post(f"{base}/auth/register", json={"email": email, "password": "benchmark-pass-123"}) \
            .json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"

        def run(name: str, method: str, url: str, **kw):
            ms, status = timed(c, method, url, **kw)
            results.setdefault(name, []).append(ms)
            if status >= 400:
                errors[name] = errors.get(name, 0) + 1

        for i in range(a.runs):
            role = ROLES[i % len(ROLES)] + (f" {i // len(ROLES)}" if i >= len(ROLES) else "")
            run("GET /health", "GET", f"{base}/health")
            run("GET /jobs/search (cache miss)", "GET", f"{base}/jobs/search", params={"q": role})
            run("GET /jobs/search (cache hit)", "GET", f"{base}/jobs/search", params={"q": role, "min_salary_lpa": 5})
            run("POST /chat (job search)", "POST", f"{base}/chat", json={"message": f"{role} jobs in Bengaluru"})
            run("POST /chat (help, no tools)", "POST", f"{base}/chat", json={"message": "hi"})
            time.sleep(2.1)  # stay under the per-user rate limit (30/min by default)
        c.delete(f"{base}/auth/me")

    print(f"Base: {base} · runs per endpoint: {a.runs}\n")
    print("| Endpoint | p50 (ms) | p95 (ms) | mean (ms) | errors |")
    print("|---|---|---|---|---|")
    for name, vals in results.items():
        print(f"| {name} | {pct(vals, 0.5):.0f} | {pct(vals, 0.95):.0f} | {statistics.mean(vals):.0f} | "
              f"{errors.get(name, 0)} |")


if __name__ == "__main__":
    main()
