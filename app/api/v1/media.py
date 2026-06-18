import uuid

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.utils.utils import rest_api_response
from app.extensions import db
from app.models.media import Media
from app.services.aws_s3_service import get_presigned_url, upload_file

media_bp = Blueprint("media", __name__, url_prefix="/media")


@media_bp.post("/upload")
@jwt_required()
def upload():
    if "file" not in request.files:
        return rest_api_response(success=False, message="No file provided", status_code=400)

    file = request.files["file"]
    if not file.filename:
        return rest_api_response(success=False, message="Empty filename", status_code=400)

    user_id = get_jwt_identity()

    try:
        s3_key = upload_file(file.stream, user_id, file.filename)
    except Exception as e:
        return rest_api_response(success=False, message="File upload failed", status_code=500, exc=e)

    try:
        record = Media(user_id=uuid.UUID(user_id), content_key=s3_key)
        db.session.add(record)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return rest_api_response(success=False, message="Failed to save file record", status_code=500, exc=e)

    try:
        signed_url = get_presigned_url(s3_key)
    except Exception as e:
        return rest_api_response(success=False, message="Failed to generate URL", status_code=500, exc=e)

    return rest_api_response(data={
        "media_id": str(record.id),
        "url": signed_url,
        "expires_in": 3600,
    }, status_code=201)


@media_bp.get("/<media_id>/url")
@jwt_required()
def get_url(media_id: str):
    user_id = get_jwt_identity()

    try:
        record = db.session.get(Media, uuid.UUID(media_id))
    except ValueError as e:
        return rest_api_response(success=False, message="Invalid media ID", status_code=400, exc=e)

    if not record or str(record.user_id) != user_id:
        return rest_api_response(success=False, message="Not found", status_code=404)

    try:
        return rest_api_response(data={"url": get_presigned_url(record.content_key)})
    except Exception as e:
        return rest_api_response(success=False, message="Failed to generate URL", status_code=500, exc=e)
