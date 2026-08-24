"""
Endpoint temporário de diagnóstico S3.
NÃO mergear em main. Remover após validação.
"""
import uuid
from fastapi import APIRouter, HTTPException
from app.services.storage_service import StorageService
from app.config import settings

router = APIRouter(tags=["diagnostics"])

@router.get("/health/s3")
async def s3_health_check():
    """
    Testa PutObject, GetObject e DeleteObject no S3.
    Retorna resultado sem expor secrets.
    NÃO expõe credenciais AWS.
    """
    test_key = f"_health_test/{uuid.uuid4()}.txt"
    test_body = b"vision-ai-casting-s3-health-check"

    result = {
        "s3_bucket": settings.S3_BUCKET,
        "s3_region": settings.AWS_REGION,
        "s3_endpoint_configured": bool(settings.S3_ENDPOINT),
        "aws_credentials_configured": bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY),
        "put": False,
        "get": False,
        "delete": False,
        "error": None,
    }

    try:
        client = StorageService.get_client()

        # PUT
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=test_key,
            Body=test_body,
            ContentType="text/plain",
        )
        result["put"] = True

        # GET
        resp = client.get_object(Bucket=settings.S3_BUCKET, Key=test_key)
        data = resp["Body"].read()
        result["get"] = data == test_body

        # DELETE
        client.delete_object(Bucket=settings.S3_BUCKET, Key=test_key)
        result["delete"] = True

        result["status"] = "healthy"

    except Exception as e:
        result["error"] = type(e).__name__
        result["error_msg"] = str(e)
        result["status"] = "failed"
        raise HTTPException(status_code=503, detail=result)

    return result
