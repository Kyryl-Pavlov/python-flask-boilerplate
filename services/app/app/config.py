import os
from datetime import timedelta


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} environment variable is not set — refusing to start"
        )
    return value


class Config:
    SECRET_KEY = _require("SECRET_KEY")
    MAX_CONTENT_LENGTH = (
        50 * 1024 * 1024
    )  # 50 MB — Flask rejects larger requests with 413
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or SECRET_KEY
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "media-bucket")
    AWS_S3_ENDPOINT_URL = os.getenv(
        "AWS_S3_ENDPOINT_URL"
    )  # None in real AWS, set to LocalStack URL in dev
    AWS_S3_PUBLIC_ENDPOINT_URL = os.getenv(
        "AWS_S3_PUBLIC_ENDPOINT_URL"
    )  # browser-accessible URL for presigned URLs
    PRESIGNED_URL_EXPIRY = int(os.getenv("PRESIGNED_URL_EXPIRY", 86400))
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    CLOUDWATCH_LOG_GROUP = os.getenv("CLOUDWATCH_LOG_GROUP")
    CLOUDWATCH_STREAM_NAME = os.getenv("CLOUDWATCH_STREAM_NAME", "app")
    CLOUDWATCH_ENDPOINT_URL = os.getenv(
        "CLOUDWATCH_ENDPOINT_URL"
    )  # None in real AWS, set to LocalStack URL in dev
    LOKI_URL = os.getenv("LOKI_URL")
    REDIS_URL = os.getenv(
        "REDIS_URL"
    )  # redis://redis:6379/0 in Docker, None disables caching
    AWS_SQS_ENDPOINT_URL = os.getenv(
        "AWS_SQS_ENDPOINT_URL"
    )  # None in real AWS, set to LocalStack URL in dev
    SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")


class DevelopmentConfig(Config):
    DEBUG = True
    GRAPHQL_INTROSPECTION = True


class ProductionConfig(Config):
    DEBUG = False
    GRAPHQL_INTROSPECTION = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///test.db")


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
