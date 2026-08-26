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


def _triage_bypass_enabled() -> bool:
    return os.environ.get("VISION_BYPASS_TRIAGE", "").lower() in ("1", "true", "yes")


def _bypass_triage_contract(photo_id: UUID):
    return {
        "photo_id": str(photo_id),
        "accepted": True,
        "category": TriageCategory.FRONTAL.value,
        "confidence": 1.0,
        "selected": True,
        "rejection_reasons": [],
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
        raise HTTPException(status_code=404, detail="Photo not found")

    # Production currently has VISION_BYPASS_TRIAGE=true. Respect the same
    # switch used by the full analysis pipeline so the mobile upload flow does
    # not invoke heavyweight MediaPipe triage before the analysis is queued.
    if _triage_bypass_enabled():
        logger.info("Photo %s triage bypassed via VISION_BYPASS_TRIAGE", photo_id)
        return APIResponse(
            data=_bypass_triage_contract(photo_id),
            message="Photo triage bypassed",
        )

    tmp_path = None
    try:
        raw = StorageService.read_object_from_url(photo.url)

        suffix = f".{photo.format}" if photo.format else ".jpg"
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)

        triage_result = ImageTriageEngine().process_image(tmp_path)
        public = _public_triage_contract(photo_id, triage_result)
        return APIResponse(data=public, message="Photo triage completed")
    except Exception as exc:
        logger.exception("Photo %s triage failed: %s", photo_id, exc)
        public = _public_triage_contract(photo_id, reason="triage_error")
        return APIResponse(data=public, message="Photo triage blocked safely")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


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
