
import strawberry
from typing import Generic, Optional, TypeVar
from flask import current_app
from app.logging.logger import AppLogger

T = TypeVar('T')

@strawberry.type
class Response(Generic[T]):
    success: bool = True
    message: str = ''
    data: Optional[T] = None
    exc: strawberry.Private[Optional[BaseException]] = None

    def __post_init__(self):
        if hasattr(current_app, 'logger_adapter'):
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
    refresh_token: Optional[str] = None

@strawberry.type
class MediaPayload:
    media_id: str
    url: str
    expires_in: int