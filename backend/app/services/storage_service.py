import boto3
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
        ext = file.filename.split(".")[-1].lower()
        key = f"photos/{photo_id}.{ext}"
        thumb_key = f"photos/{photo_id}_thumb.{ext}"
        content = await file.read()
        await cls.upload_bytes(content, key, file.content_type)
        return cls.public_url(key), cls.public_url(thumb_key)

    @classmethod
    async def upload_bytes(cls, content: bytes, key: str, content_type: str):
        """Upload generated artifacts without wrapping them as UploadFile."""
        client = cls.get_client()
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        return cls.public_url(key)

    @classmethod
    def public_url(cls, key: str) -> str:
        return (
            f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
        )

    @classmethod
    def get_presigned_url(cls, photo_id: str, expires_in: int = 3600):
        client = cls.get_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": f"photos/{photo_id}"},
            ExpiresIn=expires_in,
        )
