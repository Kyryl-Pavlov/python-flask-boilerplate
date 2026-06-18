from flask import Blueprint, request
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from app.api.utils.utils import rest_api_response
from app.extensions import db
from app.models.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return rest_api_response(success=False, message="Email and password are required", status_code=400)

    if User.query.filter_by(email=email).first():
        return rest_api_response(success=False, message="Email already registered", status_code=409)

    try:
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return rest_api_response(success=False, message="Registration failed", status_code=500, exc=e)

    return rest_api_response(status_code=201)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return rest_api_response(success=False, message="Email and password are required", status_code=400)

    try:
        user: User = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return rest_api_response(success=False, message="Invalid credentials", status_code=401)

        return rest_api_response(data={
            'access_token': create_access_token(identity=str(user.id)),
            'refresh_token': create_refresh_token(identity=str(user.id)),
        })
    except Exception as e:
        return rest_api_response(success=False, message="Login failed", status_code=500, exc=e)


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    try:
        return rest_api_response(data={
            'access_token': create_access_token(identity=get_jwt_identity())
        })
    except Exception as e:
        return rest_api_response(success=False, message="Token refresh failed", status_code=500, exc=e)
