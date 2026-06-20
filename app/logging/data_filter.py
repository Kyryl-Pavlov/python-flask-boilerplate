from __future__ import annotations

import re
from typing import Any

_MASK = "***"

# SQLAlchemy wraps the raw query and bound parameters in these blocks.
# psycopg2/asyncpg may also embed connection strings in error messages.
_SQL_BLOCK = re.compile(r"\[SQL:.*?\]", re.DOTALL)
_PARAMS_BLOCK = re.compile(r"\[parameters:.*?\]", re.DOTALL)
_DB_CONNSTR = re.compile(
    r"\b(postgresql|mysql|sqlite|mongodb|redis)(\+\w+)?://\S+",
    re.IGNORECASE,
)

_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "pass",
        "secret",
        "secret_key",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "auth_token",
        "bearer_token",
        "bearer",
        "jwt",
        "session_token",
        "session",
        "oauth_token",
        "client_secret",
        "client_token",
        "authorization",
        "auth",
        "api_key",
        "apikey",
        "private_key",
        "signing_key",
        "credential",
        "credentials",
        "credit_card",
        "card_number",
        "cvv",
        "cvc",
        "ssn",
        "pin",
    }
)


def mask_sensitive(
    data: dict[str, Any] | list[Any] | None,
) -> dict[str, Any] | list[Any] | None:
    if data is None:
        return None
    if isinstance(data, list):
        return _mask_list(data)
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
    return [_mask_dict(item) if isinstance(item, dict) else item for item in items]


def sanitize_traceback(trace: str) -> str:
    """Strip SQL statements, bound parameters, and connection strings from a traceback string."""
    trace = _SQL_BLOCK.sub("[SQL redacted]", trace)
    trace = _PARAMS_BLOCK.sub("[parameters redacted]", trace)
    trace = _DB_CONNSTR.sub("[connection string redacted]", trace)
    return trace
