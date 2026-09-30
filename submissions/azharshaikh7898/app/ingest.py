import logging

from sqlalchemy import delete

from . import embeddings
from .chunking import chunk_pages
from .config import settings
from .db import SessionLocal
from .extract import IngestError, extract_pages
from .models import Chunk, Document

log = logging.getLogger("documind.ingest")


def _mark_failed(db, doc_id: str, reason: str) -> None:
    db.rollback()
    doc = db.get(Document, doc_id)
    if doc is not None:  # may have been deleted meanwhile
        doc.status = "failed"
        doc.error = reason[:500]
        db.commit()


def ingest_document(doc_id: str) -> None:
    """Background job: extract -> chunk -> embed -> store. Safe to run twice (idempotent)."""
    with SessionLocal() as db:
        doc = db.get(Document, doc_id)
        if doc is None:
            log.info("document deleted before processing", extra={"extra_fields": {"document_id": doc_id}})
            return
        doc.status = "processing"
        doc.error = None
        db.commit()
        try:
            pages = extract_pages(doc.filename, doc.content)
            chunks = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)
            if not chunks:
                raise IngestError("No extractable text")
            vectors = embeddings.embed_documents([c.text for c in chunks])
            db.execute(delete(Chunk).where(Chunk.document_id == doc_id))
            db.add_all(
                Chunk(document_id=doc_id, user_id=doc.user_id, idx=i, page=c.page, content=c.text, embedding=v)
                for i, (c, v) in enumerate(zip(chunks, vectors))
            )
            doc.status = "ready"
            db.commit()
            log.info("document ready", extra={"extra_fields": {"document_id": doc_id, "chunks": len(chunks)}})
        except IngestError as exc:  # bad input: retrying will not help
            _mark_failed(db, doc_id, str(exc))
        except Exception:  # unexpected/transient: mark failed, re-raise so RQ retries
            log.exception("ingestion failed", extra={"extra_fields": {"document_id": doc_id}})
            _mark_failed(db, doc_id, "Processing failed; please try again")
            raise
