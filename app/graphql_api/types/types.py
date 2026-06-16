
import strawberry
from typing import Generic, Optional, TypeVar

T = TypeVar('T')

@strawberry.type
class HealthStatus:
    version: str

@strawberry.type
class Response(Generic[T]):
    status: str
    message: str
    data: Optional[T]