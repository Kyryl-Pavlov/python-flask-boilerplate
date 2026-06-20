import json
from unittest.mock import MagicMock

import pytest

from app.services.cache_service import CacheService


@pytest.fixture
def redis_mock():
    return MagicMock()


@pytest.fixture
def cache(redis_mock):
    return CacheService(redis_mock)


class TestGet:
    def test_returns_deserialized_value(self, cache, redis_mock):
        redis_mock.get.return_value = json.dumps({"key": "val"})
        assert cache.get("mykey") == {"key": "val"}
        redis_mock.get.assert_called_once_with("mykey")

    def test_returns_none_when_key_missing(self, cache, redis_mock):
        redis_mock.get.return_value = None
        assert cache.get("missing") is None

    def test_deserializes_integer(self, cache, redis_mock):
        redis_mock.get.return_value = json.dumps(42)
        assert cache.get("num") == 42

    def test_deserializes_list(self, cache, redis_mock):
        redis_mock.get.return_value = json.dumps([1, 2, 3])
        assert cache.get("lst") == [1, 2, 3]


class TestSet:
    def test_calls_setex_with_serialized_value_and_ttl(self, cache, redis_mock):
        cache.set("k", {"a": 1}, ttl=30)
        redis_mock.setex.assert_called_once_with("k", 30, json.dumps({"a": 1}))

    def test_default_ttl_is_60(self, cache, redis_mock):
        cache.set("k", "val")
        assert redis_mock.setex.call_args[0][1] == 60

    def test_serializes_scalar(self, cache, redis_mock):
        cache.set("k", 123)
        assert redis_mock.setex.call_args[0][2] == json.dumps(123)


class TestDelete:
    def test_returns_true_when_key_existed(self, cache, redis_mock):
        redis_mock.delete.return_value = 1
        assert cache.delete("k") is True

    def test_returns_false_when_key_not_found(self, cache, redis_mock):
        redis_mock.delete.return_value = 0
        assert cache.delete("k") is False


class TestTTL:
    def test_returns_ttl_from_redis(self, cache, redis_mock):
        redis_mock.ttl.return_value = 42
        assert cache.ttl("k") == 42


class TestPing:
    def test_returns_true_on_success(self, cache, redis_mock):
        redis_mock.ping.return_value = True
        assert cache.ping() is True

    def test_returns_false_on_connection_error(self, cache, redis_mock):
        redis_mock.ping.side_effect = Exception("connection refused")
        assert cache.ping() is False
