from __future__ import annotations

from typing import Any

_MASK = "***"

_SENSITIVE_KEYS: frozenset[str] = frozenset({
    "password", "passwd", "pass",
    "secret", "secret_key",
    "token", "access_token", "refresh_token", "id_token",
    "auth_token", "bearer_token", "bearer",
    "jwt", "session_token", "session",
    "oauth_token", "client_secret", "client_token",
    "authorization", "auth",
    "api_key", "apikey",
    "private_key", "signing_key",
    "credential", "credentials",
    "credit_card", "card_number", "cvv", "cvc", "ssn", "pin",
})


def mask_sensitive(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if data is None:
        return None
    return _mask_dict(data)


def _mask_dict(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(key, str) and key.lower() in _SENSITIVE_KEYS:
            result[key] = _MASK
        elif isinstance(value, dict):
            result[key] = _mask_dict(value)
        elif isinstance(value, list):
            result[key] = _mask_list(value)
        else:
            result[key] = value
    return result


def _mask_list(items: list[Any]) -> list[Any]:
    return [
        _mask_dict(item) if isinstance(item, dict) else item
        for item in items
    ]
