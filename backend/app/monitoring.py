"""Prometheus metrics, request IDs, structured logs and optional Sentry."""
import json
import logging
import time
import uuid

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.config import get_settings

HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"])
HTTP_LATENCY = Histogram("http_request_duration_seconds", "HTTP latency", ["method", "route"])
SOURCE_CALLS = Counter("job_source_calls_total", "Calls to job sources", ["source", "outcome"])
SOURCE_LATENCY = Histogram("job_source_duration_seconds", "Job source latency", ["source"])
SEARCHES = Counter("job_searches_total", "Searches served", ["channel", "cache"])
SEARCH_RESULTS = Histogram("job_search_results", "Results per search", buckets=(0, 1, 5, 10, 20, 50, 100))
LLM_CALLS = Counter("llm_calls_total", "LLM calls", ["purpose", "outcome"])


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {"ts": self.formatTime(record), "level": record.levelname, "logger": record.name,
                "msg": record.getMessage()}
        for key in ("request_id", "method", "path", "status", "duration_ms", "user_id"):
            if hasattr(record, key):
                data[key] = getattr(record, key)
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data)


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def setup_sentry() -> None:
    dsn = get_settings().sentry_dsn
    if dsn:
        import sentry_sdk

        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.1, environment=get_settings().env, send_default_pii=False)


def install(app: FastAPI) -> None:
    access = logging.getLogger("app.access")

    @app.middleware("http")
    async def observe(request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["x-request-id"] = request.state.request_id
            return response
        finally:
            elapsed = time.perf_counter() - start
            route = request.scope.get("route")
            route_path = getattr(route, "path", "unmatched")  # template, not raw path: keeps label count low
            HTTP_REQUESTS.labels(request.method, route_path, str(status)).inc()
            HTTP_LATENCY.labels(request.method, route_path).observe(elapsed)
            access.info("request", extra={"request_id": request.state.request_id, "method": request.method,
                                          "path": request.url.path, "status": status,
                                          "duration_ms": round(elapsed * 1000)})

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
