import json
import os
import re
import uuid
from datetime import UTC, datetime

import boto3
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool


def _get_database_url() -> str:
    secret_arn = os.environ.get("DATABASE_URL_SECRET_ARN")
    if secret_arn:
        sm = boto3.client(
            "secretsmanager",
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        )
        return sm.get_secret_value(SecretId=secret_arn)["SecretString"]
    return os.environ["DATABASE_URL"]


DATABASE_URL = _get_database_url()
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]
POLL_WAIT_SECONDS = int(os.environ.get("POLL_WAIT_SECONDS", "5"))

engine = sa.create_engine(DATABASE_URL, poolclass=NullPool)

_SQL_BLOCK = re.compile(r"\[SQL:.*?\]", re.DOTALL)
_PARAMS_BLOCK = re.compile(r"\[parameters:.*?\]", re.DOTALL)
_DB_CONNSTR = re.compile(r"\b(postgresql|mysql|sqlite)(\+\w+)?://\S+", re.IGNORECASE)


def _safe_exc(exc: Exception) -> str:
    msg = _SQL_BLOCK.sub("[SQL redacted]", str(exc))
    msg = _PARAMS_BLOCK.sub("[parameters redacted]", msg)
    msg = _DB_CONNSTR.sub("[connection string redacted]", msg)
    return f"{type(exc).__name__}: {msg}"


metadata = sa.MetaData()
sqs = boto3.client(
    "sqs",
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    endpoint_url=os.environ.get("AWS_SQS_ENDPOINT_URL"),
)


def events_table() -> sa.Table:
    if "events" not in metadata.tables:
        sa.Table("events", metadata, autoload_with=engine)
    return metadata.tables["events"]


def process_record(record: dict, session: Session) -> None:
    message_id = record.get("MessageId") or record.get("messageId", str(uuid.uuid4()))
    body = json.loads(record.get("Body") or record.get("body", "{}"))
    now = datetime.now(UTC)

    stmt = (
        pg_insert(events_table())
        .values(
            id=uuid.uuid4(),
            sqs_message_id=message_id,
            type=body.get("type", "unknown"),
            payload=body.get("payload", {}),
            status="processed",
            created_at=now,
            processed_at=now,
        )
        .on_conflict_do_nothing(index_elements=["sqs_message_id"])
    )
    session.execute(stmt)
    session.commit()


def handler(event: dict, context) -> dict:
    with Session(engine) as session:
        for record in event.get("Records", []):
            process_record(record, session)
    return {"statusCode": 200}


def poll() -> None:
    events_table()
    print(f"[worker] polling {SQS_QUEUE_URL} …")
    while True:
        resp = sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=POLL_WAIT_SECONDS,
        )
        for msg in resp.get("Messages", []):
            try:
                with Session(engine) as session:
                    process_record(msg, session)
                sqs.delete_message(
                    QueueUrl=SQS_QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"]
                )
            except Exception as exc:
                print(f"[worker] failed {msg.get('MessageId')}: {_safe_exc(exc)}")


if __name__ == "__main__":
    poll()
