# Week 5: More data sources with fallbacks, salary by experience, negotiation, career roadmap, GitHub analysis

## What we did
**External APIs: now 6, with a 3-tier fallback.**
- **Sources:** Adzuna, JSearch, **Jooble (new)**, Wikipedia, **GitHub (new)** and Gemini.
- **Tier 1:** the primary job sources (Adzuna, JSearch) run in parallel.
- **Tier 2:** Jooble is called only when a primary fails or the primaries return fewer than 10 jobs. This saves its
  quota.
- **Tier 3:** if every source is down, the last good result (up to 24 h old) is served, labelled "may be out of
  date".
- Every client keeps the retries, backoff, throttle and circuit breaker from Week 2.
- We evaluated Remotive and rejected it: its terms forbid reusing listings in another job board.

**Salary benchmarking by experience.** Salary research now splits listings into bands (0–1, 1–3, 3–6, 6–10, 10+
years). Each band shows its percentiles and sample size. A new parser reads Indian salary formats like "₹25,000 a
month" and "6L–9L p.a.", and ignores phone numbers.

**Negotiation advisor.** "I got 7.5 LPA for data analyst in Pune, is it fair?"
- **Benchmark:** the offer's percentile within the matching experience band.
- **Verdict:** below, around or above market.
- **Counter-offer** from a written rule:
  - below the 25th percentile → counter at the median
  - below the median → counter midway to the 75th percentile
  - up to the 75th percentile → offer + 8 %
  - above the 75th percentile → no counter
- **Cap:** the counter is capped at +25 % unless the user has a higher competing offer.
- **Output:** talking points, an email script, and an Indian CTC checklist (fixed vs variable, joining bonus, notice
  buy-out, etc.).
- No number comes from the LLM.

**Career path roadmap.** For 12 role families (backend, frontend, data analyst/scientist/engineer, DevOps,
mechanical design, thermal/CAE, manufacturing, quality, finance, sales/marketing, software):
- the career ladder
- adjacent roles
- the skills needed, which are core skills plus skills that at least 20 % of current postings ask for, ranked by
  demand
- minus what the resume already shows
- packed into 6-week phases
- free or official resources (NPTEL for core engineering) and one project per skill

Users can mark skills as learning or done and the roadmap recalculates.

**GitHub profile analysis.** Public repos only, excluding forks and archived repos:
- languages, mapped to skills
- activity in the last 6 months, and stars
- README and description checks
- skills that GitHub shows but the resume doesn't, and resume skills with no public evidence

**Agent.** Three new intents (negotiation, career path, GitHub review), still rules-first. For example: "is 9 LPA a
good offer", "roadmap to become a data engineer", "review my github".

## Contributions
| Member | Work this week |
|---|---|
| Member 1 | Router intents and LangGraph nodes for negotiation, career and GitHub |
| Member 2 | Jooble source, fallback tiers, stale cache, Indian salary parser, salary bands |
| Member 3 | Career page (roadmap, salary, negotiate, GitHub tabs), chat cards |
| Member 4 | Negotiation rules, career data and roadmap builder, GitHub client, tests, migration 0004 |

## Challenges and decisions
- **Fallback cost.** Calling all three job sources on every search would exhaust free quotas. The fallback runs
  only when it's needed.
- **Negotiation must be explainable.** We chose fixed percentile rules over LLM advice, so the same offer always
  gets the same counter, and a mentor can check the reasoning.
- **Honest roadmaps.** Skills come from current postings, not from a static list. Resources are official or free.
  Core engineering gets NPTEL, not web-dev tutorials.

## Plan for next week
Voice mock interviews with follow-up questions, calendar integration, and an accuracy evaluation.
