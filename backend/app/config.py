from pydantic_settings import BaseSettings
from functools import lru_cache
import logging
import os

logger = logging.getLogger("app.config")


class Settings(BaseSettings):
    APP_NAME: str = "Vision AI Casting"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vision_ai_casting"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_MAX_TOKENS: int = 2500
    OPENAI_TEMPERATURE: float = 0.3

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_REKOGNITION_ENABLED: bool = False
    S3_BUCKET: str = "vision-ai-casting"
    S3_ENDPOINT: str = ""

    CLERK_SECRET_KEY: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""
    CLERK_JWT_ISSUER: str = "https://clerk.visionaicasting.com"

    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    RATE_LIMIT_STARTER: int = 100
    RATE_LIMIT_PROFESSIONAL: int = 1000
    RATE_LIMIT_ENTERPRISE: int = 10000

    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_IMAGE_FORMATS: list = ["jpeg", "jpg", "png", "webp", "heic", "raw"]
    IMAGE_PROCESSING_SIZE: int = 2048
    THUMBNAIL_SIZE: int = 512

    AI_BATCH_SIZE: int = 4
    AI_CACHE_TTL: int = 86400
    AI_MAX_RETRIES: int = 3
    AI_RETRY_DELAY: int = 60

    EMAIL_PROVIDER: str = "resend"
    EMAIL_FROM: str = "noreply@visionaicasting.com"
    EMAIL_API_KEY: str = ""

    FRONTEND_URL: str = "https://vision-web-eight.vercel.app"
    CORS_ORIGINS: list = [
        "https://vision-web-eight.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def _validate_startup_config():
    """
    Valida configurações críticas no startup.
    Não altera defaults — apenas loga o que está efetivamente carregado.
    """
    critical = {
        "AWS_REGION": settings.AWS_REGION,
        "S3_BUCKET": settings.S3_BUCKET,
        "AWS_ACCESS_KEY_ID": "configured" if settings.AWS_ACCESS_KEY_ID else "MISSING",
        "AWS_SECRET_ACCESS_KEY": "configured" if settings.AWS_SECRET_ACCESS_KEY else "MISSING",
    }

    logger.info("[CONFIG_STARTUP] environment=%s", settings.ENVIRONMENT)
    for key, value in critical.items():
        logger.info("[CONFIG_STARTUP] %s=%s", key, value)

    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        logger.warning("[CONFIG_STARTUP] AWS credentials not configured — S3 operations will fail")

    if settings.ENVIRONMENT == "production":
        if settings.AWS_REGION == "us-east-1" and not os.environ.get("AWS_REGION"):
            logger.warning(
                "[CONFIG_STARTUP] AWS_REGION is default 'us-east-1' but no env var set. "
                "If your bucket is in another region, uploads will fail."
            )
        if settings.S3_BUCKET == "vision-ai-casting" and not os.environ.get("S3_BUCKET"):
            logger.warning(
                "[CONFIG_STARTUP] S3_BUCKET is default 'vision-ai-casting' but no env var set. "
                "If your bucket has a different name, uploads will fail."
            )


_validate_startup_config()
