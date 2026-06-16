import io
import uuid
from unittest.mock import patch

_FAKE_S3_KEY = "media/user-id/test.txt"
_FAKE_URL = "https://s3.example.com/signed-url"


def _upload(client, headers, content=b"hello", filename="test.png"):
    """Helper: POST a file upload with mocked S3."""
    with (
        patch("app.api.v1.media.upload_file", return_value=_FAKE_S3_KEY),
        patch("app.api.v1.media.get_presigned_url", return_value=_FAKE_URL),
    ):
        return client.post(
            "/api/v1/media/upload",
            headers=headers,
            data={"file": (io.BytesIO(content), filename)},
            content_type="multipart/form-data",
        )


class TestUpload:
    def test_no_auth_returns_401(self, client):
        res = client.post("/api/v1/media/upload")
        assert res.status_code == 401

    def test_no_file_returns_400(self, client, auth_headers):
        res = client.post("/api/v1/media/upload", headers=auth_headers, data={})
        assert res.status_code == 400

    def test_success_returns_201_with_media_id_and_url(self, client, auth_headers):
        res = _upload(client, auth_headers)
        assert res.status_code == 201
        data = res.get_json()["data"]
        assert "media_id" in data
        assert data["url"] == _FAKE_URL

    def test_media_record_persisted_in_db(self, client, auth_headers, app):
        from app.extensions import db
        from app.models.media import Media

        res = _upload(client, auth_headers)
        media_id = res.get_json()["data"]["media_id"]

        with app.app_context():
            record = db.session.get(Media, uuid.UUID(media_id))
        assert record is not None
        assert record.content_key == _FAKE_S3_KEY

    def test_s3_failure_returns_500(self, client, auth_headers):
        with patch("app.api.v1.media.upload_file", side_effect=Exception("S3 down")):
            res = client.post(
                "/api/v1/media/upload",
                headers=auth_headers,
                data={"file": (io.BytesIO(b"data"), "f.png")},
                content_type="multipart/form-data",
            )
        assert res.status_code == 500


class TestGetUrl:
    def test_no_auth_returns_401(self, client):
        res = client.get(f"/api/v1/media/{uuid.uuid4()}/url")
        assert res.status_code == 401

    def test_invalid_uuid_returns_400(self, client, auth_headers):
        res = client.get("/api/v1/media/not-a-uuid/url", headers=auth_headers)
        assert res.status_code == 400

    def test_nonexistent_media_returns_404(self, client, auth_headers):
        res = client.get(f"/api/v1/media/{uuid.uuid4()}/url", headers=auth_headers)
        assert res.status_code == 404

    def test_success_returns_presigned_url(self, client, auth_headers):
        media_id = _upload(client, auth_headers).get_json()["data"]["media_id"]

        with patch("app.api.v1.media.get_presigned_url", return_value=_FAKE_URL):
            res = client.get(f"/api/v1/media/{media_id}/url", headers=auth_headers)

        assert res.status_code == 200
        assert res.get_json()["data"]["url"] == _FAKE_URL

    def test_another_users_media_returns_404(self, client):
        client.post(
            "/api/v1/auth/register", json={"email": "u1@x.com", "password": "Pass1!"}
        )
        client.post(
            "/api/v1/auth/register", json={"email": "u2@x.com", "password": "Pass2!"}
        )

        token1 = client.post(
            "/api/v1/auth/login", json={"email": "u1@x.com", "password": "Pass1!"}
        ).get_json()["data"]["access_token"]
        token2 = client.post(
            "/api/v1/auth/login", json={"email": "u2@x.com", "password": "Pass2!"}
        ).get_json()["data"]["access_token"]

        media_id = _upload(client, {"Authorization": f"Bearer {token1}"}).get_json()[
            "data"
        ]["media_id"]

        res = client.get(
            f"/api/v1/media/{media_id}/url",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert res.status_code == 404
