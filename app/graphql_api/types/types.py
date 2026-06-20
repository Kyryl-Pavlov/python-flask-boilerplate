from typing import Generic, TypeVar

import strawberry
from flask import current_app
from strawberry.scalars import JSON  # noqa: F401 — re-exported for resolvers

from app.logging.logger import AppLogger

T = TypeVar("T")


@strawberry.type
class Response(Generic[T]):  # noqa: UP046
    success: bool = True
    message: str = ""
    data: T | None = None
    exc: strawberry.Private[BaseException | None] = None

    def __post_init__(self):
        if hasattr(current_app, "logger_adapter"):
            if self.success:
                level = AppLogger.Level.INFO
            elif self.exc is not None:
                level = AppLogger.Level.ERROR
            else:
                level = AppLogger.Level.WARN
            current_app.logger_adapter.log(self.message, level=level, exc=self.exc)


@strawberry.type
class HealthStatus:
    version: str


@strawberry.type
class AuthPayload:
    access_token: str
    refresh_token: str | None = None


@strawberry.type
class MediaPayload:
    media_id: str
    url: str
    expires_in: int


@strawberry.type
class CacheTestPayload:
    source: str  # "cache" | "computed"
    computed_at: float
    payload: str
    ttl: int | None = None
    remaining_ttl: int | None = None


@strawberry.type
class EventPayload:
    id: str
    sqs_message_id: str
    type: str
    payload: JSON | None = None
    status: str
    created_at: str
    processed_at: str | None = None
