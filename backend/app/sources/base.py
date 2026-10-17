"""Every job source inherits retries, timeouts, a client-side rate limit and a circuit breaker."""
import logging
import threading
import time
from abc import ABC, abstractmethod

import httpx

from app.domain import JobListing, SearchParams
from app.monitoring import SOURCE_CALLS, SOURCE_LATENCY

log = logging.getLogger("app.sources")

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class SourceError(Exception):
    """A source failed after retries, is misconfigured, or its circuit is open."""


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failures = 0
        self.opened_at: float | None = None
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self.opened_at is None:
                return True
            if time.monotonic() - self.opened_at >= self.cooldown_seconds:
                return True  # half-open: let one request test the source
            return False

    def record_success(self) -> None:
        with self._lock:
            self.failures, self.opened_at = 0, None

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.opened_at = time.monotonic()


class JobSource(ABC):
    name = "base"
    timeout_seconds = 10.0
    max_retries = 2
    min_interval_seconds = 1.0  # be polite to upstream APIs

    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(timeout=self.timeout_seconds)
        self.breaker = CircuitBreaker()
        self._last_call = 0.0
        self._lock = threading.Lock()

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def _request(self, params: SearchParams) -> httpx.Request: ...

    @abstractmethod
    def _parse(self, payload: dict) -> list[JobListing]: ...

    def _throttle(self) -> None:
        with self._lock:
            wait = self.min_interval_seconds - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()

    def search(self, params: SearchParams) -> list[JobListing]:
        if not self.is_configured():
            raise SourceError(f"{self.name}: API keys not configured")
        if not self.breaker.allow():
            SOURCE_CALLS.labels(self.name, "circuit_open").inc()
            raise SourceError(f"{self.name}: temporarily disabled after repeated failures")

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._throttle()
            start = time.perf_counter()
            try:
                resp = self._client.send(self._request(params))
                SOURCE_LATENCY.labels(self.name).observe(time.perf_counter() - start)
                if resp.status_code in RETRYABLE_STATUS:
                    raise httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=resp.request, response=resp)
                resp.raise_for_status()
                jobs = self._parse(resp.json())
                self.breaker.record_success()
                SOURCE_CALLS.labels(self.name, "ok").inc()
                return jobs
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code not in RETRYABLE_STATUS:
                    break  # 4xx such as bad keys: retrying will not help
            except (httpx.TimeoutException, httpx.TransportError, ValueError) as e:
                last_error = e
            if attempt < self.max_retries:
                time.sleep(min(0.5 * 2**attempt, 4))
        self.breaker.record_failure()
        SOURCE_CALLS.labels(self.name, "error").inc()
        log.warning("%s failed: %s", self.name, last_error)
        raise SourceError(f"{self.name}: {last_error}")
