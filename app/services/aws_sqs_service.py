import json

import boto3
from flask import current_app


def _client():
    return boto3.client(
        "sqs",
        region_name=current_app.config.get("AWS_DEFAULT_REGION", "us-east-1"),
        aws_access_key_id=current_app.config.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=current_app.config.get("AWS_SECRET_ACCESS_KEY"),
        endpoint_url=current_app.config.get("AWS_SQS_ENDPOINT_URL"),
    )


def _ensure_queue(client, queue_url: str) -> None:
    queue_name = queue_url.rstrip("/").split("/")[-1]
    try:
        client.get_queue_url(QueueName=queue_name)
    except client.exceptions.QueueDoesNotExist:
        client.create_queue(QueueName=queue_name)


def send_event(event_type: str, payload: dict) -> str:
    """Publish an event to the SQS queue. Returns the SQS MessageId."""
    queue_url = current_app.config["SQS_QUEUE_URL"]
    client = _client()
    _ensure_queue(client, queue_url)
    body = json.dumps({"type": event_type, "payload": payload})
    response = client.send_message(QueueUrl=queue_url, MessageBody=body)
    return response["MessageId"]
