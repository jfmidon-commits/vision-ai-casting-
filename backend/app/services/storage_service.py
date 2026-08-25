import boto3
from botocore.config import Config
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
                config=Config(
                    connect_timeout=10,
                    read_timeout=30,
                    retries={"max_attempts": 2, "mode": "standard"},
                ),
            )
        return cls._client

    @classmethod
    async def upload_file(cls, file_data: bytes, key: str, content_type: str = "image/jpeg") -> str:
        cls.get_client().put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=file_data,
            ContentType=content_type,
        )
        return f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

    @classmethod
    def read_object_from_url(cls, url: str) -> bytes:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        key = parsed.path.lstrip("/")
        response = cls.get_client().get_object(Bucket=settings.S3_BUCKET, Key=key)
        return response["Body"].read()

    @classmethod
    async def delete_file(cls, key: str) -> bool:
        try:
            cls.get_client().delete_object(Bucket=settings.S3_BUCKET, Key=key)
            return True
        except Exception:
            return False

    @classmethod
    def get_file_url(cls, key: str) -> str:
        return f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
