import hashlib
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_documind.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["QUEUE_SYNC"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import embeddings  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import EMBEDDING_DIM  # noqa: E402


def fake_vector(text: str) -> list[float]:
    """Deterministic bag-of-words embedding so tests need no model download."""
    vec = [0.0] * EMBEDDING_DIM
    for word in text.lower().split():
        vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % EMBEDDING_DIM] += 1.0
    return vec


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    monkeypatch.setattr(embeddings, "embed_documents", lambda texts: [fake_vector(t) for t in texts])
    monkeypatch.setattr(embeddings, "embed_query", fake_vector)


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def make_user(client):
    def _make(username: str) -> dict:
        r = client.post("/auth/signup", json={"username": username, "password": "password123"})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _make
