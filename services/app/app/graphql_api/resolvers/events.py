import strawberry
from flask_jwt_extended import verify_jwt_in_request
from strawberry.scalars import JSON

from app.graphql_api.types.types import EventPayload, Response
from app.graphql_api.utils import event_to_payload
from app.models.event import Event
from app.services.aws_sqs_service import send_event


@strawberry.type
class EventQueries:
    @strawberry.field
    def events(self, info: strawberry.types.Info) -> Response[list[EventPayload]]:
        try:
            verify_jwt_in_request()
        except Exception as e:
            return Response(success=False, message="Unauthorized", exc=e)

        try:
            rows = Event.query.order_by(Event.created_at.desc()).limit(100).all()
            return Response(data=[event_to_payload(r) for r in rows])
        except Exception as e:
            return Response(success=False, message="Failed to fetch events", exc=e)


@strawberry.type
class EventMutations:
    @strawberry.mutation
    def publish_event(
        self,
        type: str,
        info: strawberry.types.Info,
        payload: JSON | None = None,
    ) -> Response[str]:
        try:
            verify_jwt_in_request()
        except Exception as e:
            return Response(success=False, message="Unauthorized", exc=e)

        if not type.strip():
            return Response(success=False, message="Event type is required")

        try:
            message_id = send_event(type, payload or {})
            return Response(data=message_id)
        except Exception as e:
            return Response(success=False, message="Failed to publish event", exc=e)
