def test_ui_is_served_and_api_routes_still_win(client):
    r = client.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"] and "DocuMind" in r.text
    assert client.get("/docs").status_code == 200
    assert client.get("/livez").status_code == 200
    assert client.get("/documents").status_code == 401  # API route, not swallowed by the static mount
