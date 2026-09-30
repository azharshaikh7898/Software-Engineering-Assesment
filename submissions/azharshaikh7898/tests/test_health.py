from app.routes import health


def test_health_all_ok(client, monkeypatch):
    monkeypatch.setattr(health, "CHECKS", {"database": lambda: "ok", "queue": lambda: "ok"})
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_health_reports_down_dependency(client, monkeypatch):
    def boom():
        raise RuntimeError("redis unreachable")

    monkeypatch.setattr(health, "CHECKS", {"database": lambda: "ok", "queue": boom})
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["checks"]["queue"]["status"] == "down"


def test_request_id_header_is_returned(client):
    r = client.get("/livez", headers={"X-Request-ID": "abc123"})
    assert r.headers["X-Request-ID"] == "abc123"
