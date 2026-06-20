_PING = """
query {
    cachePing {
        success
        message
        data
    }
}
"""

_TEST = """
query {
    cacheTest {
        success
        message
        data { source computedAt payload ttl remainingTtl }
    }
}
"""

_CLEAR = """
mutation {
    clearCache {
        success
        message
        data
    }
}
"""


class TestCachePing:
    def test_no_redis_configured(self, gql):
        payload = gql(_PING).get_json()["data"]["cachePing"]
        assert payload["success"] is False
        assert "not configured" in payload["message"]

    def test_redis_healthy(self, gql, mock_cache):
        mock_cache.ping.return_value = True
        payload = gql(_PING).get_json()["data"]["cachePing"]
        assert payload["success"] is True
        assert payload["data"] == "ok"

    def test_redis_unreachable(self, gql, mock_cache):
        mock_cache.ping.return_value = False
        payload = gql(_PING).get_json()["data"]["cachePing"]
        assert payload["success"] is True
        assert payload["data"] == "unavailable"


class TestCacheTest:
    def test_no_redis_configured(self, gql):
        payload = gql(_TEST).get_json()["data"]["cacheTest"]
        assert payload["success"] is False

    def test_cache_miss_computes_value(self, gql, mock_cache):
        mock_cache.get.return_value = None
        payload = gql(_TEST).get_json()["data"]["cacheTest"]
        assert payload["success"] is True
        assert payload["data"]["source"] == "computed"
        assert payload["data"]["computedAt"] is not None
        mock_cache.set.assert_called_once()

    def test_cache_hit_returns_cached_value(self, gql, mock_cache):
        mock_cache.get.return_value = {
            "computed_at": 1234567890.0,
            "payload": "Simulated expensive computation result",
        }
        mock_cache.ttl.return_value = 30
        payload = gql(_TEST).get_json()["data"]["cacheTest"]
        assert payload["success"] is True
        assert payload["data"]["source"] == "cache"
        assert payload["data"]["remainingTtl"] == 30
        mock_cache.set.assert_not_called()


class TestClearCache:
    def test_no_redis_configured(self, gql):
        payload = gql(_CLEAR).get_json()["data"]["clearCache"]
        assert payload["success"] is False

    def test_key_deleted(self, gql, mock_cache):
        mock_cache.delete.return_value = True
        payload = gql(_CLEAR).get_json()["data"]["clearCache"]
        assert payload["success"] is True
        assert payload["data"] is True

    def test_key_not_present(self, gql, mock_cache):
        mock_cache.delete.return_value = False
        payload = gql(_CLEAR).get_json()["data"]["clearCache"]
        assert payload["success"] is True
        assert payload["data"] is False
