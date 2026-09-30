from app.db import SessionLocal
from app.models import User


def signup(client, username="alice", password="password123"):
    return client.post("/auth/signup", json={"username": username, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_signup_then_me(client):
    r = signup(client)
    assert r.status_code == 201
    me = client.get("/auth/me", headers=bearer(r.json()["access_token"]))
    assert me.status_code == 200 and me.json()["username"] == "alice"


def test_password_is_hashed(client):
    signup(client)
    with SessionLocal() as db:
        user = db.query(User).one()
    assert user.password_hash != "password123"
    assert user.password_hash.startswith("$2")


def test_duplicate_username_is_case_insensitive(client):
    signup(client, "alice")
    assert signup(client, "Alice").status_code == 409


def test_login_success_and_wrong_password(client):
    signup(client)
    ok = client.post("/auth/login", json={"username": "alice", "password": "password123"})
    assert ok.status_code == 200 and "access_token" in ok.json()
    bad = client.post("/auth/login", json={"username": "alice", "password": "wrong-password"})
    assert bad.status_code == 401


def test_protected_route_needs_valid_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers=bearer("garbage")).status_code == 401


def test_short_password_rejected(client):
    assert signup(client, password="short").status_code == 422
