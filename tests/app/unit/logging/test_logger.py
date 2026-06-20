from unittest.mock import MagicMock, patch

import pytest

from app.logging.logger import AppLogger, ConsoleLogger


class TestConsoleLogger:
    def test_info_without_data(self):
        logger = ConsoleLogger(debug=True, name="test_info_no_data")
        with patch.object(logger._logger, "info") as mock_info:
            logger.info("hello")
            mock_info.assert_called_once_with("hello")

    def test_info_with_data(self):
        logger = ConsoleLogger(debug=True, name="test_info_data")
        with patch.object(logger._logger, "info") as mock_info:
            logger.info("hello", {"key": "val"})
            mock_info.assert_called_once_with("hello | data={'key': 'val'}")

    def test_warning_without_data(self):
        logger = ConsoleLogger(debug=True, name="test_warning_no_data")
        with patch.object(logger._logger, "warning") as mock_warn:
            logger.warning("warn msg")
            mock_warn.assert_called_once_with("warn msg")

    def test_warning_with_data(self):
        logger = ConsoleLogger(debug=True, name="test_warning_data")
        with patch.object(logger._logger, "warning") as mock_warn:
            logger.warning("warn msg", {"k": "v"})
            mock_warn.assert_called_once_with("warn msg | data={'k': 'v'}")

    def test_error_without_data(self):
        logger = ConsoleLogger(debug=True, name="test_error_no_data")
        with patch.object(logger._logger, "error") as mock_error:
            logger.error("err msg")
            mock_error.assert_called_once_with("err msg")

    def test_error_with_data_and_trace(self):
        logger = ConsoleLogger(debug=True, name="test_error_full")
        with patch.object(logger._logger, "error") as mock_error:
            logger.error("err msg", {"k": "v"}, "Traceback (most recent call last)...")
            call_arg = mock_error.call_args[0][0]
            assert "err msg" in call_arg
            assert "data=" in call_arg
            assert "Traceback" in call_arg


class TestAppLogger:
    @pytest.fixture
    def mock_logger(self):
        m = MagicMock()
        m.info = MagicMock()
        m.warning = MagicMock()
        m.error = MagicMock()
        return m

    def test_info_level_calls_info(self, mock_logger):
        AppLogger(mock_logger).log("msg", level=AppLogger.Level.INFO)
        mock_logger.info.assert_called_once_with("msg", None)

    def test_warn_level_calls_warning(self, mock_logger):
        AppLogger(mock_logger).log("msg", level=AppLogger.Level.WARN)
        mock_logger.warning.assert_called_once_with("msg", None)

    def test_error_level_calls_error(self, mock_logger):
        AppLogger(mock_logger).log("msg", level=AppLogger.Level.ERROR)
        mock_logger.error.assert_called_once_with("msg", None, None)

    def test_masks_sensitive_data_before_dispatch(self, mock_logger):
        AppLogger(mock_logger).log(
            "login",
            level=AppLogger.Level.INFO,
            data={"password": "s3cr3t", "user": "alice"},
        )
        _, dispatched_data = mock_logger.info.call_args[0]
        assert dispatched_data["password"] == "***"
        assert dispatched_data["user"] == "alice"

    def test_fans_out_to_multiple_loggers(self):
        m1, m2 = MagicMock(), MagicMock()
        AppLogger(m1, m2).log("broadcast", level=AppLogger.Level.INFO)
        m1.info.assert_called_once()
        m2.info.assert_called_once()

    def test_error_with_exception_includes_traceback(self, mock_logger):
        try:
            raise ValueError("boom")
        except ValueError as exc:
            AppLogger(mock_logger).log("err", level=AppLogger.Level.ERROR, exc=exc)

        _, _, trace = mock_logger.error.call_args[0]
        assert trace is not None
        assert "ValueError" in trace
        assert "boom" in trace

    def test_error_without_exception_trace_is_none(self, mock_logger):
        AppLogger(mock_logger).log("err", level=AppLogger.Level.ERROR)
        _, _, trace = mock_logger.error.call_args[0]
        assert trace is None

    def test_data_none_passed_through_unchanged(self, mock_logger):
        AppLogger(mock_logger).log("msg", level=AppLogger.Level.INFO, data=None)
        _, dispatched_data = mock_logger.info.call_args[0]
        assert dispatched_data is None
