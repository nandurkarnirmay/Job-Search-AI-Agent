# Architecture (Week 7)

```
Next.js (Vercel) ──HTTPS + JWT──► FastAPI (Render)
                                   ├─ /auth, /me/profile ─────────► PostgreSQL (Neon)
                                   ├─ /chat, /chat/threads ──► LangGraph agent        users, profiles,
                                   │                               (see below)         chat_threads, chat_messages,
                                   ├─ /jobs/search ──► Search service                 job_alerts, search_logs
                                   ├─ /alerts ───────► Alert service ─┐               (Alembic migrations)
                                   │                                   ▼
                                   │                   Search service ──► Redis cache (Upstash)
                                   │                        └─► Aggregator ─┬─► Adzuna (India)
                                   │                                         └─► JSearch (RapidAPI)
                                   │   Company tool ──► Wikipedia REST API
                                   │   Salary tool ───► Adzuna salary histogram
                                   └─ /health, /metrics, /stats
```

## Agent

```
                    ┌─ job_search ──────► parse_query ──► search ──► respond_jobs ─┐
                    ├─ refine_search ──────────────────► search                    │
                    ├─ company_research ──► company ───────────────────────────────┤
    START ─► route ─┼─ salary_research ───► salary ────────────────────────────────┤─► END
                    ├─ resume_review / resume_match ──► resume ────────────────────┤
                    ├─ interview_prep ────► interview ─────────────────────────────┤
                    ├─ track_application / applications_status ──► tracker ────────┤
                    └─ help ──────────────► help ──────────────────────────────────┘
```

Tools that touch the user's own data (resume, tracker, interview sessions) receive a `ToolContext`
(DB session + user) in the graph state; the other tools are stateless.

**Routing.** `app/agent/router.py` is pure rules: ordinal references ("the second company") → salary
questions → company questions → filter-only follow-ups → new search → help. It returns `confident=False` when
nothing matched; only then is Gemini asked to classify. The LLM's answer is accepted only if it is consistent
with the message: a `company_research` decision must name a company that appears in the text, `refine_search`
needs a previous search, `job_search`/`salary_research` need a role. Result: on typical traffic most messages
cost zero LLM calls, and the LLM cannot send the user to research a company they never mentioned.

**Memory.** Each conversation is a `chat_threads` row holding the last search parameters and the last 10
results (compact), plus `chat_messages` with the payload shown under each reply (so a reloaded conversation
renders the same cards). The graph receives this as input state; it doesn't need LangGraph checkpointers.

**Grounding rules.**
| Output | Source | LLM role |
|---|---|---|
| Job filters | message text (+ profile defaults) | parses; numbers kept only if the rule parser also finds them |
| Company overview | Wikipedia summary | may rephrase; rejected if it contains any number not in the source |
| Openings, salary stats | our job sources, Adzuna histogram | none: computed in code |
| Reviews / ratings | none available | never generated; the reply says so |

**Salary statistics.** Listing salaries: midpoint of each disclosed range, values outside 0.5–200 LPA dropped as
parse errors, percentiles by linear interpolation, minimum 3 values. Adzuna histogram: values assumed uniform
inside each bucket, minimum 10 values, labelled as including estimates.

## External APIs
All clients inherit `ResilientAPI` (`app/sources/base.py`): timeout, retries with backoff on 429/5xx/network
errors only, client-side throttle, circuit breaker (3 failures → skipped for 60 s), and a parse failure counts as a
source failure. Wikipedia 404s are "no page", not errors. Company reports are cached 6 h, salary histograms 6 h,
raw job results 15 min.

## Alerts
`job_alerts` stores the search, frequency and the dedupe keys of jobs already sent (capped at 500).
`run_alert()` returns only unseen jobs and records them; `due_alerts()` selects alerts whose interval has passed.
Week 4: Celery beat calls `due_alerts()` → `run_alert()` → email.

## Migrations
Alembic (`backend/alembic`). `AUTO_MIGRATE=true` applies them on startup. A database created by Week 2's
`create_all` (tables but no `alembic_version`) is stamped at `0001` first, then upgraded. Tests check that a fresh
migration produces exactly the models' columns, nullability and indexes, and that a Week 2 database is upgraded
without data loss.

