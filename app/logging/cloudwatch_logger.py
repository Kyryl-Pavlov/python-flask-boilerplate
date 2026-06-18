from __future__ import annotations

import json
import logging
from typing import Any

import boto3
import watchtower


class CloudWatchLogger:
    """Ships structured JSON log events to AWS CloudWatch Logs."""

    def __init__(
        self,
        log_group: str,
        stream_name: str,
        region: str = "us-east-1",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        boto3_client = boto3.client(
            "logs",
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=endpoint_url,
        )
        self._logger = logging.getLogger(f"cloudwatch.{log_group}.{stream_name}")
        if not self._logger.handlers:
            self._logger.addHandler(
                watchtower.CloudWatchLogHandler(
                    boto3_client=boto3_client,
                    log_group_name=log_group,
                    log_stream_name=stream_name,
                )
            )
        self._logger.setLevel(logging.DEBUG)

    def _serialize(
        self,
        level: str,
        message: str,
        data: dict[str, Any] | None,
        trace: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {"level": level, "message": message}
        if data:
            payload["data"] = data
        if trace:
            payload["trace"] = trace
        return json.dumps(payload)

    def info(self, message: str, data: dict[str, Any] | None = None) -> None:
        self._logger.info(self._serialize("info", message, data))

    def warning(self, message: str, data: dict[str, Any] | None = None) -> None:
        self._logger.warning(self._serialize("warning", message, data))

    def error(self, message: str, data: dict[str, Any] | None = None, trace: str | None = None) -> None:
        self._logger.error(self._serialize("error", message, data, trace))
