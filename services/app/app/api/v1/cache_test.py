import time

from flask import Blueprint, current_app

from app.api.utils.utils import rest_api_response

cache_test_bp = Blueprint("cache_test", __name__)

_CACHE_KEY = "poc:test_value"
_CACHE_TTL = 60  # seconds


@cache_test_bp.get("/cache/ping")
def cache_ping():
    cache = current_app.cache
    if cache is None:
        return rest_api_response(
            success=False, message="Redis not configured", status_code=503
        )
    return rest_api_response(data={"redis": "ok" if cache.ping() else "unavailable"})


@cache_test_bp.get("/cache/test")
def cache_get():
    cache = current_app.cache
    if cache is None:
        return rest_api_response(
            success=False, message="Redis not configured", status_code=503
        )

    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return rest_api_response(
            message="Cache hit",
            data={**cached, "source": "cache", "remaining_ttl": cache.ttl(_CACHE_KEY)},
        )

    value = {
        "computed_at": time.time(),
        "payload": "Simulated expensive computation result",
    }
    cache.set(_CACHE_KEY, value, ttl=_CACHE_TTL)
    return rest_api_response(
        message="Cache miss — value computed and stored",
        data={**value, "source": "computed", "ttl": _CACHE_TTL},
    )


@cache_test_bp.delete("/cache/test")
def cache_invalidate():
    cache = current_app.cache
    if cache is None:
        return rest_api_response(
            success=False, message="Redis not configured", status_code=503
        )

    deleted = cache.delete(_CACHE_KEY)
    return rest_api_response(
        message="Cache key deleted" if deleted else "Key was not in cache",
        data={"deleted": deleted},
    )
