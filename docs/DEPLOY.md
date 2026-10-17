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
