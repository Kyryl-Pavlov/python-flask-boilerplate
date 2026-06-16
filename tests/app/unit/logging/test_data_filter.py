from app.logging.data_filter import mask_sensitive


def test_returns_none_for_none_input():
    assert mask_sensitive(None) is None


def test_empty_dict_unchanged():
    assert mask_sensitive({}) == {}


def test_masks_password():
    assert mask_sensitive({"password": "secret123"}) == {"password": "***"}


def test_case_insensitive_masking():
    result = mask_sensitive({"PASSWORD": "s3cr3t", "Token": "abc"})
    assert result == {"PASSWORD": "***", "Token": "***"}


def test_preserves_non_sensitive_keys():
    data = {"username": "alice", "email": "a@example.com"}
    assert mask_sensitive(data) == data


def test_masks_multiple_sensitive_keys():
    result = mask_sensitive(
        {"user": "alice", "password": "s3cr3t", "token": "abc", "api_key": "key"}
    )
    assert result == {
        "user": "alice",
        "password": "***",
        "token": "***",
        "api_key": "***",
    }


def test_nested_dict_masking():
    result = mask_sensitive({"outer": {"password": "hidden", "name": "alice"}})
    assert result == {"outer": {"password": "***", "name": "alice"}}


def test_deeply_nested_masking():
    result = mask_sensitive({"level1": {"level2": {"secret": "deep"}}})
    assert result == {"level1": {"level2": {"secret": "***"}}}


def test_list_input_masks_dicts_inside():
    result = mask_sensitive([{"password": "x"}, {"name": "bob"}])
    assert result == [{"password": "***"}, {"name": "bob"}]


def test_list_preserves_non_dict_items():
    data = [1, "string", None, 3.14]
    assert mask_sensitive(data) == data


def test_list_inside_dict():
    result = mask_sensitive({"users": [{"password": "pw1"}, {"password": "pw2"}]})
    assert result == {"users": [{"password": "***"}, {"password": "***"}]}


def test_does_not_mutate_original():
    original = {"password": "original"}
    mask_sensitive(original)
    assert original["password"] == "original"


def test_known_sensitive_keys_are_masked():
    sensitive_keys = [
        "secret",
        "access_token",
        "refresh_token",
        "api_key",
        "authorization",
        "jwt",
        "ssn",
        "cvv",
    ]
    for key in sensitive_keys:
        result = mask_sensitive({key: "value"})
        assert result[key] == "***", f"Expected {key!r} to be masked"
