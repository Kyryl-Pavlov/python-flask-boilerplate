import uuid
from datetime import UTC, datetime

from app.extensions import db


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sqs_message_id = db.Column(db.String(256), unique=True, nullable=False, index=True)
    type = db.Column(db.String(100), nullable=False)
    payload = db.Column(db.JSON, nullable=True)
    status = db.Column(
        db.String(20), nullable=False, default="processed"
    )  # processed | failed
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)
