import json
from typing import Any

import redis


class CacheService:
    def __init__(self, client: redis.Redis):
        self._client = client

    def get(self, key: str) -> Any | None:
        raw = self._client.get(key)
        return json.loads(raw) if raw is not None else None

    def set(self, key: str, value: Any, ttl: int = 60) -> None:
        self._client.setex(key, ttl, json.dumps(value))

    def delete(self, key: str) -> bool:
        return bool(self._client.delete(key))

    def ttl(self, key: str) -> int:
        return self._client.ttl(key)

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except Exception:
            return False

    @classmethod
    def from_url(cls, url: str) -> "CacheService":
        return cls(redis.from_url(url, decode_responses=True))
