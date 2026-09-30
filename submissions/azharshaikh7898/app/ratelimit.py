import logging
import time
from functools import lru_cache

import redis
from fastapi import Depends, HTTPException

from .config import settings
from .models import User
from .security import current_user

log = logging.getLogger("documind.ratelimit")


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)


def enforce_rate_limit(user: User = Depends(current_user)) -> None:
    """Per-user fixed-window limits (per minute and per day), counted in Redis.

    Fails closed: if Redis is down the endpoint returns 503 rather than allowing unlimited LLM spend.
    """
    now = int(time.time())
    windows = (("minute", 60, settings.rate_limit_per_min), ("day", 86400, settings.rate_limit_per_day))
    try:
        r = get_redis()
        for label, seconds, limit in windows:
            key = f"rl:{user.id}:{label}:{now // seconds}"
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, seconds + 5)
            count, _ = pipe.execute()
            if count > limit:
                retry_after = seconds - now % seconds
                raise HTTPException(
                    429,
                    f"Rate limit exceeded ({limit} questions per {label}). Try again in {retry_after}s.",
                    headers={"Retry-After": str(retry_after)},
                )
    except redis.RedisError:
        log.exception("rate limiter unavailable")
        raise HTTPException(503, "Rate limiter unavailable; please try again shortly")
