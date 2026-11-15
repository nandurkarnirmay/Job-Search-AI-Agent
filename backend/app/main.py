"""One codebase, several deploy units. SERVICE selects which routers this process serves:

  all        everything (local dev, single free-tier instance)
  auth       accounts, profile, data export
  jobs       search, chat agent, alerts, tracker, calendar, career tools, analytics, scheduler endpoint
  resume     resume upload, ATS matching, skill-gap review
  interview  interview practice sessions

Every unit verifies JWTs itself (shared secret, stateless), so no service calls another to authenticate.
The Next.js frontend is the gateway: /api/* paths are rewritten to the right service (frontend/next.config.mjs)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app import monitoring
from app.config import get_settings
from app.errors import register_error_handlers
from app.migrate import run_migrations
from app.routers import (
    alerts,
    analytics,
    applications,
    auth,
    calendar,
    career,
    chat,
    health,
    internal,
    interview,
    jobs,
    privacy,
    profile,
    resume,
    stats,
)

SERVICES = {
    "auth": [auth, profile, privacy],
    "jobs": [jobs, chat, alerts, applications, calendar, career, analytics, stats, internal],
    "resume": [resume],
    "interview": [interview],
}
SERVICES["all"] = [m for mods in SERVICES.values() for m in mods]

monitoring.setup_logging()
monitoring.setup_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if s.auto_migrate and s.service in ("all", "jobs"):  # exactly one deploy unit owns migrations
        run_migrations()
    yield


settings = get_settings()
app = FastAPI(title=f"Job Search AI Agent API ({settings.service})", version="0.7.0", lifespan=lifespan,
              description="Career assistant for the Indian job market (Track B, Week 7). "
                          "See docs/API.md for the service map and integration guide.")

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["x-request-id"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    h = response.headers
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Referrer-Policy", "no-referrer")
    h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):  # Swagger UI needs its CDN scripts
        h.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    if get_settings().env == "production":
        h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


monitoring.install(app)
register_error_handlers(app)

app.include_router(health.router)
for module in SERVICES[settings.service]:
    app.include_router(module.router)


@app.get("/", include_in_schema=False)
def root():
    return {"name": "Job Search AI Agent API", "service": settings.service, "docs": "/docs", "health": "/health"}