## Week 4 tools

**Resume.** `resume_parser.py` validates by magic bytes (not extension), caps size (2 MB), pages (6) and DOCX
unpacked size (20 MB, zip-bomb guard), extracts text (pypdf; python-docx incl. tables), redacts emails/phones,
detects standard section headings and ~150 skills from `skills.py`. Skill matching handles symbols (C++, C#,
.NET, Node.js), avoids substring hits (Java≠JavaScript, SQL inside MySQL counted via implication), and skips
everyday words that look like skills (spark plugs, guard rails, "spring internship"). The file is discarded.

**ATS score** (`resume_analysis.py`), deterministic:
| Part | Points | Rule |
|---|---|---|
| Skills | 70 | required groups ×2, preferred ×1 ("nice to have / preferred / a plus" sentences); "A or B" and "A, B or C" are one group met by any member; a resume skill implies its parents (Spring Boot → Java) |
| Title | 15 | share of the job title's meaningful words (not senior/intern/…) found in the resume |
| Structure | 15 | experience 4, education 3, skills 4, projects 2, contact details 2 |
If the posting has no recognisable skills, the score is title+structure scaled to 100 and marked low-confidence.

**Interview** (`interview.py`, `interview_bank.py`). Question set = tell-me-about-yourself + why-this-company +
up to 5 technical questions round-robin over the role's skills + 2 behavioural + 1 India-specific HR question
(notice period / salary in LPA / relocation). Selection is seeded by role+company, so it's reproducible. Answer
score 1–5 = average of rule checks: technical key-point coverage (regex per point), STAR elements + measurable
impact for behavioural, concreteness for HR (days, LPA range + basis, company-specific reasons), length bands
per question type, plus tips ("we" vs "I", filler words). The LLM may add one coaching sentence, never the score.

**Tracker.** One row per (user, job dedupe key), so the same job from two sources is one entry. Saving by
`job_id` takes details from the server-side job cache, not the client. Status changes append to `history`.

**Alert delivery.** `dispatch_due_alerts()` is scheduler-agnostic: Celery beat calls it hourly where a worker
runs; GitHub Actions cron calls `POST /internal/alerts/dispatch` (shared-secret header) on free hosting.
A cache lock prevents double runs. Jobs are marked sent only after the email succeeds; if email is disabled
the digest is stored in `alert_runs` for in-app viewing. Emails escape all third-party text, only link http(s)
URLs, and carry a signed one-click unsubscribe link plus a `List-Unsubscribe` header.

**Job cache.** Every search result is cached by id for 24 h (one Redis pipeline round trip), so later
"match my resume to the second job" / "save it" / "prepare me for it" can use the full description.

## Weeks 5–7

### Services (Week 7)
One codebase, four deployable services selected by the `SERVICE` env var (`app/main.py`):

| Service | Routers | Migrates DB |
|---|---|---|
| `auth` | `/auth`, `/me/profile`, `/me/export` | no |
| `jobs` | `/jobs`, `/chat`, `/alerts`, `/applications`, `/calendar`, `/salary`, `/career`, `/github`, `/analytics`, `/stats`, `/internal` | **yes** (single owner of migrations) |
| `resume` | `/resume` | no |
| `interview` | `/interview` | no |
| `all` (default) | everything: the monolith, for local dev and the free-tier fallback | yes |

