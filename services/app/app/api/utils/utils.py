from typing import Any

from flask import current_app, jsonify

from app.logging.logger import AppLogger


def rest_api_response(
    success=True,
    message="",
    data: dict[str, Any] | None = None,
    status_code=200,
    exc: BaseException | None = None,
):
    if data is None:
        data = {}

    if hasattr(current_app, "logger_adapter"):
        if success:
            level = AppLogger.Level.INFO
        elif status_code >= 500:
            level = AppLogger.Level.ERROR
        else:
            level = AppLogger.Level.WARN
        current_app.logger_adapter.log(message, level=level, data=data or None, exc=exc)

    return jsonify({"success": success, "message": message, "data": data}), status_code
