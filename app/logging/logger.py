from __future__ import annotations

import logging
import traceback
from enum import Enum
from typing import Any, Protocol

from app.logging.data_filter import mask_sensitive, sanitize_traceback


class LoggerProtocol(Protocol):
    def info(self, message: str, data: dict[str, Any] | None = None) -> None: ...
    def warning(self, message: str, data: dict[str, Any] | None = None) -> None: ...
    def error(
        self, message: str, data: dict[str, Any] | None = None, trace: str | None = None
    ) -> None: ...


class ConsoleLogger:
    """Logs to stdout. Level is DEBUG when the app runs in debug mode, WARNING otherwise."""

    def __init__(self, debug: bool = False, name: str = "app") -> None:
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )
            self._logger.addHandler(handler)
        self._logger.setLevel(logging.DEBUG if debug else logging.WARNING)

    def info(self, message: str, data: dict[str, Any] | None = None) -> None:
        self._logger.info(message if data is None else f"{message} | data={data}")

    def warning(self, message: str, data: dict[str, Any] | None = None) -> None:
        self._logger.warning(message if data is None else f"{message} | data={data}")

    def error(
        self, message: str, data: dict[str, Any] | None = None, trace: str | None = None
    ) -> None:
        parts = [message]
        if data is not None:
            parts.append(f"data={data}")
        if trace is not None:
            parts.append(f"\n{trace}")
        self._logger.error(" | ".join(parts))


class AppLogger:
    class Level(Enum):
        INFO = "info"
        WARN = "warn"
        ERROR = "error"

    def __init__(self, *loggers: LoggerProtocol) -> None:
        self._loggers = list(loggers)

    def log(
        self,
        message: str,
        level: AppLogger.Level = Level.INFO,
        data: dict[str, Any] | None = None,
        exc: BaseException | None = None,
    ) -> None:
        safe_data = mask_sensitive(data)
        match level:
            case AppLogger.Level.INFO:
                self.__info(message, safe_data)
            case AppLogger.Level.WARN:
                self.__warn(message, safe_data)
            case AppLogger.Level.ERROR:
                trace: str | None = None
                if exc is not None:
                    raw = "".join(
                        traceback.format_exception(type(exc), exc, exc.__traceback__)
                    )
                    trace = sanitize_traceback(raw)
                self.__error(message, safe_data, trace)

    def __info(self, message: str, data: dict[str, Any] | None) -> None:
        for logger in self._loggers:
            logger.info(message, data)

    def __warn(self, message: str, data: dict[str, Any] | None) -> None:
        for logger in self._loggers:
            logger.warning(message, data)

    def __error(
        self, message: str, data: dict[str, Any] | None, trace: str | None
    ) -> None:
        for logger in self._loggers:
            logger.error(message, data, trace)
