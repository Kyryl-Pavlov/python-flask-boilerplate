_REGISTER = """
mutation($email: String!, $password: String!) {
    register(email: $email, password: $password) {
        success
        message
    }
}
"""

_LOGIN = """
mutation($email: String!, $password: String!) {
    login(email: $email, password: $password) {
        success
        message
        data { accessToken refreshToken }
    }
}
"""

_REFRESH = """
mutation {
    refreshToken {
        success
        message
        data { accessToken }
    }
}
"""


class TestRegister:
    def test_success(self, gql):
        payload = gql(
            _REGISTER, {"email": "new@example.com", "password": "Pass123!"}
        ).get_json()["data"]["register"]
        assert payload["success"] is True

    def test_duplicate_email(self, gql):
        vars_ = {"email": "dup@example.com", "password": "Pass123!"}
        gql(_REGISTER, vars_)
        payload = gql(_REGISTER, vars_).get_json()["data"]["register"]
        assert payload["success"] is False
        assert "already registered" in payload["message"]

    def test_missing_password(self, gql):
        payload = gql(_REGISTER, {"email": "a@b.com", "password": ""}).get_json()[
            "data"
        ]["register"]
        assert payload["success"] is False

    def test_email_normalized_to_lowercase(self, gql, client):
        gql(_REGISTER, {"email": "Upper@Example.COM", "password": "Pass123!"})
        login = gql(
            _LOGIN, {"email": "upper@example.com", "password": "Pass123!"}
        ).get_json()["data"]["login"]
        assert login["success"] is True


class TestLogin:
    def test_success_returns_both_tokens(self, gql, registered_user):
        payload = gql(_LOGIN, registered_user).get_json()["data"]["login"]
        assert payload["success"] is True
        assert payload["data"]["accessToken"]
        assert payload["data"]["refreshToken"]

    def test_wrong_password(self, gql, registered_user):
        payload = gql(_LOGIN, {**registered_user, "password": "wrong"}).get_json()[
            "data"
        ]["login"]
        assert payload["success"] is False
        assert "Invalid credentials" in payload["message"]

    def test_unknown_email(self, gql):
        payload = gql(_LOGIN, {"email": "nobody@x.com", "password": "pass"}).get_json()[
            "data"
        ]["login"]
        assert payload["success"] is False


class TestRefreshToken:
    def test_success_returns_new_access_token(self, gql, gql_auth_headers):
        payload = gql(_REFRESH, headers=gql_auth_headers["refresh"]).get_json()["data"][
            "refreshToken"
        ]
        assert payload["success"] is True
        assert payload["data"]["accessToken"]

    def test_access_token_rejected(self, gql, gql_auth_headers):
        payload = gql(_REFRESH, headers=gql_auth_headers["access"]).get_json()["data"][
            "refreshToken"
        ]
        assert payload["success"] is False

    def test_no_token(self, gql):
        payload = gql(_REFRESH).get_json()["data"]["refreshToken"]
        assert payload["success"] is False
