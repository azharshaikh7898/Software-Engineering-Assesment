import logging

import redis
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ..config import settings
from ..db import engine

log = logging.getLogger("documind.health")
router = APIRouter(tags=["health"])


def check_database() -> str:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return "ok"


def check_vector_store() -> str:
    if engine.dialect.name != "postgresql":
        return "skipped (not postgres)"
    with engine.connect() as conn:
        row = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).first()
    if row is None:
        raise RuntimeError("pgvector extension missing")
    return "ok"


def _redis() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)


def check_queue() -> str:
    _redis().ping()
    return "ok"


def check_worker() -> str:
    from rq import Worker

    if Worker.count(connection=_redis()) < 1:
        raise RuntimeError("no worker registered")
    return "ok"


CHECKS = {
    "database": check_database,
    "vector_store": check_vector_store,
    "queue": check_queue,
    "worker": check_worker,
}


@router.get("/livez")
def livez():
    return {"status": "ok"}


@router.get("/health")
def health():
    results, healthy = {}, True
    for name, fn in CHECKS.items():
        try:
            results[name] = {"status": "ok", "detail": fn()}
        except Exception:
            log.exception("health check failed", extra={"extra_fields": {"check": name}})
            results[name] = {"status": "down"}
            healthy = False
    body = {"status": "ok" if healthy else "degraded", "checks": results}
    return JSONResponse(body, status_code=200 if healthy else 503)
