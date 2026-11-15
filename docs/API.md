# API reference (v0.7)

Interactive docs (OpenAPI/Swagger) are generated from the code: `https://<service>/docs`, schema at
`/openapi.json`. This page is the integration guide: base URLs, auth, errors, and every endpoint.

## Base URL
| Setup | Base URL |
|---|---|
| Through the frontend gateway (recommended) | `https://<project>.vercel.app/api` |
| Monolith direct | `https://<service>.onrender.com` |
| Microservices direct | the service that owns the route (table below) |
| Local | `http://localhost:8000` |

## Auth
`POST /auth/register` or `/auth/login` returns `{"access_token": "...", "token_type": "bearer"}`. Send it as
`Authorization: Bearer <token>` on every other call (expires after `JWT_EXPIRE_MINUTES`, default 24 h). All four
services accept the same token (shared `JWT_SECRET`).

```bash
TOKEN=$(curl -s -X POST $BASE/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"a@b.in","password":"longpassword"}' | jq -r .access_token)
curl -s "$BASE/jobs/search?q=python&city=Pune&max_experience_years=2" -H "Authorization: Bearer $TOKEN"
```

## Errors
Every error has the same shape and a request ID for support:
```json
{"error": {"code": "not_found", "message": "Application not found", "request_id": "6f1c…"}}
```
| Status | When |
|---|---|
| 400 / 422 | invalid input (`validation_error` lists the fields) |
| 401 | missing/expired token |
| 403 | admin-only endpoint |
| 404 | not found **or not yours** (we never reveal other users' ids) |
| 409 | duplicate (email taken, job already tracked) |
| 413 / 415 | resume too large / not PDF or DOCX |
| 429 | rate limit (`RATE_LIMIT_PER_MINUTE`, default 30/min on search and chat); retry after `Retry-After` |
| 503 | every job source down and no cached copy; `github_unavailable` |

## Endpoints

### auth service
| Method | Path | Body / query | Returns |
|---|---|---|---|
| POST | `/auth/register` | `email`, `password` (≥ 8) | token |
| POST | `/auth/login` | `email`, `password` | token |
| GET | `/auth/me` | | user |
| DELETE | `/auth/me` | | 204; deletes the account and **all** its data |
| GET / PUT | `/me/profile` | cities, experience, skills, expected LPA, notice, work mode, target roles, `github_username` | profile |
| GET | `/me/export` | | JSON file with everything stored about you |

### jobs service
| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/jobs/search` | `q`, `city`, `max_experience_years`, `min_salary_lpa`, `work_mode`, `notice_period_days`, `page` | jobs, `sources_ok/failed`, `cache_hit`, `stale` |
| POST | `/chat` | `message`, `thread_id?` | reply, intent, jobs / company / salary / `extras` (ats, interview, application, negotiation, career, github) |
| GET / DELETE | `/chat/threads`, `/chat/threads/{id}` | | history |
| GET | `/salary/benchmark` | `role`, `city?`, `experience_years?` | percentiles from listings + market, `bands` by experience |
| POST | `/salary/negotiate` | `role`, `offer_lpa`, `city?`, `experience_years?`, `current_lpa?`, `competing_lpa?`, `notice_period_days?` | verdict, percentile, counter, talking points, email script, CTC checklist |
| GET | `/career/path` | `role?` (default: first target role in profile) | ladder, phases of skills with resources and projects |
| PUT | `/career/progress` | `skill`, `status` (`todo`/`learning`/`done`) | saved status |
| POST | `/github/analyse` | `username` | repo/language summary, skills, resume gaps, checks |
| GET / POST | `/applications` | `?status=` / `job_id` or manual fields | tracker |
| GET | `/applications/pipeline` | | counts per status |
| PATCH / DELETE | `/applications/{id}` | status, notes, `next_action_on` | |
| GET / POST | `/calendar/events` | `kind`, `title`, `starts_at` (ISO with timezone), `duration_minutes`, `location`, `notes`, `remind`, `application_id?` | events with `google_calendar_url` |
| PATCH / DELETE | `/calendar/events/{id}` | any field | rescheduling re-arms the reminder |
| GET | `/calendar/events/{id}.ics` | | iCalendar file |
| POST / DELETE | `/calendar/feed` | | create/rotate or revoke the private feed URL |
| GET | `/calendar/feed/{token}.ics` | public, token is the secret | subscribable calendar |
| GET / POST | `/alerts` | search params, `frequency` | max 5 per user |
| PATCH / DELETE | `/alerts/{id}` | | |
| POST | `/alerts/{id}/preview` | | next digest |
| GET | `/alerts/{id}/runs` | | delivery history |
| GET | `/analytics/me` | | funnel, pipeline, 8-week activity, practice trend |
| GET | `/analytics/system` | admin | users, latency p50/p95, cache hit rate, source failures, intents |
| GET | `/stats/search` | admin | search log stats |
| POST | `/internal/alerts/dispatch` | header `X-Cron-Token` | alerts + reminders + retention purge |

### resume service
| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/resume` | multipart `file` (PDF/DOCX, ≤ 2 MB) | parsed resume (file not stored) |
| GET / DELETE | `/resume` | | |
| POST | `/resume/match` | `job_id` or `job_title` + `description` | ATS score 0–100 with breakdown |
| GET | `/resume/review` | `role?` | skill demand vs your resume |

### interview service
| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/interview/sessions` | `role` or `job_id`, `company?` | question set |
| GET | `/interview/sessions`, `/interview/sessions/{id}` | | |
| POST | `/interview/sessions/{id}/questions/{qid}/answer` | `answer`, optional `duration_seconds`, `long_pauses` (voice) | score, criteria, tips, `speech` metrics, `followup` question |
| GET | `/interview/sessions/{id}/report` | | averages by type, weakest answers, pace, next steps |
| DELETE | `/interview/sessions/{id}` | | |

### every service
`GET /health` (status, service name, database, cache, sources) · `GET /metrics` (Prometheus; needs
`X-Metrics-Token` when `METRICS_TOKEN` is set).

## Integration notes
- Numbers (salaries, scores, counts) are always computed in code, never by the LLM, so they're reproducible
  for the same data.
- `GET /jobs/search` with `stale: true` means every source failed and you got the last good result (≤ 24 h).
- Job ids are stable per listing; pass them to `/applications`, `/resume/match` and `/interview/sessions`.
- Times: send ISO 8601 with an offset (`2026-11-20T10:30:00+05:30`); naive times are rejected.
