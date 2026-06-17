import uuid

import strawberry
from flask import current_app
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from strawberry.file_uploads import Upload

from app.extensions import db
from app.graphql_api.types.types import MediaPayload, Response
from app.models.media import Media
from app.services.aws_s3_service import get_presigned_url, upload_file


@strawberry.type
class MediaQueries:
    @strawberry.field
    def signed_url(self, media_id: str, info: strawberry.types.Info) -> Response[str]:
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
        except Exception:
            return Response(success=False, message="Unauthorized")

        try:
            record = db.session.get(Media, uuid.UUID(media_id))
        except ValueError:
            return Response(success=False, message="Invalid media ID")

        if not record or str(record.user_id) != user_id:
            return Response(success=False, message="Not found")

        try:
            return Response(success=True, message="ok", data=get_presigned_url(record.content_key))
        except Exception:
            return Response(success=False, message="Failed to generate URL")


@strawberry.type
class MediaMutations:
    @strawberry.mutation
    def upload_file(self, file: Upload, info: strawberry.types.Info) -> Response[MediaPayload]:
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
        except Exception:
            return Response(success=False, message="Unauthorized")

        try:
            s3_key = upload_file(file, user_id, file.filename)
        except Exception:
            return Response(success=False, message="File upload failed")

        try:
            record = Media(user_id=uuid.UUID(user_id), content_key=s3_key)
            db.session.add(record)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return Response(success=False, message="Failed to save file record")

        try:
            signed_url = get_presigned_url(s3_key)
        except Exception:
            return Response(success=False, message="Failed to generate URL")

        return Response(
            data=MediaPayload(media_id=str(record.id), url=signed_url, expires_in=current_app.config["PRESIGNED_URL_EXPIRY"]),
        )
