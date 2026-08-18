import boto3
import uuid
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
                endpoint_url=settings.S3_ENDPOINT or None
            )
        return cls._client

    @classmethod
    async def upload(cls, file, photo_id: str):
        client = cls.get_client()
        ext = file.filename.split(".")[-1].lower()
        key = f"photos/{photo_id}.{ext}"
        thumb_key = f"photos/{photo_id}_thumb.{ext}"

        content = await file.read()
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=content,
            ContentType=file.content_type
        )

        url = f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
        thumb_url = f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{thumb_key}"
        return url, thumb_url

    @classmethod
    def get_presigned_url(cls, photo_id: str, expires_in: int = 3600):
        client = cls.get_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": f"photos/{photo_id}"},
            ExpiresIn=expires_in
        )
