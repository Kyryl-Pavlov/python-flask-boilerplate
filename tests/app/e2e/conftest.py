import os

import pytest
import requests as _requests

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost/api/v1")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def http():
    session = _requests.Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
def auth_headers(http, base_url):
    """Register once for the session and return a valid Bearer header."""
    creds = {"email": "e2e-runner@ci-test.internal", "password": "E2eRunner1!"}
    http.post(f"{base_url}/auth/register", json=creds)
    res = http.post(f"{base_url}/auth/login", json=creds)
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
