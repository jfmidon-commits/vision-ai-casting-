import boto3
from urllib.parse import urlparse

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
            )
        return cls._client

    @classmethod
    async def upload(cls, file, photo_id: str):
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
        # No thumbnail object is generated yet. Point the thumbnail to the real
        # uploaded object instead of returning a URL that does not exist.
        return url, url

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
        client = cls.get_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
