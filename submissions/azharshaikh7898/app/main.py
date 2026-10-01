from pathlib import Path
from fastapi.staticfiles import StaticFiles
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from . import models  # noqa: F401  (registers tables on Base.metadata)
from .db import Base, engine
from .logging_conf import request_id_var, setup_logging
from .routes import auth, documents, health
from .routes import qa

setup_logging()
log = logging.getLogger("documind")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="DocuMind", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = (request.headers.get("X-Request-ID") or uuid.uuid4().hex)[:64]
    token = request_id_var.set(rid)
    start = time.perf_counter()
    try:
        try:
            response = await call_next(request)
        except Exception:
            log.exception("unhandled error")
            response = JSONResponse({"detail": "Internal server error"}, status_code=500)
        response.headers["X-Request-ID"] = rid
        log.info(
            "request",
            extra={"extra_fields": {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "ms": round((time.perf_counter() - start) * 1000, 1),
            }},
        )
        return response
    finally:
        request_id_var.reset(token)


app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(health.router)
app.include_router(qa.router)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
