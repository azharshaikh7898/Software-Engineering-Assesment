from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Document, User
from ..models import Query as QueryRow
from ..qa import UpstreamError, answer_question, query_out
from ..ratelimit import enforce_rate_limit
from ..security import current_user

router = APIRouter(tags=["qa"])


class AskIn(BaseModel):
    question: str = Field(max_length=1000)
    document_ids: list[str] | None = Field(default=None, max_length=50)

    @field_validator("question")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("question is too short")
        return v


@router.post("/ask")
def ask(
    body: AskIn,
    user: User = Depends(current_user),
    _: None = Depends(enforce_rate_limit),
    db: Session = Depends(get_db),
):
    ids = list(dict.fromkeys(body.document_ids or []))
    if ids:
        owned = set(db.scalars(select(Document.id).where(Document.user_id == user.id, Document.id.in_(ids))))
        if owned != set(ids):
            raise HTTPException(404, "Document not found")  # same answer for "missing" and "someone else's"
    try:
        return answer_question(db, user, body.question, ids or None)
    except UpstreamError as exc:
        raise HTTPException(503, str(exc))


@router.get("/history")
def history(limit: int = 50, user: User = Depends(current_user), db: Session = Depends(get_db)):
    limit = max(1, min(limit, 200))
    rows = db.scalars(
        select(QueryRow).where(QueryRow.user_id == user.id).order_by(QueryRow.id.desc()).limit(limit)
    )
    return [query_out(q) for q in rows]
