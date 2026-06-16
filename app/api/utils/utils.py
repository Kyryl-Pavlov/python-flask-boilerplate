from flask import jsonify
from typing import Any

def rest_api_response(success=True, message='', data: dict[str, Any] | None = None, status_code=200):
    if data is None:
        data = {}
    return jsonify({'success': success, 'message': message, 'data': data}), status_code