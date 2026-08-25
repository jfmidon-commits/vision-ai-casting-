from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from datetime import datetime
import uuid

from app.database import get_db
from app.models import Photo, Photoshoot
from app.schemas import PhotoUploadResponse, APIResponse
from app.middleware.auth import get_current_user
from app.services.storage_service import StorageService
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/photoshoots", tags=["uploads"])
logger = get_logger(__name__)


_ALLOWED_FORMATS = {"jpg", "jpeg", "png", "webp", "heic", "heif", "raw"}


def _normalize_image_format(filename: str | None, content_type: str | None) -> str:
    """
    Determina formato seguro para armazenamento.
    Prioridade: filename válido -> content_type -> fallback 'jpg'
    Normaliza: jpeg->jpg, heif->heic
    Rejeita extensões não permitidas.
    """
    if filename and isinstance(filename, str):
        filename_clean = filename.strip()
        if "." in filename_clean:
            ext = filename_clean.rsplit(".", 1)[1].strip().lower()
            if ext == "jpeg":
                ext = "jpg"
            elif ext == "heif":
                ext = "heic"
            if ext in _ALLOWED_FORMATS:
                logger.info(
                    "[UPLOAD_FORMAT_FROM_FILENAME] filename=%s format=%s",
                    filename_clean,
                    ext,
                )
                return ext

    if content_type and isinstance(content_type, str):
        ct = content_type.strip().lower().split(";")[0].strip()
        ct_map = {
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/heic": "heic",
            "image/heif": "heic",
        }
        if ct in ct_map:
            logger.info(
                "[UPLOAD_FORMAT_FROM_CONTENT_TYPE] content_type=%s format=%s",
                ct,
                ct_map[ct],
            )
            return ct_map[ct]

    logger.warning(
        "[UPLOAD_FORMAT_FALLBACK] filename=%s content_type=%s fallback=jpg",
        filename,
        content_type,
    )
    return "jpg"


@router.post("/{photoshoot_id}/photos", response_model=APIResponse)
async def upload_photo(
    photoshoot_id: UUID,
    file: UploadFile = File(...),
    angle: str = "front",
    current_user=Depends(get_current_user),
    db: AsyncSession=Depends(get_db)
):
    logger.info(
        "[UPLOAD_START] photoshoot_id=%s angle=%s filename=%s content_type=%s tenant_id=%s",
        photoshoot_id,
        angle,
        file.filename,
        file.content_type,
        getattr(current_user, "tenant_id", "UNKNOWN"),
    )

    result = await db.execute(
        select(Photoshoot).where(
            and_(Photoshoot.id == photoshoot_id, Photoshoot.tenant_id == current_user.tenant_id)
        )
    )
    photoshoot = result.scalar_one_or_none()
    if not photoshoot:
        logger.warning(
            "[UPLOAD_PHOTOSHOOT_NOT_FOUND] photoshoot_id=%s tenant_id=%s",
            photoshoot_id,
            getattr(current_user, "tenant_id", "UNKNOWN"),
        )
        raise HTTPException(status_code=404, detail="Photoshoot not found")

    photo_id = uuid.uuid4()
    safe_format = _normalize_image_format(file.filename, file.content_type)
    logger.info(
        "[UPLOAD_FORMAT_SELECTED] photo_id=%s format=%s original_filename=%s",
        photo_id,
        safe_format,
        file.filename,
    )

    url, thumbnail_url = await StorageService.upload(file, str(photo_id), forced_format=safe_format)

    photo = Photo(
        id=photo_id,
        tenant_id=current_user.tenant_id,
        photoshoot_id=photoshoot_id,
        profile_id=photoshoot.profile_id,
        url=url,
        thumbnail_url=thumbnail_url,
        angle=angle,
        format=safe_format,
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    url_key = url.split(".amazonaws.com/")[1] if ".amazonaws.com/" in url else "[redacted]"
    logger.info(
        "[UPLOAD_COMPLETE] photo_id=%s photoshoot_id=%s format=%s url_key=%s",
        photo_id,
        photoshoot_id,
        safe_format,
        url_key,
    )

    return APIResponse(
        data=PhotoUploadResponse(
            id=photo_id,
            url=url,
            thumbnail_url=thumbnail_url,
            upload_url=url,
            expires_at=datetime.utcnow()
        ),
        message="Photo uploaded successfully"
    )
