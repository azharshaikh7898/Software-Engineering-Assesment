import logging
import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..jobs import enqueue_ingest
from ..models import Chunk, Document, User
from ..security import current_user

log = logging.getLogger("documind.documents")
router = APIRouter(prefix="/documents", tags=["documents"])
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    filename: str
    status: str
    error: str | None
    created_at: datetime


def get_owned(db: Session, user: User, doc_id: str) -> Document:
    """404 (not 403) for other users' documents, so IDs reveal nothing."""
    doc = db.scalar(select(Document).where(Document.id == doc_id, Document.user_id == user.id))
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


@router.post("", response_model=DocumentOut, status_code=202)
def upload(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    name = os.path.basename((file.filename or "").replace("\\", "/"))[:255]
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Only .pdf, .txt and .md files are supported")

    limit = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File exceeds the {settings.max_upload_mb} MB limit")
    if not data:
        raise HTTPException(400, "File is empty")
    if ext == ".pdf" and not data.startswith(b"%PDF-"):
        raise HTTPException(400, "File is not a valid PDF")

    owned = db.scalar(select(func.count()).select_from(Document).where(Document.user_id == user.id))
    if owned >= settings.max_docs_per_user:
        raise HTTPException(409, f"Document limit reached ({settings.max_docs_per_user})")

    doc = Document(user_id=user.id, filename=name, content=data)
    db.add(doc)
    db.commit()
    try:
        enqueue_ingest(doc.id)
    except Exception:
        log.exception("could not enqueue ingestion", extra={"extra_fields": {"document_id": doc.id}})
        doc.status = "failed"
        doc.error = "Could not queue processing; please upload again"
        db.commit()
        raise HTTPException(503, "Processing queue unavailable")
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Document).where(Document.user_id == user.id).order_by(Document.created_at.desc())
    ).all()


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_owned(db, user, doc_id)


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = get_owned(db, user, doc_id)
    db.execute(delete(Chunk).where(Chunk.document_id == doc.id))  # explicit, does not rely on FK cascade
    db.delete(doc)
    db.commit()
    return Response(status_code=204)
