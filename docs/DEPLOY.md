# Deployment (all free tiers)

| Piece | Service | Region |
|---|---|---|
| Postgres | Neon | AWS Singapore |
| Redis | Upstash | Mumbai or Singapore |
| Backend | Render (Blueprint `render.yaml`) | Singapore |
| Frontend | Vercel | auto |

1. **Neon** → new project → copy the connection string (`postgresql://...?sslmode=require`).
2. **Upstash** → create Redis database → copy the `rediss://...` URL.
3. **Render** → New → Blueprint → pick this repo. Fill in `DATABASE_URL`, `REDIS_URL`, `GOOGLE_API_KEY`,
   `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `RAPIDAPI_KEY`, `ADMIN_EMAILS`. Leave `FRONTEND_ORIGINS` for step 5.
   Deploy once manually, then open `https://<service>.onrender.com/health`: database must be `true`,
   cache backend `redis`, sources `configured`.
4. **Vercel** → Add New Project → this repo → **Root Directory `frontend`** → env var
   `NEXT_PUBLIC_API_URL=https://<service>.onrender.com` → Deploy.
5. Back in Render: `FRONTEND_ORIGINS=https://<project>.vercel.app` (no trailing slash) → save (redeploys).
6. **CD hook**: Render → service → Settings → Deploy Hook → copy URL → GitHub repo → Settings → Secrets and
   variables → Actions → `RENDER_DEPLOY_HOOK_URL`. From now on every push to `main` that passes CI deploys.
7. **Branch protection**: GitHub → Settings → Branches → rule for `main`: require PR + status checks
   `backend` and `frontend`.

Free-tier gotcha: Render's free service sleeps after ~15 min idle and takes ~1 min to wake. Before a demo,
open `/health` and wait for it to respond.

## Week 3 upgrade
Nothing manual: on the first start of the Week 3 backend, `AUTO_MIGRATE` detects the Week 2 tables, stamps them
as migration `0001` and applies `0002` (new profile columns, chat threads/messages, job alerts). Check the Render
log for `database schema is up to date`. Before deploying, back up the Neon database (Neon → Branches →
create a branch from main) so a bad migration can be rolled back by switching branches.

## Week 4 setup
1. **Migration** `0003` runs automatically on startup (new tables: resumes, applications, interview_sessions,
   alert_runs). Back up Neon first (create a branch).
2. **Email (optional; without it alerts stay in-app under History).** Brevo free plan → SMTP & API → SMTP key.
   In Render set `SMTP_HOST=smtp-relay.brevo.com`, `SMTP_PORT=587`, `SMTP_USER=<Brevo login>`,
   `SMTP_PASSWORD=<SMTP key>`, `EMAIL_FROM=<a sender you verified in Brevo>`. Gmail alternative:
   `smtp.gmail.com:587` with an App Password (needs 2-step verification).
3. **Links in emails:** `PUBLIC_APP_URL=https://<project>.vercel.app`, `PUBLIC_API_URL=https://<service>.onrender.com`.
4. **Scheduler:** Render generates `CRON_TOKEN`; copy it. GitHub → Settings → Secrets → Actions: add
   `CRON_TOKEN` (same value) and `API_URL=https://<service>.onrender.com`. Test with Actions → "Job alerts
   dispatch" → Run workflow; the log should print `{"alerts": …}`.
5. Locally, `docker compose up` also starts a Celery worker+beat (`worker` service) that does the same hourly.

## Weeks 5–7 setup
**Back up Neon first** (Neon → Branches → create branch from main). Migration `0004` (calendar events, skill
progress, calendar token, GitHub username) runs automatically on the jobs/all service.

### New environment variables
| Key | Required | Value |
|---|---|---|
| `FIELD_ENCRYPTION_KEYS` | **yes in production** (startup fails without it) | long random string; generate with `python -c "import secrets;print(secrets.token_urlsafe(32))"`. **Keep a copy offline. Losing it makes encrypted data unreadable.** To rotate: put the new key first, keep the old one after a comma |
| `METRICS_TOKEN` | recommended | random string; Prometheus sends it as `X-Metrics-Token` |
| `JOOBLE_API_KEY` | recommended | https://jooble.org/api/about (free key by email) |
| `GITHUB_TOKEN` | optional | fine-grained token with **no permissions** (public data only); raises the limit from 60 to 5,000 requests/h |
| `SERVICE` | per service | `all`, `auth`, `jobs`, `resume` or `interview` |

### Option A: monolith (simplest, free)
Keep a single Render web service with `SERVICE=all`. Vercel: `API_URL=https://<service>.onrender.com`. Done.

### Option B: four services (what `render.yaml` describes)
1. Render → Blueprint → sync. It creates the env group `job-agent-shared` (generates `JWT_SECRET`,
   `FIELD_ENCRYPTION_KEYS`, `METRICS_TOKEN`) and four services. **If you already have a `JWT_SECRET` /
   data, copy the old `JWT_SECRET` into the group** or every user is logged out.
2. Fill the group's manual values (`DATABASE_URL`, `REDIS_URL`, `FRONTEND_ORIGINS`, `PUBLIC_APP_URL`,
   `PUBLIC_API_URL`, `ADMIN_EMAILS`) and the jobs service's API keys, SMTP and `CRON_TOKEN`.
3. Vercel → env: `JOBS_SERVICE_URL`, `AUTH_SERVICE_URL`, `RESUME_SERVICE_URL`, `INTERVIEW_SERVICE_URL`
   (each `https://<name>.onrender.com`), and remove `NEXT_PUBLIC_API_URL` so the browser uses `/api`.
4. `PUBLIC_API_URL=https://<project>.vercel.app/api` (email unsubscribe and calendar feed links go through the
   gateway).
5. GitHub secret `API_URL` (alerts cron) → the jobs service URL.

Free-tier cost: Render gives 750 instance-hours/month per workspace. Four always-on services need ~2,900, so
on the free plan they only fit because they sleep when idle; each one cold-starts (~1 min) separately. For the
demo, wake all four (`/health` on each) a few minutes before, or present Option A.

### Check after deploying
- `/health` on each service: `database: true`, `service: <name>`.
- `curl -I https://<service>/health` shows `content-security-policy` and `x-content-type-options`.
- `/metrics` without the header → 404.
- App → Settings → "Download my data" returns JSON.
