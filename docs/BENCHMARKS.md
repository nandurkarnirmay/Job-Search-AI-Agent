# Benchmarks: accuracy and speed

Reproduce: `cd backend && python -m scripts.eval_accuracy` (accuracy), `python -m scripts.bench_offline` (speed of
the deterministic code), `python -m scripts.benchmark --base <url>` (end-to-end latency of a deployment).
CI fails if router accuracy < 0.95 or skills F1 < 0.95.

## 1. Accuracy

### Intent router (64 labelled messages, 13 intents)
| Run | Accuracy | Notes |
|---|---|---|
| First run (Week 6) | **61/64 = 0.953** | 3 errors, in offers phrased as a question ("is this a fair offer…") and filter-only follow-ups ("anywhere in India is fine") |
| After fixes | **64/64 = 1.000** | fixed in the router rules, not by relabelling |

Per intent after fixes: every intent 100 % (job_search 10, refine_search 8, company_research 7, salary_research 5,
salary_negotiation 5, career_path 5, resume_review 4, interview_prep 4, help 4, resume_match 3,
track_application 3, applications_status 3, github_review 3).

### Skill extraction (25 snippets from resumes and job descriptions)
| Run | Precision | Recall | F1 |
|---|---|---|---|
| First run | 0.952 | 1.000 | 0.975 |
| After fixes (Spring vs Spring Boot, "5S", edge cases) | **0.988** | **1.000** | **0.994** |
The one remaining "error" is intended: "Power BI dashboards" also yields *Data Visualization*.

**Read these numbers with care.** The sets are small, written by us, and we fixed the bugs they exposed, so the
"after" numbers are training-set accuracy and overstate real-world performance. The "first run" numbers are the
honest estimate of accuracy on unseen phrasing. Week 8: a held-out set of 50 messages written by people outside the
team, scored once, without fixes.

### Deterministic outputs (correctness tests, not statistics)
| Feature | Checked by |
|---|---|
| Salary percentiles, bands | unit tests with known inputs |
| Negotiation counters | 4 scenarios: below / around / above market, competing offer |
| ATS score | fixed resume + job pairs |
| iCalendar | RFC 5545 escaping, 75-octet folding, alarms, all-day events |
| Interview scoring | reproducible per answer; follow-up triggers |

## 2. Speed

### Deterministic code (offline, one core, Python 3.13, measured Week 7)
| Operation | calls | p50 (ms) | p95 (ms) | max (ms) |
|---|---|---|---|---|
| router: route one message | 1280 | 0.094 | 0.230 | 1.302 |
| skills: one job-description snippet | 500 | 0.160 | 0.264 | 38.296* |
| skills: resume-sized text (1,856 words) | 20 | 11.5 | 14.8 | 15.1 |
| negotiation: parse offer message | 20 | 0.005 | 0.010 | 0.022 |
| calendar: build a 50-event .ics feed | 20 | 1.6 | 2.0 | 2.1 |
\* first call compiles the ~150 skill regexes once.

Conclusion: our own logic costs < 15 ms per request. End-to-end latency is dominated by the job APIs (cache miss)
and Gemini (only for messages the rules can't route), which is why rules-first routing and caching matter.

### End-to-end (deployment) — run before the final demo
`python -m scripts.benchmark --base https://<project>.vercel.app/api --runs 20` after a warm-up. Paste its table here:

| Endpoint | p50 (ms) | p95 (ms) | mean (ms) | errors |
|---|---|---|---|---|
| _to be measured_ | | | | |

Targets: cached search p95 < 500 ms, uncached search p95 < 4 s, chat (rules-routed) p95 < 4 s. Free-tier cold starts
(~1 min) are excluded and reported separately. Live numbers also appear on `/analytics/system` (p50/p95 from
`search_logs`, cache hit rate, per-source failure rate).
