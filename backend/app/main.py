from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import monitoring
from app.config import get_settings
from app.errors import register_error_handlers
from app.migrate import run_migrations
from app.routers import alerts, applications, auth, chat, health, internal, interview, jobs, profile, resume, stats

monitoring.setup_logging()
monitoring.setup_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if get_settings().auto_migrate:
        run_migrations()
    yield


app = FastAPI(title="Job Search AI Agent API", version="0.4.0", lifespan=lifespan,
              description="Career assistant for the Indian job market (Track B, Week 4).")

app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["x-request-id"])
monitoring.install(app)
register_error_handlers(app)

for r in (health.router, auth.router, profile.router, jobs.router, chat.router, alerts.router, resume.router,
          applications.router, interview.router, internal.router, stats.router):
    app.include_router(r)


@app.get("/", include_in_schema=False)
def root():
    return {"name": "Job Search AI Agent API", "docs": "/docs", "health": "/health"}
