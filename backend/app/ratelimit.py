"""Fixed-window rate limit (per user per endpoint) to protect our free-tier API quotas."""
import time

from app.cache import get_cache
from app.config import get_settings
from app.errors import RateLimitedError

WINDOW_SECONDS = 60


def check_rate_limit(key: str) -> None:
    limit = get_settings().rate_limit_per_minute
    window = int(time.time() // WINDOW_SECONDS)
    count = get_cache().incr(f"rl:{key}:{window}", WINDOW_SECONDS + 5)
    if count > limit:
        raise RateLimitedError(f"Too many requests: limit is {limit} per minute. Try again shortly.")
