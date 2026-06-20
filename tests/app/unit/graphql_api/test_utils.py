import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.graphql_api.utils import event_to_payload

_FIXED_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
_CREATED_AT = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
_PROCESSED_AT = datetime(2024, 1, 15, 12, 5, 0, tzinfo=UTC)


def make_event(processed_at=None):
    event = MagicMock()
    event.id = _FIXED_UUID
    event.sqs_message_id = "msg-001"
    event.type = "user.created"
    event.payload = {"user_id": "abc"}
    event.status = "processed"
    event.created_at = _CREATED_AT
    event.processed_at = processed_at
    return event


def test_maps_all_scalar_fields():
    payload = event_to_payload(make_event())
    assert payload.sqs_message_id == "msg-001"
    assert payload.type == "user.created"
    assert payload.payload == {"user_id": "abc"}
    assert payload.status == "processed"


def test_id_is_stringified_uuid():
    payload = event_to_payload(make_event())
    assert payload.id == str(_FIXED_UUID)
    assert isinstance(payload.id, str)


def test_created_at_is_iso_format():
    payload = event_to_payload(make_event())
    assert payload.created_at == _CREATED_AT.isoformat()


def test_processed_at_is_none_when_not_set():
    payload = event_to_payload(make_event(processed_at=None))
    assert payload.processed_at is None


def test_processed_at_is_iso_format_when_set():
    payload = event_to_payload(make_event(processed_at=_PROCESSED_AT))
    assert payload.processed_at == _PROCESSED_AT.isoformat()
