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
