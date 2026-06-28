from __future__ import annotations

import json
import time
import urllib.request
from typing import Any


class LokiLogger:
    """Ships structured log events to Grafana Loki via the HTTP push API."""

    def __init__(self, url: str, labels: dict[str, str]) -> None:
        self._push_url = f"{url.rstrip('/')}/loki/api/v1/push"
        self._labels = labels

    def _push(
        self, level: str, message: str, data: dict[str, Any] | None, trace: str | None
    ) -> None:
        payload: dict[str, Any] = {"level": level, "message": message}
        if data:
            payload["data"] = data
        if trace:
            payload["trace"] = trace

        body = json.dumps(
            {
                "streams": [
                    {
                        "stream": {**self._labels, "level": level},
                        "values": [[str(time.time_ns()), json.dumps(payload)]],
                    }
                ]
            }
        ).encode()

        req = urllib.request.Request(
            self._push_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pass  # non-fatal — Loki unavailability must not crash the app

    def info(self, message: str, data: dict[str, Any] | None = None) -> None:
        self._push("info", message, data, None)

    def warning(self, message: str, data: dict[str, Any] | None = None) -> None:
        self._push("warning", message, data, None)

    def error(
        self, message: str, data: dict[str, Any] | None = None, trace: str | None = None
    ) -> None:
        self._push("error", message, data, trace)
