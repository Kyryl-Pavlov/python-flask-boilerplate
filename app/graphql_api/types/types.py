
import strawberry
from typing import Generic, Optional, TypeVar

T = TypeVar('T')

@strawberry.type
class Response(Generic[T]):
    success: bool = True
    message: str = ''
    data: Optional[T] = None

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