```
Browser ──► Next.js (Vercel)  /api/* rewrites = API gateway (same origin, no CORS)
              ├─ /api/auth/*, /api/me/*   ──► job-agent-auth
              ├─ /api/resume*             ──► job-agent-resume
              ├─ /api/interview/*         ──► job-agent-interview
              └─ /api/*                   ──► job-agent-jobs ──► Adzuna, JSearch, Jooble, Wikipedia, GitHub, Gemini
                                  all four ──► one Postgres (Neon) + one Redis (Upstash), shared JWT secret
```
Honest limits: the services share one database and are split by route ownership, not by data ownership. That
gives independent deploys, scaling and failure isolation (a crashing resume parser doesn't take search down),
but not independent schemas. The chat agent (in `jobs`) calls resume/interview code in-process rather than over
HTTP, so the resume and interview services are the API surface, not the agent's dependency. A full split
(per-service schemas, service-to-service auth) isn't justified at this scale.

### Job sources: three tiers (Week 5)
1. **Primary**: Adzuna (India) and JSearch, in parallel.
2. **Fallback**: Jooble, called only when a primary fails or together they return fewer than
   `FALLBACK_MIN_RESULTS` (10) jobs. That keeps Jooble's quota for when it matters.
3. **Stale cache**: every successful search is also stored under `stale:<key>` for 24 h. If every source fails,
   that copy is served with `stale: true` and the UI and chat say "results may be out of date".
Remotive was evaluated and rejected: its terms forbid redistributing listings in another job board.

All clients inherit `ResilientAPI`: timeout, retries with backoff on 429/5xx only, throttle, circuit breaker
(3 failures → skipped 60 s), and a parse failure counts as a failure.

**External APIs (6):** Adzuna, JSearch (RapidAPI), Jooble, Wikipedia REST, GitHub REST, Gemini.
Calendar uses the iCalendar standard (RFC 5545) and Google Calendar "add event" links, so it needs no OAuth.

### New tools (Weeks 5–6)
```
route ─┬─ salary_negotiation ──► negotiation ─┐
       ├─ career_path ─────────► career ──────┤─► END   (plus the Week 3–4 tools)
       └─ github_review ───────► github ──────┘
```
| Tool | Data | LLM role |
|---|---|---|
| Salary bands | listings grouped by experience (0–1, 1–3, 3–6, 6–10, 10+ yrs), percentiles, n ≥ 3 per band | none |
| Negotiation | offer percentile within the matching band → counter (below p25 → median; below median → midway to p75; to p75 → +8 %; above p75 → no counter) capped at +25 % unless a competing offer is higher | none: script is a template |
| Career path | role family ladder + required skills = core skills ∪ skills in ≥ 20 % of current postings, minus resume skills and skills marked done, ranked by demand, packed into 6-week phases; free/official resources | none |
| GitHub review | public repos (forks and archived excluded): languages → skills, activity in last 6 months, stars, README/description checks, skills on GitHub but not on the resume and vice versa | none |
| Mock interview v2 | spoken answers transcribed in the browser; pace (110–160 wpm), fillers/100 words, long pauses; follow-up question when an answer misses a key point / own action / result | follow-up wording only, guarded; rule fallback |

### Calendar (Week 6)
`calendar_events` (interview / follow-up / deadline, optionally linked to a tracked application). Each event
exports as `.ics` with two reminders (1 day and 1 hour before) and has a Google Calendar link. A private feed
URL (`/calendar/feed/<random token>.ics`, rotatable, revocable) lets Google/Outlook subscribe; it also lists
tracker next-action dates as all-day items. Email reminders go out from the same scheduler as alerts
(`dispatch_reminders`), marked sent only after success; rescheduling resets the reminder.

### Security and data (Week 7)
- **Encryption at rest:** chat messages, resume text, tracker notes, event notes and interview answers are
  encrypted per field with Fernet (AES-128-CBC + HMAC-SHA256). `FIELD_ENCRYPTION_KEYS` is a comma list: the
  first key encrypts, all keys decrypt, so keys rotate without downtime. Rows written before Week 7 are read as
  plaintext and encrypted on their next write. Production refuses to start without a key.
- **Headers:** CSP `default-src 'none'` on the API, nosniff, `X-Frame-Options: DENY`, no-referrer, HSTS in
  production; the frontend allows the microphone for itself only.
- **`/metrics`** requires `X-Metrics-Token` when `METRICS_TOKEN` is set.
- **Retention:** conversations idle > 180 days, search logs > 90 days and alert runs > 60 days are purged by the
  scheduler.
- **Data export:** `GET /me/export` returns everything stored about the user as JSON.
See [SECURITY_PRIVACY.md](SECURITY_PRIVACY.md).

### Performance (Week 7)
GZip on responses > 1 KB; cached search hits skip all sources; `/analytics/system` reports p50/p95 search
latency, cache hit rate and source failure rates from `search_logs`. Measurements: [BENCHMARKS.md](BENCHMARKS.md).
