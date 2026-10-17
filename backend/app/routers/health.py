from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.cache import get_cache
from app.db import engine
from app.sources.aggregator import get_aggregator

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """Liveness + dependency status. Returns 503 only when the database is down."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    cache = get_cache()
    sources = {s.name: ("configured" if s.is_configured() else "missing_keys") +
               ("" if s.breaker.allow() else ",circuit_open") for s in get_aggregator().sources}
    body = {"status": "ok" if db_ok else "degraded", "database": db_ok,
            "cache": {"backend": cache.backend, "ok": cache.ping()}, "sources": sources}
    return JSONResponse(body, status_code=200 if db_ok else 503)
