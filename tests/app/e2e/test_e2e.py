"""
E2E smoke tests — run against a fully started stack (docker-compose.ci.yml).
Each test hits real Postgres, LocalStack S3/SQS, and Redis through Nginx.
No mocks. Happy paths only — edge cases belong in integration tests.

Run:
    docker compose -f docker-compose.ci.yml up -d --wait
    pytest tests/app/e2e/
    docker compose -f docker-compose.ci.yml down
"""

import io


def test_health_check(http, base_url):
    res = http.get(f"{base_url}/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_auth_register_and_login(http, base_url):
    creds = {"email": "smoke-auth@ci-test.internal", "password": "SmokeAuth1!"}
    assert http.post(f"{base_url}/auth/register", json=creds).status_code == 201

    res = http.post(f"{base_url}/auth/login", json=creds)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data


def test_authenticated_request_accepted(http, base_url, auth_headers):
    res = http.get(f"{base_url}/events", headers=auth_headers)
    assert res.status_code == 200


def test_media_upload_and_get_presigned_url(http, base_url, auth_headers):
    res = http.post(
        f"{base_url}/media/upload",
        headers=auth_headers,
        files={"file": ("e2e.txt", io.BytesIO(b"e2e smoke content"), "text/plain")},
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data.get("media_id")
    assert data.get("url")

    url_res = http.get(f"{base_url}/media/{data['media_id']}/url", headers=auth_headers)
    assert url_res.status_code == 200
    assert url_res.json()["data"].get("url")


def test_publish_event(http, base_url, auth_headers):
    res = http.post(
        f"{base_url}/events",
        json={"type": "e2e.smoke", "payload": {"source": "ci"}},
        headers=auth_headers,
    )
    assert res.status_code == 202
    assert res.json()["data"].get("message_id")
