# Plan of Action – Track B (Advanced)

| Week | Goals | Checkpoint |
|---|---|---|
| 1 | Repo, stack, roles, issue board | ✅ |
| 2 | FastAPI + Postgres + Redis, JWT auth + profiles, Adzuna + JSearch with retries/circuit breaker/cache, LangGraph chat agent, monitoring (metrics, logs, health, stats), CI/CD, Next.js UI, deploy, 2-min demo | **Deployed demo** |
| 3 | Agent router node; company research tool; Alembic migrations; job alerts design | |
| 4 | Resume upload + NLP parsing, job–resume match score, application tracking, email alerts (Celery) | **4+ tools** |
| 5 | 5+ APIs with fallbacks (GitHub, company data), full schema | |
| 6 | AI mock interviews, salary benchmarking + negotiation, career roadmap, calendar integration | **Specialised features** |
| 7 | Analytics dashboard, split services (auth/jobs/resume/interview), security hardening (httpOnly cookies, resume encryption), performance | |
| 8 | API docs, user guide, blog post, benchmarks, privacy assessment, 8–10 min demo, v1.0 | **Final** |

## Known Week 2 shortcuts (scheduled fixes)
| Shortcut | Fix in |
|---|---|
| Tables created on startup, no migrations | Week 3 (Alembic) |
| JWT in localStorage | Week 7 (httpOnly cookie) |
| One service, not microservices | Week 7 |
| Own JWT auth instead of Firebase/Auth0 | Decide by Week 4: keep (documented reason: no vendor lock-in, testable) or switch |
| `/metrics` is public | Week 7 (token or private network) |
