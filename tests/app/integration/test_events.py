from unittest.mock import patch


class TestPublish:
    def test_no_auth_returns_401(self, client):
        res = client.post("/api/v1/events", json={"type": "test"})
        assert res.status_code == 401

    def test_missing_type_returns_400(self, client, auth_headers):
        res = client.post("/api/v1/events", json={}, headers=auth_headers)
        assert res.status_code == 400

    def test_success_returns_202_with_message_id(self, client, auth_headers):
        with patch("app.api.v1.events.send_event", return_value="msg-abc"):
            res = client.post(
                "/api/v1/events",
                json={"type": "order.created", "payload": {"order_id": 1}},
                headers=auth_headers,
            )
        assert res.status_code == 202
        assert res.get_json()["data"]["message_id"] == "msg-abc"

    def test_sqs_failure_returns_500(self, client, auth_headers):
        with patch("app.api.v1.events.send_event", side_effect=Exception("SQS down")):
            res = client.post(
                "/api/v1/events",
                json={"type": "test.event"},
                headers=auth_headers,
            )
        assert res.status_code == 500


class TestList:
    def test_no_auth_returns_401(self, client):
        assert client.get("/api/v1/events").status_code == 401

    def test_empty_returns_empty_list(self, client, auth_headers):
        res = client.get("/api/v1/events", headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()["data"] == []

    def test_returns_stored_events(self, client, auth_headers, app):
        from app.extensions import db
        from app.models.event import Event

        with app.app_context():
            db.session.add(
                Event(sqs_message_id="msg-001", type="user.created", status="processed")
            )
            db.session.commit()

        res = client.get("/api/v1/events", headers=auth_headers)
        data = res.get_json()["data"]
        assert len(data) == 1
        assert data[0]["sqs_message_id"] == "msg-001"
        assert data[0]["type"] == "user.created"
        assert data[0]["status"] == "processed"

    def test_response_contains_required_fields(self, client, auth_headers, app):
        from app.extensions import db
        from app.models.event import Event

        with app.app_context():
            db.session.add(
                Event(sqs_message_id="msg-002", type="ping", status="processed")
            )
            db.session.commit()

        data = client.get("/api/v1/events", headers=auth_headers).get_json()["data"][0]
        assert {
            "id",
            "sqs_message_id",
            "type",
            "payload",
            "status",
            "created_at",
            "processed_at",
        } <= data.keys()
