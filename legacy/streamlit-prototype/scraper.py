"""Track A: Simple Job Listing Scraper (Indeed / Naukri / Indian Job Sites with Rate Limiting).

Can be executed standalone:
    python scraper.py --keywords "python developer" --city "Bengaluru"
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
for p in (str(BACKEND), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.domain import SearchParams
from app.sources.scraper import (
    IndianScraperSource,
    RateLimiter,
    get_curated_indian_listings,
    rate_limiter,
    scrape_indeed_india,
)

__all__ = [
    "IndianScraperSource",
    "RateLimiter",
    "get_curated_indian_listings",
    "rate_limiter",
    "scrape_indeed_india",
    "search_jobs",
]


def search_jobs(keywords: str, city: str = "", limit: int = 10):
    source = IndianScraperSource()
    params = SearchParams(keywords=keywords, city=city or None)
    return source.search(params)[:limit]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Indian Job Listings with Rate Limiting")
    parser.add_argument("--keywords", default="python developer", help="Role or skills")
    parser.add_argument("--city", default="Bengaluru", help="Indian city (Bengaluru, Pune, Mumbai, etc.)")
    parser.add_argument("--limit", type=int, default=5, help="Number of results to display")
    args = parser.parse_args()

    print(f"[*] Scraping Indian job listings for '{args.keywords}' in '{args.city}' with rate limiting...")
    jobs = search_jobs(args.keywords, args.city, limit=args.limit)

    print(f"\n[+] Found {len(jobs)} openings:")
    for i, j in enumerate(jobs, 1):
        sal = f"₹{j.salary_min_lpa} - ₹{j.salary_max_lpa} LPA" if j.salary_min_lpa else "Not disclosed"
        exp = f"{j.experience_min_years} yrs" if j.experience_min_years is not None else "Any"
        mode = j.work_mode or "Not specified"
        print(f"\n{i}. {j.title}")
        print(f"   Company:    {j.company}")
        print(f"   Location:   {j.location} ({mode})")
        print(f"   Salary:     {sal}")
        print(f"   Experience: {exp}")
        print(f"   Source:     {j.source}")
        print(f"   Apply Link: {j.url}")
