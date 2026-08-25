import boto3
from urllib.parse import urlparse

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StorageService:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            endpoint = settings.S3_ENDPOINT or None
            if endpoint:
                endpoint = endpoint.strip() or None

            logger.info(
                "[S3_CLIENT_INIT] region=%s bucket=%s endpoint=%s",
                settings.AWS_REGION,
                settings.S3_BUCKET,
                endpoint or "default",
            )
            cls._client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
                endpoint_url=endpoint,
            )
        return cls._client

    @classmethod
    async def upload(cls, file, photo_id: str, forced_format: str | None = None):
        client = cls.get_client()

        if forced_format:
            ext = forced_format
        else:
            raw_ext = (file.filename or "").split(".")[-1].strip().lower()
            if raw_ext == "jpeg":
                raw_ext = "jpg"
            elif raw_ext == "heif":
                raw_ext = "heic"
            allowed = {"jpg", "png", "webp", "heic", "raw"}
            ext = raw_ext if raw_ext in allowed else "jpg"

        key = f"photos/{photo_id}.{ext}"
        content = await file.read()
        content_type = file.content_type or f"image/{ext}"

        logger.info(
            "[S3_PUT_START] bucket=%s key=%s region=%s content_type=%s bytes=%d",
            settings.S3_BUCKET,
            key,
            settings.AWS_REGION,
            content_type,
            len(content),
        )

        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

        url = f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
        logger.info(
            "[S3_PUT_OK] bucket=%s key=%s region=%s bytes=%d",
            settings.S3_BUCKET,
            key,
            settings.AWS_REGION,
            len(content),
        )

        return url, url

    @classmethod
    def read_object_from_url(cls, url: str) -> bytes:
        """Read an object from this app's private S3 bucket using IAM credentials."""
        parsed = urlparse(url)
        key = parsed.path.lstrip("/")
        if not key:
            logger.error("[S3_GET_ERROR] url=%s reason=empty_key", url)
            raise ValueError("s3_object_key_missing")

        logger.info(
            "[S3_GET_START] bucket=%s key=%s region=%s",
            settings.S3_BUCKET,
            key,
            settings.AWS_REGION,
        )

        response = cls.get_client().get_object(Bucket=settings.S3_BUCKET, Key=key)
        data = response["Body"].read()

        logger.info(
            "[S3_GET_OK] bucket=%s key=%s region=%s bytes=%d",
            settings.S3_BUCKET,
            key,
            settings.AWS_REGION,
            len(data),
        )
        return data

    @classmethod
    def get_presigned_url(cls, key: str, expires_in: int = 3600):
        client = cls.get_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
