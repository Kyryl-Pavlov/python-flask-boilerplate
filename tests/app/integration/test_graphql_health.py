_QUERY = """
query {
    health {
        success
        message
        data { version }
    }
}
"""


def test_health_returns_success(gql):
    res = gql(_QUERY)
    assert res.status_code == 200
    payload = res.get_json()["data"]["health"]
    assert payload["success"] is True


def test_health_returns_version(gql):
    payload = gql(_QUERY).get_json()["data"]["health"]
    assert payload["data"]["version"] is not None


def test_health_returns_message(gql):
    payload = gql(_QUERY).get_json()["data"]["health"]
    assert payload["message"] != ""
