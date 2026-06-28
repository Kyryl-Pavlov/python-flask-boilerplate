import time

import strawberry
from flask import current_app

from app.graphql_api.types.types import CacheTestPayload, Response

_CACHE_KEY = "poc:test_value"
_CACHE_TTL = 60  # seconds


@strawberry.type
class CacheTestQueries:
    @strawberry.field
    def cache_ping(self) -> Response[str]:
        cache = current_app.cache
        if cache is None:
            return Response(success=False, message="Redis not configured")
        return Response(data="ok" if cache.ping() else "unavailable")

    @strawberry.field
    def cache_test(self) -> Response[CacheTestPayload]:
        cache = current_app.cache
        if cache is None:
            return Response(success=False, message="Redis not configured")

        cached = cache.get(_CACHE_KEY)
        if cached is not None:
            return Response(
                message="Cache hit",
                data=CacheTestPayload(
                    source="cache",
                    computed_at=cached["computed_at"],
                    payload=cached["payload"],
                    remaining_ttl=cache.ttl(_CACHE_KEY),
                ),
            )

        value = {
            "computed_at": time.time(),
            "payload": "Simulated expensive computation result",
        }
        cache.set(_CACHE_KEY, value, ttl=_CACHE_TTL)
        return Response(
            message="Cache miss — value computed and stored",
            data=CacheTestPayload(
                source="computed",
                computed_at=value["computed_at"],
                payload=value["payload"],
                ttl=_CACHE_TTL,
            ),
        )


@strawberry.type
class CacheTestMutations:
    @strawberry.mutation
    def clear_cache(self) -> Response[bool]:
        cache = current_app.cache
        if cache is None:
            return Response(success=False, message="Redis not configured")

        deleted = cache.delete(_CACHE_KEY)
        return Response(
            message="Cache key deleted" if deleted else "Key was not in cache",
            data=deleted,
        )
