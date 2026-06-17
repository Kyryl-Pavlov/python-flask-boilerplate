import boto3
from flask import current_app

def _client(public: bool = False):
    endpoint = (
        current_app.config.get("AWS_S3_PUBLIC_ENDPOINT_URL")
        if public
        else current_app.config.get("AWS_S3_ENDPOINT_URL")
    )
    return boto3.client(
        "s3",
        region_name=current_app.config["AWS_DEFAULT_REGION"],
        aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
        endpoint_url=endpoint,
    )

def _ensure_bucket(client, bucket: str) -> None:  # client must be the internal (non-public) client
    try:
        client.head_bucket(Bucket=bucket)
    except client.exceptions.NoSuchBucket:
        client.create_bucket(Bucket=bucket)
    except Exception:
        pass


def upload_file(file_obj, user_id: str, filename: str) -> str:
    key = f"media/{user_id}/{filename}"
    client = _client()
    _ensure_bucket(client, current_app.config["AWS_S3_BUCKET"])
    client.upload_fileobj(file_obj, current_app.config["AWS_S3_BUCKET"], key)
    return key

def get_presigned_url(s3_key: str) -> str:
    return _client(public=True).generate_presigned_url(
        "get_object",
        Params={
            "Bucket": current_app.config["AWS_S3_BUCKET"],
            "Key": s3_key,
        },
        ExpiresIn=current_app.config["PRESIGNED_URL_EXPIRY"],
    )