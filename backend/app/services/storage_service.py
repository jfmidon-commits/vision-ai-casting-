import asyncio
from tempfile import SpooledTemporaryFile
from urllib.parse import urlparse

import boto3
from botocore.config import Config

from app.config import settings


class StorageService:
    _client = None
    MAX_UPLOAD_BYTES = 15 * 1024 * 1024
    UPLOAD_CHUNK_BYTES = 1024 * 1024
    ALLOWED_IMAGE_TYPES = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/heic": "heic",
        "image/heif": "heif",
    }

    @staticmethod
    def _has_valid_image_header(content_type: str, header: bytes) -> bool:
        if content_type == "image/jpeg":
            return header.startswith(b"\xff\xd8\xff")
        if content_type == "image/png":
            return header.startswith(b"\x89PNG\r\n\x1a\n")
        if content_type == "image/webp":
            return header.startswith(b"RIFF") and header[8:12] == b"WEBP"
        if content_type in {"image/heic", "image/heif"}:
            return len(header) >= 12 and header[4:8] == b"ftyp"
        return False

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
    async def upload(cls, file, photo_id: str, tenant_id: str):
        """Upload a file to S3 and return (url, thumbnail_url).

        This is the original interface used by uploads.py.
        Thumbnail generation is not yet implemented; returns the same URL.
        """
        content_type = (file.content_type or "").lower()
        ext = cls.ALLOWED_IMAGE_TYPES.get(content_type)
        if not ext:
            raise ValueError("unsupported_image_type")

        safe_tenant_id = str(tenant_id)
        safe_photo_id = str(photo_id)
        if not safe_tenant_id or not safe_photo_id:
            raise ValueError("storage_identifier_missing")
        key = f"tenants/{safe_tenant_id}/photos/{safe_photo_id}.{ext}"

        size = 0
        header = b""
        with SpooledTemporaryFile(max_size=2 * 1024 * 1024) as upload_buffer:
            while chunk := await file.read(cls.UPLOAD_CHUNK_BYTES):
                size += len(chunk)
                if size > cls.MAX_UPLOAD_BYTES:
                    raise ValueError("image_too_large")
                if len(header) < 16:
                    header = (header + chunk)[:16]
                upload_buffer.write(chunk)

            if size == 0:
                raise ValueError("empty_image")
            if not cls._has_valid_image_header(content_type, header):
                raise ValueError("invalid_image_content")

            upload_buffer.seek(0)
            await asyncio.to_thread(
                cls.get_client().upload_fileobj,
                upload_buffer,
                settings.S3_BUCKET,
                key,
                ExtraArgs={"ContentType": content_type},
            )

        url = f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
        return url, url

    @classmethod
    async def upload_file(
        cls, file_data: bytes, key: str, content_type: str = "image/jpeg"
    ) -> str:
        """Upload raw bytes to S3 with an explicit key."""
        cls.get_client().put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=file_data,
            ContentType=content_type,
        )
        return f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

    @classmethod
    def read_object_from_url(
        cls,
        url: str,
        max_bytes: int = 20 * 1024 * 1024,
    ) -> bytes:
        """Read a private S3 object with a hard in-memory size bound."""
        parsed = urlparse(url)
        key = parsed.path.lstrip("/")
        if not key:
            raise ValueError("s3_object_key_missing")

        response = cls.get_client().get_object(Bucket=settings.S3_BUCKET, Key=key)
        content_length = response.get("ContentLength")
        if content_length is not None and content_length > max_bytes:
            raise ValueError(f"s3_object_too_large:{content_length}>{max_bytes}")

        body = response["Body"]
        data = body.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError(f"s3_object_too_large:>{max_bytes}")
        return data

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
            await asyncio.to_thread(
                cls.get_client().delete_object,
                Bucket=settings.S3_BUCKET,
                Key=key,
            )
            return True
        except Exception:
            return False

    @staticmethod
    def key_from_url(url: str) -> str:
        """Extract the object key from a URL generated by this service."""
        return urlparse(url).path.lstrip("/")
