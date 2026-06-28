import uuid
from datetime import UTC, datetime

from app.extensions import db


class Media(db.Model):
    __tablename__ = "media"

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # db stores the S3 key of hte content, not the presigned URL
    # presigned URL are time-limited
    content_key = db.Column(db.String, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    user = db.relationship("User", backref=db.backref("media", lazy="dynamic"))
