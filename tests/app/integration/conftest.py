from unittest.mock import patch

import bcrypt as _bcrypt
import pytest
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="session", autouse=True)
def fast_bcrypt():
    """Replace bcrypt's 13-round salt with 4-round to keep tests fast."""
    _real_gensalt = _bcrypt.gensalt  # capture real fn before the patch replaces it
    with patch(
        "app.models.user.bcrypt.gensalt",
        side_effect=lambda rounds=12: _real_gensalt(rounds=4),
    ):
        yield


@pytest.fixture(scope="session")
def app(fast_bcrypt):
    from app import create_app
    from app.extensions import db as _db

    flask_app = create_app("testing")
    flask_app.config.update(
        {
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            },
            "JWT_SECRET_KEY": "test-jwt-secret-key-minimum-32-bytes!!",
            "SECRET_KEY": "test-secret-key-minimum-32-bytes!!!!",
            "REDIS_URL": None,
        }
    )

    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


@pytest.fixture(autouse=True)
def clean_tables(app):
    from app.extensions import db

    yield
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def registered_user(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "Password123!"},
    )
    return {"email": "user@example.com", "password": "Password123!"}


@pytest.fixture
def access_token(client, registered_user):
    res = client.post("/api/v1/auth/login", json=registered_user)
    return res.get_json()["data"]["access_token"]


@pytest.fixture
def refresh_token(client, registered_user):
    res = client.post("/api/v1/auth/login", json=registered_user)
    return res.get_json()["data"]["refresh_token"]


@pytest.fixture
def auth_headers(access_token):
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def mock_cache(app):
    """Attaches a MagicMock as app.cache; restores None after the test."""
    from unittest.mock import MagicMock

    m = MagicMock()
    app.cache = m
    yield m
    app.cache = None


@pytest.fixture
def gql(client):
    """Post a GraphQL query/mutation; returns the parsed response dict."""

    def _execute(
        query: str, variables: dict | None = None, headers: dict | None = None
    ):
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        return client.post("/graphql", json=payload, headers=headers or {})

    return _execute


@pytest.fixture
def gql_auth_headers(client, registered_user):
    """GraphQL auth via the GraphQL login mutation itself."""
    res = client.post(
        "/graphql",
        json={
            "query": """
                mutation($email: String!, $password: String!) {
                    login(email: $email, password: $password) {
                        data { accessToken refreshToken }
                    }
                }
            """,
            "variables": registered_user,
        },
    )
    tokens = res.get_json()["data"]["login"]["data"]
    return {
        "access": {"Authorization": f"Bearer {tokens['accessToken']}"},
        "refresh": {"Authorization": f"Bearer {tokens['refreshToken']}"},
    }
