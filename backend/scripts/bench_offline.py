"""Offline speed benchmark of the deterministic parts (no network, no DB): router, skill extraction, resume-sized
skill extraction, offer parsing, iCalendar generation. `python -m scripts.bench_offline`"""
import json
import statistics
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.agent.router import route
from app.services.calendar_ics import calendar, vevent
from app.services.negotiation import parse_offer_message
from app.services.skills import extract_skills

EVAL = Path(__file__).resolve().parent.parent / "eval"


def bench(name, fn, items, repeat=20):
    times = []
    for _ in range(repeat):
        for it in items:
            t = time.perf_counter()
            fn(it)
            times.append((time.perf_counter() - t) * 1000)
    times.sort()
    return name, len(items) * repeat, statistics.median(times), times[int(0.95 * len(times)) - 1], times[-1]


if __name__ == "__main__":
    msgs = [json.loads(line)["message"] for line in (EVAL / "router_eval.jsonl").open(encoding="utf-8")]
    texts = [json.loads(line)["text"] for line in (EVAL / "skills_eval.jsonl").open(encoding="utf-8")]
    resume = " ".join(texts * 8)  # ~ a 2-page resume
    now = datetime(2026, 11, 20, 10, tzinfo=timezone.utc)
    events = [vevent(f"e{i}", f"Interview {i}", now + timedelta(days=i), description="Round 1, bring ID")
              for i in range(50)]
    rows = [
        bench("router: route one message", lambda m: route(m), msgs),
        bench("skills: one job-description snippet", extract_skills, texts),
        bench(f"skills: resume-sized text ({len(resume.split())} words)", extract_skills, [resume]),
        bench("negotiation: parse offer message", parse_offer_message,
              ["got an offer of 7.5 LPA, current 5, competing 8.2"]),
        bench("calendar: build a 50-event .ics feed", lambda e: calendar(e, "Jobs"), [events]),
    ]
    print("| Operation | calls | p50 (ms) | p95 (ms) | max (ms) |\n|---|---|---|---|---|")
    for n, c, p50, p95, mx in rows:
        print(f"| {n} | {c} | {p50:.3f} | {p95:.3f} | {mx:.3f} |")
