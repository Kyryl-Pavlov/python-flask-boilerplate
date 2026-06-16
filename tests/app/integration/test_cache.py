class TestCachePing:
    def test_no_redis_configured_returns_503(self, client):
        res = client.get("/api/v1/cache/ping")
        assert res.status_code == 503

    def test_redis_healthy_returns_ok(self, client, mock_cache):
        mock_cache.ping.return_value = True
        res = client.get("/api/v1/cache/ping")
        assert res.status_code == 200
        assert res.get_json()["data"]["redis"] == "ok"

    def test_redis_unreachable_returns_unavailable(self, client, mock_cache):
        mock_cache.ping.return_value = False
        res = client.get("/api/v1/cache/ping")
        assert res.status_code == 200
        assert res.get_json()["data"]["redis"] == "unavailable"


class TestCacheGet:
    def test_no_redis_configured_returns_503(self, client):
        res = client.get("/api/v1/cache/test")
        assert res.status_code == 503

    def test_cache_miss_computes_and_stores_value(self, client, mock_cache):
        mock_cache.get.return_value = None

        res = client.get("/api/v1/cache/test")

        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["source"] == "computed"
        assert "computed_at" in data
        mock_cache.set.assert_called_once()

    def test_cache_hit_returns_cached_value(self, client, mock_cache):
        cached_value = {
            "computed_at": 1234567890.0,
            "payload": "Simulated expensive computation result",
        }
        mock_cache.get.return_value = cached_value
        mock_cache.ttl.return_value = 42

        res = client.get("/api/v1/cache/test")

        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["source"] == "cache"
        assert data["remaining_ttl"] == 42
        mock_cache.set.assert_not_called()


class TestCacheInvalidate:
    def test_no_redis_configured_returns_503(self, client):
        res = client.delete("/api/v1/cache/test")
        assert res.status_code == 503

    def test_deletes_existing_key(self, client, mock_cache):
        mock_cache.delete.return_value = True
        res = client.delete("/api/v1/cache/test")
        assert res.status_code == 200
        assert res.get_json()["data"]["deleted"] is True

    def test_key_not_present_returns_false(self, client, mock_cache):
        mock_cache.delete.return_value = False
        res = client.delete("/api/v1/cache/test")
        assert res.status_code == 200
        assert res.get_json()["data"]["deleted"] is False
