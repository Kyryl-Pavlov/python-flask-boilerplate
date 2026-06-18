import strawberry
from flask_jwt_extended import create_access_token, create_refresh_token, verify_jwt_in_request, get_jwt_identity

from app.extensions import db
from app.models.user import User
from app.graphql_api.types.types import AuthPayload, Response


@strawberry.type
class AuthMutations:
    @strawberry.mutation
    def register(self, email: str, password: str) -> Response[str]:
        email = email.strip().lower()
        if not email or not password:
            return Response(success=False, message='Email and password are required')
        if User.query.filter_by(email=email).first():
            return Response(success=False, message='Email already registered')

        try:
            user = User(email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return Response(success=False, message='Registration failed', exc=e)

        return Response()

    @strawberry.mutation
    def login(self, email: str, password: str) -> Response[AuthPayload]:
        try:
            user = User.query.filter_by(email=email.strip().lower()).first()
            if not user or not user.check_password(password):
                return Response(success=False, message='Invalid credentials')

            return Response(data=AuthPayload(
                access_token=create_access_token(identity=str(user.id)),
                refresh_token=create_refresh_token(identity=str(user.id)),
            ))
        except Exception as e:
            return Response(success=False, message='Login failed', exc=e)

    @strawberry.mutation
    def refresh_token(self, info: strawberry.types.Info) -> Response[AuthPayload]:
        try:
            verify_jwt_in_request(refresh=True)
        except Exception as e:
            return Response(success=False, message="Invalid or expired refresh token", exc=e)

        try:
            return Response(data=AuthPayload(access_token=create_access_token(identity=get_jwt_identity())))
        except Exception as e:
            return Response(success=False, message="Token refresh failed", exc=e)
