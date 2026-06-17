from flask import Blueprint

bp = Blueprint('api_v1', __name__)

from . import health
from .auth import auth_bp
from .media import media_bp

bp.register_blueprint(auth_bp)
bp.register_blueprint(media_bp)