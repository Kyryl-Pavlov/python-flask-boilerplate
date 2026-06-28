import importlib
import os
import time

from flask import Flask, g, request
from prometheus_flask_exporter import PrometheusMetrics

from . import models  # noqa: F401 — registers models with SQLAlchemy for migrations
from .config import config
from .extensions import db, jwt, migrate
from .graphql_api import create_graphql_view
from .logging.cloudwatch_logger import CloudWatchLogger
from .logging.logger import AppLogger, ConsoleLogger
from .logging.loki_logger import LokiLogger
from .logging.sentry_logger import SentryLogger
from .services.cache_service import CacheService

REST_API_V = os.environ.get("REST_API_V", "v1")
api_module = importlib.import_module(f".api.{REST_API_V}", package=__name__)


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    loggers = [ConsoleLogger(debug=app.config.get("DEBUG", False))]

    sentry_dsn = app.config.get("SENTRY_DSN")
    if sentry_dsn:
        loggers.append(SentryLogger(dsn=sentry_dsn, environment=config_name))

    cw_log_group = app.config.get("CLOUDWATCH_LOG_GROUP")
    if cw_log_group:
        try:
            loggers.append(
                CloudWatchLogger(
                    log_group=cw_log_group,
                    stream_name=app.config.get("CLOUDWATCH_STREAM_NAME", "app"),
                    region=app.config.get("AWS_DEFAULT_REGION", "us-east-1"),
                    aws_access_key_id=app.config.get("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=app.config.get("AWS_SECRET_ACCESS_KEY"),
                    endpoint_url=app.config.get("CLOUDWATCH_ENDPOINT_URL"),
                )
            )
        except Exception as e:
            app.logger.warning(f"CloudWatch logger unavailable, skipping: {e}")

    loki_url = app.config.get("LOKI_URL")
    if loki_url:
        loggers.append(
            LokiLogger(
                url=loki_url,
                labels={"app": "flask-boilerplate", "env": config_name},
            )
        )

    app.logger_adapter = AppLogger(*loggers)

    redis_url = app.config.get("REDIS_URL")
    app.cache = CacheService.from_url(redis_url) if redis_url else None

    PrometheusMetrics(
        app, group_by="endpoint", default_labels={"app": "flask-boilerplate"}
    )

    app.register_blueprint(api_module.bp, url_prefix=f"/api/{REST_API_V}")
    app.add_url_rule(
        "/graphql",
        view_func=create_graphql_view(app.config.get("GRAPHQL_INTROSPECTION", False)),
        methods=["GET", "POST"],
    )

    @app.before_request
    def _record_start_time():
        g.request_start = time.perf_counter()

    @app.after_request
    def _log_response_time(response):
        if hasattr(g, "request_start"):
            duration_ms = round((time.perf_counter() - g.request_start) * 1000, 2)
            app.logger_adapter.log(
                "response",
                level=AppLogger.Level.INFO,
                data={
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
        return response

    return app
