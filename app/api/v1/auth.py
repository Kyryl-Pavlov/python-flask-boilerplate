from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from app.api.utils.utils import rest_api_response
from app.extensions import db
from app.models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return rest_api_response(success=False, message="Email and password are required", status_code=400)

    if User.query.filter_by(email=email).first():
        return rest_api_response(success=False, message="Email already registered", status_code=409)
    
    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return rest_api_response(status_code=201)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return rest_api_response(success=False, message="Email and password are required", status_code=401)
    
    user: User = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return rest_api_response(success=False, message="Invalid credentials", status_code=401)
    
    return rest_api_response(data={
        'access_token': create_access_token(identity=str(user.id)),
        'refresh_token': create_refresh_token(identity=str(user.id)),
    })

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    return rest_api_response(data={
        'access_token': create_access_token(identity=get_jwt_identity())
    })