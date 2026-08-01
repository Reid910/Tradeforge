import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, status

from app.core.config import settings

# In-memory fixed-window limiter. Fine for a single backend instance; if this
# ever runs behind multiple instances, move the counters to Redis instead.
_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def check_auth_rate_limit(key: str) -> None:
    now = time.monotonic()
    window_start = now - settings.auth_rate_limit_window_seconds

    with _lock:
        attempts = [t for t in _attempts[key] if t > window_start]
        if len(attempts) >= settings.auth_rate_limit_attempts:
            _attempts[key] = attempts
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Try again shortly.",
            )
        attempts.append(now)
        _attempts[key] = attempts
