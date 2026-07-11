"""MinIO (S3-compatible) storage helper."""
from __future__ import annotations
import io
from functools import lru_cache
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from app.config import settings


@lru_cache
def _client():
    return boto3.client(
        "s3",
        endpoint_url=f"{'https' if settings.MINIO_SECURE else 'http'}://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_buckets() -> None:
    client = _client()
    for bucket in (
        settings.MINIO_BUCKET_MEDIA,
        settings.MINIO_BUCKET_EXPORTS,
        getattr(settings, "MINIO_BUCKET_BACKUPS", "koptumbuh-backups"),
    ):
        try:
            client.head_bucket(Bucket=bucket)
        except ClientError:
            try:
                client.create_bucket(Bucket=bucket)
            except ClientError:
                pass


def upload_bytes(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    ensure_buckets()
    _client().upload_fileobj(
        io.BytesIO(data),
        bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return f"{bucket}/{key}"


def upload_file(bucket: str, key: str, file_path: str, content_type: str = "application/octet-stream") -> str:
    ensure_buckets()
    _client().upload_file(file_path, bucket, key, ExtraArgs={"ContentType": content_type})
    return f"{bucket}/{key}"


def download_bytes(bucket: str, key: str) -> bytes:
    buf = io.BytesIO()
    _client().download_fileobj(bucket, key, buf)
    return buf.getvalue()


def presigned_url(bucket: str, key: str, expires: int = 3600) -> str:
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires,
    )
