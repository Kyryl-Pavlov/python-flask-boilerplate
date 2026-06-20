from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.api.utils.utils import rest_api_response
from app.models.event import Event
from app.services.aws_sqs_service import send_event

events_bp = Blueprint("events", __name__, url_prefix="/events")


@events_bp.post("")
@jwt_required()
def publish():
    data = request.get_json() or {}
    event_type = data.get("type", "").strip()
    payload = data.get("payload") or {}

    if not event_type:
        return rest_api_response(
            success=False, message="Event type is required", status_code=400
        )

    try:
        message_id = send_event(event_type, payload)
    except Exception as e:
        return rest_api_response(
            success=False, message="Failed to publish event", status_code=500, exc=e
        )

    return rest_api_response(data={"message_id": message_id}, status_code=202)


@events_bp.get("")
@jwt_required()
def list_events():
    try:
        rows = Event.query.order_by(Event.created_at.desc()).limit(100).all()
    except Exception as e:
        return rest_api_response(
            success=False, message="Failed to fetch events", status_code=500, exc=e
        )

    return rest_api_response(
        data=[
            {
                "id": str(r.id),
                "sqs_message_id": r.sqs_message_id,
                "type": r.type,
                "payload": r.payload,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            }
            for r in rows
        ]
    )
