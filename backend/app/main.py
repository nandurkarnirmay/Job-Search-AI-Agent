from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import monitoring
from app.config import get_settings
from app.db import init_db
from app.errors import register_error_handlers
from app.routers import auth, chat, health, jobs, profile, stats

monitoring.setup_logging()
monitoring.setup_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Job Search AI Agent API", version="0.2.0", lifespan=lifespan,
              description="Career assistant for the Indian job market (Track B, Week 2).")

app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["x-request-id"])
monitoring.install(app)
register_error_handlers(app)

for r in (health.router, auth.router, profile.router, jobs.router, chat.router, stats.router):
    app.include_router(r)


@app.get("/", include_in_schema=False)
def root():
    return {"name": "Job Search AI Agent API", "docs": "/docs", "health": "/health"}
