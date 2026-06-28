from app.graphql_api.types.types import EventPayload
from app.models.event import Event


def event_to_payload(r: Event) -> EventPayload:
    return EventPayload(
        id=str(r.id),
        sqs_message_id=r.sqs_message_id,
        type=r.type,
        payload=r.payload,
        status=r.status,
        created_at=r.created_at.isoformat(),
        processed_at=r.processed_at.isoformat() if r.processed_at else None,
    )
