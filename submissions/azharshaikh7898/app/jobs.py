from redis import Redis
from rq import Queue, Retry

from .config import settings

QUEUE_NAME = "ingest"


def get_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=Redis.from_url(settings.redis_url))


def enqueue_ingest(doc_id: str) -> None:
    if settings.queue_sync:  # tests/dev only
        from .ingest import ingest_document

        ingest_document(doc_id)
        return
    # job referenced by import path so the API process never imports pypdf/fastembed
    get_queue().enqueue(
        "app.ingest.ingest_document", doc_id, job_timeout=600, retry=Retry(max=2, interval=[10, 30])
    )
