from sqlalchemy import func, select

from app.config import settings
from app.db import SessionLocal
from app.ingest import ingest_document
from app.models import Chunk
from app.routes import documents

TEXT = b"Refunds are processed within 14 days.\n\nShipping takes 3 to 5 business days."


def make_pdf(pages: list[str]) -> bytes:
    objs = {
        1: "<< /Type /Catalog /Pages 2 0 R >>",
        2: "<< /Type /Pages /Kids [%s] /Count %d >>"
        % (" ".join(f"{4 + 2 * i} 0 R" for i in range(len(pages))), len(pages)),
        3: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for i, text in enumerate(pages):
        page_id, content_id = 4 + 2 * i, 5 + 2 * i
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
        objs[page_id] = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_id} 0 R /Resources << /Font << /F1 3 0 R >> >> >>"
        )
        objs[content_id] = f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"
    out, offsets = b"%PDF-1.4\n", {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n{objs[num]}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for num in sorted(objs):
        out += f"{offsets[num]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def upload(client, headers, name="policy.txt", data=TEXT):
    return client.post("/documents", headers=headers, files={"file": (name, data)})


def chunk_count(doc_id=None) -> int:
    q = select(func.count()).select_from(Chunk)
    if doc_id:
        q = q.where(Chunk.document_id == doc_id)
    with SessionLocal() as db:
        return db.scalar(q)


def test_upload_is_ingested_and_becomes_ready(client, make_user):
    h = make_user("alice")
    r = upload(client, h)
    assert r.status_code == 202
    doc = client.get(f"/documents/{r.json()['id']}", headers=h).json()
    assert doc["status"] == "ready" and doc["error"] is None
    assert chunk_count(doc["id"]) >= 1


def test_status_is_queued_until_worker_runs(client, make_user, monkeypatch):
    monkeypatch.setattr(documents, "enqueue_ingest", lambda doc_id: None)
    h = make_user("alice")
    doc_id = upload(client, h).json()["id"]
    assert client.get(f"/documents/{doc_id}", headers=h).json()["status"] == "queued"
    ingest_document(doc_id)  # what the worker does
    assert client.get(f"/documents/{doc_id}", headers=h).json()["status"] == "ready"


def test_pdf_chunks_carry_page_numbers(client, make_user):
    h = make_user("alice")
    pdf = make_pdf(["Refunds take 14 days", "Shipping takes 5 days"])
    doc_id = upload(client, h, "policy.pdf", pdf).json()["id"]
    assert client.get(f"/documents/{doc_id}", headers=h).json()["status"] == "ready"
    with SessionLocal() as db:
        rows = db.execute(select(Chunk.page, Chunk.content).order_by(Chunk.idx)).all()
    assert [p for p, _ in rows] == [1, 2]
    assert "Refunds" in rows[0][1] and "Shipping" in rows[1][1]


def test_unreadable_document_is_marked_failed_with_reason(client, make_user):
    h = make_user("alice")
    doc_id = upload(client, h, "blank.txt", b"   \n\n  ").json()["id"]
    doc = client.get(f"/documents/{doc_id}", headers=h).json()
    assert doc["status"] == "failed" and "No extractable text" in doc["error"]


def test_rejects_bad_uploads(client, make_user, monkeypatch):
    h = make_user("alice")
    assert upload(client, h, "run.exe", b"data").status_code == 415
    assert upload(client, h, "empty.txt", b"").status_code == 400
    assert upload(client, h, "fake.pdf", b"not a pdf").status_code == 400
    monkeypatch.setattr(settings, "max_upload_mb", 0)
    assert upload(client, h).status_code == 413


def test_per_user_document_limit(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "max_docs_per_user", 1)
    h = make_user("alice")
    assert upload(client, h).status_code == 202
    assert upload(client, h).status_code == 409


def test_queue_failure_returns_503_and_marks_failed(client, make_user, monkeypatch):
    def boom(doc_id):
        raise ConnectionError("redis down")

    monkeypatch.setattr(documents, "enqueue_ingest", boom)
    h = make_user("alice")
    assert upload(client, h).status_code == 503
    listed = client.get("/documents", headers=h).json()
    assert listed[0]["status"] == "failed"


def test_ingestion_is_idempotent_and_ignores_deleted_docs(client, make_user):
    h = make_user("alice")
    doc_id = upload(client, h).json()["id"]
    before = chunk_count(doc_id)
    ingest_document(doc_id)
    assert chunk_count(doc_id) == before
    ingest_document("does-not-exist")  # must not raise


def test_delete_removes_document_and_chunks(client, make_user):
    h = make_user("alice")
    doc_id = upload(client, h).json()["id"]
    assert chunk_count(doc_id) > 0
    assert client.delete(f"/documents/{doc_id}", headers=h).status_code == 204
    assert chunk_count(doc_id) == 0
    assert client.get(f"/documents/{doc_id}", headers=h).status_code == 404


def test_user_cannot_access_another_users_documents(client, make_user):
    alice, bob = make_user("alice"), make_user("bobby")
    doc_id = upload(client, alice).json()["id"]
    assert client.get("/documents", headers=bob).json() == []
    assert client.get(f"/documents/{doc_id}", headers=bob).status_code == 404
    assert client.delete(f"/documents/{doc_id}", headers=bob).status_code == 404
    assert chunk_count(doc_id) > 0  # bob's delete attempt changed nothing
    assert client.get(f"/documents/{doc_id}", headers=alice).status_code == 200


def test_documents_require_auth(client):
    assert client.get("/documents").status_code == 401
    assert client.post("/documents", files={"file": ("a.txt", b"x")}).status_code == 401
