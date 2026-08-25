import os
import tempfile
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.image_triage.engine import ImageTriageEngine, TriageCategory
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import Photo
from app.schemas import APIResponse, PhotoBase, PhotoResponse
from app.services.storage_service import StorageService
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/photos", tags=["photos"])
logger = get_logger(__name__)


def _safe_suffix_from_format(photo_format: str | None) -> str:
    """
    Garante suffix válido para tempfile.mkstemp.
    Nunca retorna '.' nem string vazia.
    """
    if not photo_format:
        return ".jpg"
    fmt = photo_format.strip().lstrip(".").lower()
    if fmt == "jpeg":
        fmt = "jpg"
    elif fmt == "heif":
        fmt = "heic"
    allowed = {"jpg", "png", "webp", "heic", "raw"}
    if fmt not in allowed:
        logger.warning(
            "[TRIAGE_FORMAT_FALLBACK] format_original=%s format_normalized=%s fallback=jpg",
            photo_format,
            fmt,
        )
        return ".jpg"
    return f".{fmt}"


def _public_triage_contract(photo_id: UUID, result=None, reason: str | None = None):
    """Return the minimal JSON-safe triage contract used by mobile upload flows."""
    if result is None:
        return {
            "photo_id": str(photo_id),
            "accepted": False,
            "category": TriageCategory.REJECTED.value,
            "confidence": 0.0,
            "selected": False,
            "rejection_reasons": [reason or "triage_failed"],
        }

    category = result.category.value
    selected = bool(result.selected)
    accepted = selected and result.category not in (
        TriageCategory.REJECTED,
        TriageCategory.UNKNOWN,
    )
    return {
        "photo_id": str(photo_id),
        "accepted": accepted,
        "category": category,
        "confidence": float(result.confidence),
        "selected": selected,
        "rejection_reasons": list(result.rejection_reasons or []),
    }


@router.get("/{photo_id}", response_model=APIResponse)
async def get_photo(
    photo_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Photo).where(
            and_(Photo.id == photo_id, Photo.tenant_id == current_user.tenant_id)
        )
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return APIResponse(data=PhotoResponse.model_validate(photo))


@router.post("/{photo_id}/triage", response_model=APIResponse)
async def triage_photo(
    photo_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Classify one stored real photo before full analysis.

    Stored media remains private. The backend reads the object with its own S3
    credentials instead of requiring public bucket access.
    """
    result = await db.execute(
        select(Photo).where(
            and_(Photo.id == photo_id, Photo.tenant_id == current_user.tenant_id)
        )
    )
    photo = result.scalar_one_or_none()
    if not photo:
        logger.warning(
            "[TRIAGE_PHOTO_NOT_FOUND] photo_id=%s tenant_id=%s user_id=%s",
            photo_id,
            getattr(current_user, "tenant_id", "UNKNOWN"),
            getattr(current_user, "id", "UNKNOWN"),
        )
        raise HTTPException(status_code=404, detail="Photo not found")

    url_for_log = photo.url
    if url_for_log and "amazonaws.com" in url_for_log:
        try:
            url_for_log = url_for_log.split(".amazonaws.com/")[1]
        except Exception:
            url_for_log = "[redacted]"

    logger.info(
        "[TRIAGE_START] photo_id=%s format=%s url_key=%s tenant_id=%s",
        photo_id,
        photo.format,
        url_for_log,
        getattr(current_user, "tenant_id", "UNKNOWN"),
    )

    tmp_path = None
    try:
        logger.info("[TRIAGE_S3_DOWNLOAD_START] photo_id=%s", photo_id)
        raw = StorageService.read_object_from_url(photo.url)
        logger.info(
            "[TRIAGE_S3_DOWNLOAD_OK] photo_id=%s bytes=%d",
            photo_id,
            len(raw),
        )

        suffix = _safe_suffix_from_format(photo.format)
        logger.info(
            "[TRIAGE_TEMPFILE_SUFFIX] photo_id=%s suffix=%s original_format=%s",
            photo_id,
            suffix,
            photo.format,
        )
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        logger.info(
            "[TRIAGE_TEMPFILE_CREATED] photo_id=%s tmp_path=%s bytes_written=%d",
            photo_id,
            tmp_path,
            len(raw),
        )

        logger.info("[TRIAGE_ENGINE_START] photo_id=%s", photo_id)
        triage_result = ImageTriageEngine().process_image(tmp_path)
        logger.info(
            "[TRIAGE_ENGINE_OK] photo_id=%s category=%s selected=%s confidence=%.3f",
            photo_id,
            triage_result.category.value,
            triage_result.selected,
            triage_result.confidence,
        )

        public = _public_triage_contract(photo_id, triage_result)
        logger.info(
            "[TRIAGE_PUBLIC_CONTRACT] photo_id=%s accepted=%s category=%s",
            photo_id,
            public["accepted"],
            public["category"],
        )
        return APIResponse(data=public, message="Photo triage completed")

    except Exception as exc:
        logger.exception(
            "[TRIAGE_EXCEPTION] photo_id=%s exc_type=%s exc_msg=%s format=%s",
            photo_id,
            type(exc).__name__,
            str(exc),
            photo.format,
        )
        public = _public_triage_contract(photo_id, reason="triage_error")
        return APIResponse(data=public, message="Photo triage blocked safely")

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                logger.info("[TRIAGE_TEMPFILE_CLEANUP] photo_id=%s tmp_path=%s", photo_id, tmp_path)
            except OSError as cleanup_err:
                logger.warning(
                    "[TRIAGE_TEMPFILE_CLEANUP_FAIL] photo_id=%s tmp_path=%s error=%s",
                    photo_id,
                    tmp_path,
                    cleanup_err,
                )


@router.put("/{photo_id}", response_model=APIResponse)
async def update_photo(
    photo_id: UUID,
    photo_update: PhotoBase,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Photo).where(
            and_(Photo.id == photo_id, Photo.tenant_id == current_user.tenant_id)
        )
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    for field, value in photo_update.model_dump(exclude_unset=True).items():
        setattr(photo, field, value)

    await db.commit()
    await db.refresh(photo)
    return APIResponse(data=PhotoResponse.model_validate(photo), message="Photo updated")


@router.delete("/{photo_id}", response_model=APIResponse)
async def delete_photo(
    photo_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Photo).where(
            and_(Photo.id == photo_id, Photo.tenant_id == current_user.tenant_id)
        )
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    await db.delete(photo)
    await db.commit()
    return APIResponse(message="Photo deleted")
