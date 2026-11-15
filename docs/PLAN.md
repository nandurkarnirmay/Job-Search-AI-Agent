# Plan of Action – Track B (Advanced)

| Week | Goals | Checkpoint |
|---|---|---|
| 1 | Repo, stack, roles, issue board | ✅ |
| 2 | FastAPI + Postgres + Redis, JWT auth + profiles, Adzuna + JSearch with retries/circuit breaker/cache, LangGraph chat agent, monitoring (metrics, logs, health, stats), CI/CD, Next.js UI, deploy, 2-min demo | **Deployed demo** ✅ |
| 3 | Agent router + conversation memory; company research and salary research tools; job alerts (API, new-job detection); career-goal profile; Alembic migrations | ✅ 3 of 5 agent tools |
| 4 | Resume tool (PDF/DOCX, skills, ATS score, skill gap), interview practice with feedback, application tracker, alert emails (Celery beat / GitHub cron), filter removal in follow-ups | ✅ **6 tools** |
| 5 | 5+ APIs with fallbacks (Jooble fallback tier + stale cache, GitHub profile analysis), salary bands by experience, negotiation advisor, career-path roadmap | ✅ 6 APIs |
| 6 | Voice mock interviews with follow-ups + session report, calendar (events, .ics, feed, email reminders), career/salary pages, accuracy eval | ✅ **Specialised features** |
| 7 | Analytics dashboard, 4 services behind a Next.js gateway, field encryption, security headers, retention, data export, API docs, user guide, benchmarks | ✅ |
| 8 | API docs, user guide, blog post, benchmarks, privacy assessment, 8–10 min demo, v1.0 | **Final** |

## Known Week 2 shortcuts (scheduled fixes)
| Shortcut | Fix in |
|---|---|
| ~~Tables created on startup, no migrations~~ | Done in Week 3 (Alembic) |
| JWT in localStorage | Partly mitigated (CSP, no third-party scripts, safe links). httpOnly cookie moved to Week 8 |
| ~~One service, not microservices~~ | Done in Week 7 (4 services, shared DB) |
| Own JWT auth instead of Firebase/Auth0 | Decide by Week 4: keep (documented reason: no vendor lock-in, testable) or switch |
| ~~`/metrics` is public~~ | Done in Week 7 (token) |
| ~~Rule-based follow-ups can add filters but not remove them~~ | Done in Week 4 |
| Company research has no reviews/culture data (no public API) | Permanent; stated in every reply |
| ~~Alert emails not sent yet~~ | Done in Week 4 |
| ~~Resume text stored unencrypted~~ | Done in Week 7 (field encryption) |
| ~~Interview practice is typed only~~ | Done in Week 6 (browser speech-to-text) |
| Celery worker isn't free on Render | Using GitHub Actions cron in production; Celery for local/paid hosting |
