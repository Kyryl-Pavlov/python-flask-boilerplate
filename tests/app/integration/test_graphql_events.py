from unittest.mock import patch

_EVENTS = """
query {
    events {
        success
        message
        data { id sqsMessageId type status createdAt processedAt }
    }
}
"""

_PUBLISH = """
mutation($type: String!, $payload: JSON) {
    publishEvent(type: $type, payload: $payload) {
        success
        message
        data
    }
}
"""


class TestEvents:
    def test_no_auth_returns_unauthorized(self, gql):
        payload = gql(_EVENTS).get_json()["data"]["events"]
        assert payload["success"] is False
        assert "Unauthorized" in payload["message"]

    def test_empty_returns_empty_list(self, gql, gql_auth_headers):
        payload = gql(_EVENTS, headers=gql_auth_headers["access"]).get_json()["data"][
            "events"
        ]
        assert payload["success"] is True
        assert payload["data"] == []

    def test_returns_stored_events(self, gql, gql_auth_headers, app):
        from app.extensions import db
        from app.models.event import Event

        with app.app_context():
            db.session.add(
                Event(sqs_message_id="msg-gql-01", type="gql.test", status="processed")
            )
            db.session.commit()

        payload = gql(_EVENTS, headers=gql_auth_headers["access"]).get_json()["data"][
            "events"
        ]
        assert payload["success"] is True
        assert len(payload["data"]) == 1
        event = payload["data"][0]
        assert event["sqsMessageId"] == "msg-gql-01"
        assert event["type"] == "gql.test"
        assert event["status"] == "processed"
        assert event["createdAt"] is not None
        assert event["processedAt"] is None


class TestPublishEvent:
    def test_no_auth_returns_unauthorized(self, gql):
        payload = gql(_PUBLISH, {"type": "test"}).get_json()["data"]["publishEvent"]
        assert payload["success"] is False
        assert "Unauthorized" in payload["message"]

    def test_empty_type_returns_error(self, gql, gql_auth_headers):
        payload = gql(
            _PUBLISH, {"type": "  "}, headers=gql_auth_headers["access"]
        ).get_json()["data"]["publishEvent"]
        assert payload["success"] is False
        assert "required" in payload["message"]

    def test_success_returns_message_id(self, gql, gql_auth_headers):
        with patch(
            "app.graphql_api.resolvers.events.send_event", return_value="msg-xyz"
        ):
            payload = gql(
                _PUBLISH,
                {"type": "order.placed", "payload": {"id": 1}},
                headers=gql_auth_headers["access"],
            ).get_json()["data"]["publishEvent"]
        assert payload["success"] is True
        assert payload["data"] == "msg-xyz"

    def test_sqs_failure_returns_error(self, gql, gql_auth_headers):
        with patch(
            "app.graphql_api.resolvers.events.send_event",
            side_effect=Exception("SQS down"),
        ):
            payload = gql(
                _PUBLISH, {"type": "test.event"}, headers=gql_auth_headers["access"]
            ).get_json()["data"]["publishEvent"]
        assert payload["success"] is False
        assert "Failed to publish" in payload["message"]
