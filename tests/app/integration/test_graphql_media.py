import io
import json
import uuid
from unittest.mock import patch

_SIGNED_URL = """
query($mediaId: String!) {
    signedUrl(mediaId: $mediaId) {
        success
        message
        data
    }
}
"""

_UPLOAD = """
mutation($file: Upload!) {
    uploadFile(file: $file) {
        success
        message
        data { mediaId url expiresIn }
    }
}
"""

_FAKE_KEY = "media/user/test.txt"
_FAKE_URL = "https://s3.example.com/signed"


def _upload_file(client, headers):
    """Post a multipart GraphQL upload; returns the parsed response."""
    operations = json.dumps(
        {
            "query": _UPLOAD,
            "variables": {"file": None},
        }
    )
    return client.post(
        "/graphql",
        data={
            "operations": operations,
            "map": json.dumps({"0": ["variables.file"]}),
            "0": (io.BytesIO(b"test content"), "test.txt"),
        },
        headers=headers,
        content_type="multipart/form-data",
    )


class TestSignedUrl:
    def test_no_auth_returns_unauthorized(self, gql):
        payload = gql(_SIGNED_URL, {"mediaId": str(uuid.uuid4())}).get_json()["data"][
            "signedUrl"
        ]
        assert payload["success"] is False
        assert "Unauthorized" in payload["message"]

    def test_invalid_uuid_returns_error(self, gql, gql_auth_headers):
        payload = gql(
            _SIGNED_URL, {"mediaId": "not-a-uuid"}, headers=gql_auth_headers["access"]
        ).get_json()["data"]["signedUrl"]
        assert payload["success"] is False
        assert "Invalid media ID" in payload["message"]

    def test_nonexistent_media_returns_not_found(self, gql, gql_auth_headers):
        payload = gql(
            _SIGNED_URL,
            {"mediaId": str(uuid.uuid4())},
            headers=gql_auth_headers["access"],
        ).get_json()["data"]["signedUrl"]
        assert payload["success"] is False
        assert "Not found" in payload["message"]

    def test_success_returns_url(self, client, gql, gql_auth_headers, app):
        with (
            patch(
                "app.graphql_api.resolvers.media.upload_file", return_value=_FAKE_KEY
            ),
            patch(
                "app.graphql_api.resolvers.media.get_presigned_url",
                return_value=_FAKE_URL,
            ),
        ):
            upload_res = _upload_file(client, gql_auth_headers["access"])
        media_id = upload_res.get_json()["data"]["uploadFile"]["data"]["mediaId"]

        with patch(
            "app.graphql_api.resolvers.media.get_presigned_url", return_value=_FAKE_URL
        ):
            payload = gql(
                _SIGNED_URL, {"mediaId": media_id}, headers=gql_auth_headers["access"]
            ).get_json()["data"]["signedUrl"]

        assert payload["success"] is True
        assert payload["data"] == _FAKE_URL

    def test_another_users_media_returns_not_found(self, client, gql):
        # User 1 uploads
        client.post(
            "/graphql",
            json={
                "query": 'mutation { register(email: "u1@x.com", password: "Pass1!") { success } }'
            },
        )
        login1 = client.post(
            "/graphql",
            json={
                "query": 'mutation { login(email: "u1@x.com", password: "Pass1!") { data { accessToken } } }'
            },
        )
        headers1 = {
            "Authorization": f"Bearer {login1.get_json()['data']['login']['data']['accessToken']}"
        }

        with (
            patch(
                "app.graphql_api.resolvers.media.upload_file", return_value=_FAKE_KEY
            ),
            patch(
                "app.graphql_api.resolvers.media.get_presigned_url",
                return_value=_FAKE_URL,
            ),
        ):
            media_id = _upload_file(client, headers1).get_json()["data"]["uploadFile"][
                "data"
            ]["mediaId"]

        # User 2 tries to access it
        client.post(
            "/graphql",
            json={
                "query": 'mutation { register(email: "u2@x.com", password: "Pass2!") { success } }'
            },
        )
        login2 = client.post(
            "/graphql",
            json={
                "query": 'mutation { login(email: "u2@x.com", password: "Pass2!") { data { accessToken } } }'
            },
        )
        headers2 = {
            "Authorization": f"Bearer {login2.get_json()['data']['login']['data']['accessToken']}"
        }

        payload = gql(_SIGNED_URL, {"mediaId": media_id}, headers=headers2).get_json()[
            "data"
        ]["signedUrl"]
        assert payload["success"] is False
        assert "Not found" in payload["message"]


class TestUploadFile:
    def test_no_auth_returns_unauthorized(self, client):
        res = _upload_file(client, {})
        payload = res.get_json()["data"]["uploadFile"]
        assert payload["success"] is False
        assert "Unauthorized" in payload["message"]

    def test_success_returns_media_payload(self, client, gql_auth_headers):
        with (
            patch(
                "app.graphql_api.resolvers.media.upload_file", return_value=_FAKE_KEY
            ),
            patch(
                "app.graphql_api.resolvers.media.get_presigned_url",
                return_value=_FAKE_URL,
            ),
        ):
            payload = _upload_file(client, gql_auth_headers["access"]).get_json()[
                "data"
            ]["uploadFile"]

        assert payload["success"] is True
        assert payload["data"]["mediaId"]
        assert payload["data"]["url"] == _FAKE_URL

    def test_s3_failure_returns_error(self, client, gql_auth_headers):
        with patch(
            "app.graphql_api.resolvers.media.upload_file",
            side_effect=Exception("S3 down"),
        ):
            payload = _upload_file(client, gql_auth_headers["access"]).get_json()[
                "data"
            ]["uploadFile"]
        assert payload["success"] is False
        assert "upload failed" in payload["message"]
