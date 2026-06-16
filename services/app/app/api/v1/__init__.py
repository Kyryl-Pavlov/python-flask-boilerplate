from flask import Blueprint

bp = Blueprint("api_v1", __name__)

from . import health  # noqa: F401, E402
from .auth import auth_bp  # noqa: E402
from .cache_test import cache_test_bp  # noqa: E402
from .events import events_bp  # noqa: E402
from .media import media_bp  # noqa: E402

bp.register_blueprint(auth_bp)
bp.register_blueprint(media_bp)
bp.register_blueprint(cache_test_bp)
bp.register_blueprint(events_bp)
