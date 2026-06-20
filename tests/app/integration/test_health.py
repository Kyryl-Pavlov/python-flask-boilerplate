def test_returns_ok_status(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "ok"
    assert "version" in body
