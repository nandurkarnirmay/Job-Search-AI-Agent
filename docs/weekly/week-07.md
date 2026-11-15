# Week 7: Professional UI, analytics dashboard, microservices, data security, performance, documentation

## What we did
**UI.**
- **New pages:** Dashboard, Career (roadmap, salary, negotiation, GitHub), Settings (privacy, data export, delete
  account), and a calendar panel in the tracker.
- **Navigation:** responsive, with a mobile menu.
- **Landing page:** a feature overview. Logged-in users go straight to the dashboard.

**Analytics dashboard.**
- **Personal view:**
  - application funnel (tracked → applied → interview → offer, with conversion rates)
  - searches, applications and practice sessions per week for the last 8 weeks
  - interview score trend
  - upcoming events
- **Admin view:** users, searches per day, search latency p50/p95, cache hit rate, zero-result rate, failure rate
  per source, intent mix, tracker and alert totals.
- **Charts:** accessible, with a hover value and a table view.

**Microservices.** One codebase deploys as four services, chosen by the `SERVICE` variable: auth, jobs, resume and
interview.
- **Gateway:** the Next.js frontend is the API gateway (`/api/*` routes to the right service). The browser talks to
  one origin, so there is no CORS.
- **Migrations:** only the jobs service runs them.
- **Monolith fallback:** `SERVICE=all` still runs everything as one service (local development, free-tier fallback).
- **Honest limit:** the services share one database, so they are split by route ownership, not data ownership.

**Career data security.**
- **Field-level encryption** (Fernet: AES + HMAC) for chat messages, resume text, tracker and event notes, and
  interview answers.
  - Keys rotate with no downtime.
  - Older plaintext rows are still readable.
  - Production refuses to start without a key.
- **Security headers:** CSP, nosniff, frame denial, no-referrer, HSTS.
- **Monitoring:** `/metrics` is protected by a token.
- **Login protection:** attempts are now also limited per account (10/min). While writing the assessment we found
  that the per-IP limit could be bypassed with a spoofed `X-Forwarded-For` header, so we fixed it and added a test.
- **Retention:** conversations idle for 180 days, search logs older than 90 days and alert runs older than 60 days
  are deleted automatically.
- **Data export:** a JSON download of everything we store about the user.

**Performance.**
- **Compression:** GZip on API responses.
- **Benchmarks:** an offline benchmark of our own code:
  - routing one message takes 0.09 ms
  - skill extraction on a 1,850-word resume takes 11 ms
  - a 50-event calendar feed takes 1.6 ms
  So request latency is dominated by the job APIs, which is why caching and rules-first routing matter.
- **Live benchmark:** a script measures p50/p95 per endpoint on the deployment.
- **CI accuracy gate:** CI now fails if routing accuracy drops below 95 % or skill F1 drops below 0.95.

**Documentation.**
- `docs/API.md`: an integration guide (auth, errors, every endpoint per service), alongside the generated
  OpenAPI docs.
- `docs/USER_GUIDE.md`
- `docs/SECURITY_PRIVACY.md`: a privacy and security assessment covering the data inventory, a STRIDE threat model,
  controls with test evidence, DPDP Act principles, and a ranked list of known gaps.
- `docs/BENCHMARKS.md`
- A draft blog post.

## Contributions
| Member | Work this week |
|---|---|
| Member 1 | Analytics API (personal + admin), service split in `main.py`, gateway rewrites |
| Member 2 | Field encryption, key rotation, retention job, data export, login hardening |
| Member 3 | Dashboard, charts, settings page, navigation, landing page |
| Member 4 | Render blueprint for 4 services, security headers, metrics token, benchmarks, docs, tests |

## Challenges and decisions
- **Microservices on a free tier.** Four always-on services need about 2,900 instance-hours a month. Render's free
  plan gives 750. They fit only because idle services sleep, and each one cold-starts separately. We kept the
  monolith mode for the demo and documented both.
- **What to encrypt.** We encrypted the free-text fields where sensitive details live: offers, salaries in chat,
  career history. Fields used in queries or reminders (company names, statuses, event times) stay readable. The
  assessment explains the reasoning.
- **Known gaps we chose to document rather than hide:**
  - JWT in localStorage: the move to an httpOnly cookie is planned for Week 8
  - one database user shared by all services
  - no MFA or email verification

## Plan for next week (final)
- Move the token to an httpOnly cookie through the gateway.
- Build a held-out accuracy set written by people outside the team.
- Run the live latency benchmarks.
- Publish the blog post.
- Record the 8–10 minute demo video and tag v1.0.
