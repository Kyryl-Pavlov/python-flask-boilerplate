import os

from flask import jsonify

from . import bp

REST_API_VN = os.environ.get("REST_API_VN", "1.0.0")


@bp.get("/health")
def health_check():
    return jsonify({"status": "ok", "version": REST_API_VN})
