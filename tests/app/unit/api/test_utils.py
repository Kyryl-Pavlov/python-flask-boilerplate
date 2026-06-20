from unittest.mock import MagicMock

import pytest
from flask import Flask

from app.api.utils.utils import rest_api_response
from app.logging.logger import AppLogger


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    return app


class TestRestApiResponse:
    def test_default_returns_200_success(self, app):
        with app.app_context():
            response, status = rest_api_response()
        assert status == 200
        body = response.get_json()
        assert body["success"] is True
        assert body["message"] == ""
        assert body["data"] == {}

    def test_failure_with_custom_status(self, app):
        with app.app_context():
            response, status = rest_api_response(
                success=False, message="Not found", status_code=404
            )
        assert status == 404
        body = response.get_json()
        assert body["success"] is False
        assert body["message"] == "Not found"

    def test_data_is_included_in_body(self, app):
        with app.app_context():
            response, _ = rest_api_response(data={"user_id": "abc"})
        assert response.get_json()["data"] == {"user_id": "abc"}

    def test_data_defaults_to_empty_dict_when_none(self, app):
        with app.app_context():
            response, _ = rest_api_response(data=None)
        assert response.get_json()["data"] == {}

    def test_500_status_code(self, app):
        with app.app_context():
            _, status = rest_api_response(success=False, status_code=500)
        assert status == 500

    def test_response_always_has_three_keys(self, app):
        with app.app_context():
            response, _ = rest_api_response()
        body = response.get_json()
        assert set(body.keys()) == {"success", "message", "data"}

    def test_logger_adapter_called_when_present(self, app):
        mock_adapter = MagicMock()
        app.logger_adapter = mock_adapter

        with app.app_context():
            rest_api_response(success=True, message="ok")

        mock_adapter.log.assert_called_once()
        _, kwargs = mock_adapter.log.call_args
        assert kwargs["level"] == AppLogger.Level.INFO

    def test_logger_adapter_uses_error_level_for_5xx(self, app):
        mock_adapter = MagicMock()
        app.logger_adapter = mock_adapter

        with app.app_context():
            rest_api_response(success=False, status_code=500)

        _, kwargs = mock_adapter.log.call_args
        assert kwargs["level"] == AppLogger.Level.ERROR

    def test_logger_adapter_uses_warn_level_for_4xx(self, app):
        mock_adapter = MagicMock()
        app.logger_adapter = mock_adapter

        with app.app_context():
            rest_api_response(success=False, status_code=400)

        _, kwargs = mock_adapter.log.call_args
        assert kwargs["level"] == AppLogger.Level.WARN
