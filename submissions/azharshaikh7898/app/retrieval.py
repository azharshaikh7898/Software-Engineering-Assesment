import math
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Chunk, Document


@dataclass(frozen=True)
class Hit:
    chunk_id: int
    document_id: str
    filename: str
    page: int | None
    content: str
    score: float  # cosine similarity, higher is better


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def search(db: Session, user_id: int, query_vec: list[float], k: int,
           document_ids: list[str] | None = None) -> list[Hit]:
    """Top-k chunks for one user, ready documents only. The user filter is part of the SQL itself."""
    base = (
        select(Chunk, Document.filename)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.user_id == user_id, Document.user_id == user_id, Document.status == "ready")
    )
    if document_ids:
        base = base.where(Chunk.document_id.in_(document_ids))

    if db.get_bind().dialect.name == "postgresql":  # pgvector does the ranking
        dist = Chunk.embedding.cosine_distance(query_vec)
        rows = db.execute(base.add_columns(dist.label("dist")).order_by(dist).limit(k)).all()
        return [Hit(c.id, c.document_id, fn, c.page, c.content, 1.0 - float(d)) for c, fn, d in rows]

    rows = db.execute(base).all()  # SQLite (tests/dev): rank in Python
    hits = [Hit(c.id, c.document_id, fn, c.page, c.content, _cosine(query_vec, c.embedding)) for c, fn in rows]
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:k]
