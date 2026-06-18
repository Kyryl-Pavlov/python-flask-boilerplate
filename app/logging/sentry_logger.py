from __future__ import annotations

from typing import Any

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration


class SentryLogger:
    """Routes log calls to Sentry. info/warn become breadcrumbs; errors become captured events."""

    def __init__(self, dsn: str, environment: str = "production", traces_sample_rate: float = 0.1) -> None:
        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration()],
            environment=environment,
            traces_sample_rate=traces_sample_rate,
        )

    def info(self, message: str, data: dict[str, Any] | None = None) -> None:
        sentry_sdk.add_breadcrumb(message=message, level="info", data=data or {})

    def warning(self, message: str, data: dict[str, Any] | None = None) -> None:
        sentry_sdk.add_breadcrumb(message=message, level="warning", data=data or {})

    def error(self, message: str, data: dict[str, Any] | None = None, trace: str | None = None) -> None:
        with sentry_sdk.new_scope() as scope:
            if data:
                scope.set_extra("data", data)
            if trace:
                scope.set_extra("trace", trace)
            sentry_sdk.capture_message(message, level="error")
