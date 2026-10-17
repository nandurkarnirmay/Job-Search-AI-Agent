"""Redis cache with an in-memory fallback. A cache failure must never fail a user request."""
import logging
import threading
import time
from functools import lru_cache

from app.config import get_settings

log = logging.getLogger("app.cache")


class MemoryCache:
    backend = "memory"

    def __init__(self):
        self._data: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires, value = item
            if expires < time.time():
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: str, ttl: int) -> None:
        with self._lock:
            self._data[key] = (time.time() + ttl, value)

    def incr(self, key: str, ttl: int) -> int:
        with self._lock:
            expires, value = self._data.get(key, (0.0, "0"))
            if expires < time.time():
                expires, value = time.time() + ttl, "0"
            new = int(value) + 1
            self._data[key] = (expires, str(new))
            return new

    def ping(self) -> bool:
        return True


class RedisCache:
    backend = "redis"

    def __init__(self, url: str):
        import redis

        self._r = redis.Redis.from_url(url, decode_responses=True, socket_timeout=2, socket_connect_timeout=2)
        self._fallback = MemoryCache()

    def get(self, key: str) -> str | None:
        try:
            return self._r.get(key)
        except Exception as e:
            log.warning("redis get failed, using memory: %s", e)
            return self._fallback.get(key)

    def set(self, key: str, value: str, ttl: int) -> None:
        try:
            self._r.set(key, value, ex=ttl)
        except Exception as e:
            log.warning("redis set failed, using memory: %s", e)
            self._fallback.set(key, value, ttl)

    def incr(self, key: str, ttl: int) -> int:
        try:
            pipe = self._r.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl)  # key is per-window, so refreshing the TTL is harmless
            return int(pipe.execute()[0])
        except Exception as e:
            log.warning("redis incr failed, using memory: %s", e)
            return self._fallback.incr(key, ttl)

    def ping(self) -> bool:
        try:
            return bool(self._r.ping())
        except Exception:
            return False


@lru_cache
def get_cache() -> MemoryCache | RedisCache:
    url = get_settings().redis_url
    if not url:
        log.info("REDIS_URL not set: using in-memory cache")
        return MemoryCache()
    return RedisCache(url)
