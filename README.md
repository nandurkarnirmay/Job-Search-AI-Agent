# Job Search AI Agent 🇮🇳

AI career platform for the Indian job market. Ask in plain English ("remote Python jobs in Bengaluru above
8 LPA for a fresher") and a LangGraph agent turns it into a search across several job sources, filtered by
city, experience, salary in LPA, work mode and notice period.

**Track B (Advanced)** · Status: **Week 4**: the agent has 6 career tools (job search, company research, salary
research, resume/ATS analysis, interview practice, application tracker), plus scheduled job-alert emails.
Plan: [docs/PLAN.md](docs/PLAN.md) · Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ·
Deployment: [docs/DEPLOY.md](docs/DEPLOY.md)

| | |
|---|---|
| Live app | _add Vercel URL_ |
| API docs | _add Render URL_/docs |
| Demo video | _add link_ |

## What works
**Week 4**
- Resume tool: upload PDF/DOCX (2 MB, validated by content, zip-bomb guard). The file isn't stored; only the
  text with email/phone removed and the parsed fields. Detects ~150 skills (tech, data, core engineering,
  business), standard sections, scanned/image PDFs ATS can't read, missing contact details, length problems
- ATS match: transparent 0–100 score (skills 70, required ×2 / preferred ×1, "Power BI or Tableau" counts once;
  title 15; structure 15) against a job from a search or a pasted description, with missing skills and fixes
- Skill-gap review: which skills current postings for a role ask for, and which your resume shows
- Interview practice: role/job-specific HR, technical and behavioural questions (curated bank incl. core
  mechanical topics; optional LLM extras); rule-based 1–5 feedback per answer (key points, STAR structure,
  measurable impact, concrete HR answers)
- Application tracker: save from search/chat, statuses Saved → Applied → Interview → Offer/Rejected/Withdrawn,
  history, notes, next-action date, pipeline counts
- Alert delivery: hourly Celery beat (docker-compose) or GitHub Actions cron (free hosting) → email over SMTP
  with one-click unsubscribe; jobs are marked sent only after a successful email; run history in the app
- Chat: "how does my resume match the first job?", "save the second job", "prepare me for the first job",
  "show my applications", "remove the salary filter", "any city"

**Week 3**
- Agent router (LangGraph): each message goes to job search, search refinement, company research, salary research
  or help. Rules route first; the LLM is called only for messages no rule can place, and its choice is
  rejected if it names a company or role that isn't in the message
- Conversation memory: threads stored in Postgres; follow-ups like "what about Pune?", "only remote",
  "show more", "tell me about the second company", "salary for the first one"
- Company research: Wikipedia overview + current openings in our sources + disclosed salaries. The LLM may only
  rephrase Wikipedia; any number it adds that isn't in the source is rejected. No invented reviews
- Salary research: percentiles (median, middle half, range) from salaries disclosed in listings and from Adzuna's
  salary histogram, always with sample size; "not enough data" instead of a guess below 3 data points.
  Numbers never pass through the LLM
- Job alerts: create from any search, daily/weekly, pause, preview; only jobs never sent before count as new
  (email delivery: Week 4)
- Profile: career goal, target roles (used for "show me jobs"), open to relocation
- Alembic migrations, applied on startup; a Week 2 database is detected and upgraded in place

**Week 2**
- Sign up / log in (JWT, bcrypt), profile with preferred cities, experience, skills, expected LPA, notice period
- `/chat`: LangGraph agent (Gemini) parses free text → filters; rule-based parser as fallback
- `/jobs/search`: Adzuna (India) + JSearch in parallel, merged and de-duplicated
- Indian fields extracted from listings: salary in LPA, experience, notice period, remote/hybrid/on-site
- Resilience: per-source retries with backoff, timeouts, circuit breaker, partial results if one source is down,
  Redis cache (in-memory fallback), per-user rate limits, one consistent error format
- Monitoring: Prometheus `/metrics`, structured JSON logs with request IDs, `/health`, admin search stats,
  optional Sentry
- CI/CD: GitHub Actions runs lint + tests (SQLite and Postgres) + frontend build; deploys to Render on `main`

## Stack
FastAPI · LangGraph · Gemini · PostgreSQL (Neon) · Redis (Upstash) · Next.js + Tailwind · Render · Vercel

## Run locally
Requirements: Python 3.12, Node 22, Docker.

```bash
# 1. Backend + Postgres + Redis
cp backend/.env.example backend/.env      # fill in API keys
docker compose up --build                 # API on http://localhost:8000/docs

# 2. Frontend
cd frontend
cp .env.example .env.local
npm install
npm run dev                               # http://localhost:3000
```

Without Docker: `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt`,
set `DATABASE_URL=sqlite:///./dev.db` and `REDIS_URL=` (empty → in-memory cache) in `backend/.env`, then
`uvicorn app.main:app --reload` (migrations run automatically on startup; `python -m app.migrate` runs them manually).

## Tests
```bash
cd backend && pytest -q && ruff check .
```

## Environment variables
See `backend/.env.example` and `frontend/.env.example`. Real values live only in `.env` files (git-ignored),
Render/Vercel settings and GitHub Secrets.

| Key | Get it from |
|---|---|
| `GOOGLE_API_KEY` | https://aistudio.google.com/app/apikey |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | https://developer.adzuna.com |
| `RAPIDAPI_KEY` | https://rapidapi.com → JSearch |
| `SMTP_*`, `EMAIL_FROM` | any SMTP provider, e.g. Brevo (free 300/day) or a Gmail App Password |
| `CRON_TOKEN` | any long random string; same value in Render and the GitHub secret |

## API
| Method | Path | |
|---|---|---|
| POST | `/auth/register`, `/auth/login` | returns JWT |
| GET / DELETE | `/auth/me` | current user / delete account and data |
| GET / PUT | `/me/profile` | career profile |
| GET | `/jobs/search?q=&city=&max_experience_years=&min_salary_lpa=&work_mode=&notice_period_days=` | filtered search |
| POST | `/chat` | `{"message": "...", "thread_id": optional}` → reply, intent, jobs / company / salary |
| GET / DELETE | `/chat/threads`, `/chat/threads/{id}` | conversation history |
| GET / POST | `/alerts` | list / create job alerts (max 5) |
| PATCH / DELETE | `/alerts/{id}` | pause, change frequency, delete |
| POST | `/alerts/{id}/preview` | what the next alert would contain |
| GET | `/alerts/{id}/runs`, `/alerts/unsubscribe?token=` | delivery history, email unsubscribe |
| POST / GET / DELETE | `/resume` | upload (multipart `file`), view parsed resume, delete |
| POST | `/resume/match` | `{"job_id"}` or `{"job_title", "description"}` → ATS score |
| GET | `/resume/review?role=` | skill-gap vs current postings |
| GET / POST | `/applications`, `/applications/pipeline` | tracker list (filter `?status=`), add, counts |
| PATCH / DELETE | `/applications/{id}` | status / notes / next action, remove |
| POST / GET | `/interview/sessions`, `/interview/sessions/{id}` | practice sets |
| POST | `/interview/sessions/{id}/questions/{qid}/answer` | feedback on one answer |
| POST | `/internal/alerts/dispatch` | scheduler only (`X-Cron-Token`) |
| GET | `/health`, `/metrics`, `/stats/search` (admin) | monitoring |

## Team
| Member | Ownership |
|---|---|
| _Name 1_ | LangGraph agent, LLM integration |
| _Name 2_ | Job/company data sources, search pipeline, caching |
| _Name 3_ | Next.js frontend, auth UX, deployment |
| _Name 4_ | FastAPI backend, database, CI/CD, monitoring |

## Data & ethics
Official APIs only (no scraping). Passwords are bcrypt-hashed; deleting an account deletes its profile,
conversations, alerts, resume, tracker and interview sessions. Resume files are never stored, and emails/phone
numbers are removed from the stored text. Resume suggestions say "if you genuinely have it": the tool never
tells users to claim skills they lack. Users can delete single conversations. Search logs are visible only to admins.
Salaries a source *estimated* are labelled as estimates. Company research never shows ratings or reviews,
because Glassdoor and AmbitionBox offer no public API and the agent must not invent them.
