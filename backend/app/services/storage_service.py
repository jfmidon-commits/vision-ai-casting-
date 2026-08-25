import boto3
from botocore.config import Config
from urllib.parse import urlparse
from typing import Optional

from app.config import settings


class StorageService:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
                endpoint_url=settings.S3_ENDPOINT or None,
                config=Config(
                    connect_timeout=10,
                    read_timeout=30,
                    retries={"max_attempts": 2, "mode": "standard"},
                ),
            )
        return cls._client

    @classmethod
    async def upload(cls, file, photo_id: str):
        """Upload a file to S3 and return (url, thumbnail_url).

        This is the original interface used by uploads.py.
        Thumbnail generation is not yet implemented; returns the same URL."""
        client = cls.get_client()
        ext = file.filename.split(".")[-1].lower()
        key = f"photos/{photo_id}.{ext}"

        content = await file.read()
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=content,
            ContentType=file.content_type,
        )

        url = f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
        return url, url

    @classmethod
    async def upload_file(cls, file_data: bytes, key: str, content_type: str = "image/jpeg") -> str:
        """Upload raw bytes to S3 with an explicit key.

        Alternative interface for programmatic uploads."""
        cls.get_client().put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=file_data,
            ContentType=content_type,
        )
        return f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

    @classmethod
    def read_object_from_url(cls, url: str) -> bytes:
        """Read an object from this app's private S3 bucket using IAM credentials."""
        parsed = urlparse(url)
        key = parsed.path.lstrip("/")
        if not key:
            raise ValueError("s3_object_key_missing")

        response = cls.get_client().get_object(Bucket=settings.S3_BUCKET, Key=key)
        return response["Body"].read()

    @classmethod
    def get_presigned_url(cls, key: str, expires_in: int = 3600):
        """Generate a presigned URL for temporary access to a private S3 object."""
        client = cls.get_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )

    @classmethod
    def get_file_url(cls, key: str) -> str:
        """Return the public URL for an S3 object."""
        return f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

    @classmethod
    async def delete_file(cls, key: str) -> bool:
        """Delete an object from S3."""
        try:
            cls.get_client().delete_object(Bucket=settings.S3_BUCKET, Key=key)
            return True
        except Exception:
            return False
