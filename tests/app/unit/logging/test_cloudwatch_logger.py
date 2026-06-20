import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def cw_logger():
    from app.logging.cloudwatch_logger import CloudWatchLogger

    with (
        patch("app.logging.cloudwatch_logger.boto3") as mock_boto3,
        patch("app.logging.cloudwatch_logger.watchtower") as mock_watchtower,
    ):
        mock_boto3.client.return_value = MagicMock()
        mock_watchtower.CloudWatchLogHandler.return_value = MagicMock()
        yield CloudWatchLogger("test-group", "test-stream")


class TestCloudWatchLoggerSerialize:
    def test_minimal_output(self, cw_logger):
        result = json.loads(cw_logger._serialize("info", "hello", None))
        assert result == {"level": "info", "message": "hello"}

    def test_includes_data_when_provided(self, cw_logger):
        result = json.loads(cw_logger._serialize("warning", "warn", {"k": "v"}))
        assert result["data"] == {"k": "v"}

    def test_includes_trace_when_provided(self, cw_logger):
        result = json.loads(cw_logger._serialize("error", "err", None, "Traceback..."))
        assert result["trace"] == "Traceback..."

    def test_all_fields_present(self, cw_logger):
        result = json.loads(cw_logger._serialize("error", "msg", {"k": "v"}, "tb"))
        assert result == {
            "level": "error",
            "message": "msg",
            "data": {"k": "v"},
            "trace": "tb",
        }

    def test_omits_data_when_none(self, cw_logger):
        result = json.loads(cw_logger._serialize("info", "msg", None))
        assert "data" not in result

    def test_omits_trace_when_none(self, cw_logger):
        result = json.loads(cw_logger._serialize("info", "msg", None, None))
        assert "trace" not in result

    def test_output_is_valid_json(self, cw_logger):
        raw = cw_logger._serialize("info", "msg", {"a": 1}, "tb")
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)
