import os
from flask import Flask
from .config import config
from .extensions import db, migrate, jwt
from . import models  # noqa: F401 — registers models with SQLAlchemy for migrations
import importlib
from .graphql_api import create_graphql_view
from .logging.logger import AppLogger, ConsoleLogger
from .logging.sentry_logger import SentryLogger
from .logging.cloudwatch_logger import CloudWatchLogger

REST_API_V = os.environ.get('REST_API_V', 'v1')
api_module = importlib.import_module(f'.api.{REST_API_V}', package=__name__)

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    loggers = [ConsoleLogger(debug=app.config.get('DEBUG', False))]

    sentry_dsn = app.config.get('SENTRY_DSN')
    if sentry_dsn:
        loggers.append(SentryLogger(dsn=sentry_dsn, environment=config_name))

    cw_log_group = app.config.get('CLOUDWATCH_LOG_GROUP')
    if cw_log_group:
        try:
            loggers.append(CloudWatchLogger(
                log_group=cw_log_group,
                stream_name=app.config.get('CLOUDWATCH_STREAM_NAME', 'app'),
                region=app.config.get('AWS_DEFAULT_REGION', 'us-east-1'),
                aws_access_key_id=app.config.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=app.config.get('AWS_SECRET_ACCESS_KEY'),
                endpoint_url=app.config.get('CLOUDWATCH_ENDPOINT_URL'),
            ))
        except Exception as e:
            app.logger.warning(f"CloudWatch logger unavailable, skipping: {e}")

    app.logger_adapter = AppLogger(*loggers)

    app.register_blueprint(api_module.bp, url_prefix=f'/api/{REST_API_V}')
    app.add_url_rule('/graphql', view_func=create_graphql_view(), methods=['GET', 'POST'])

    return app

