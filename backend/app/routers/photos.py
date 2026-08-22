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

router = APIRouter(prefix="/api/v1/photos", tags=["photos"])


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

    This endpoint is intentionally fail-closed and exposes no landmarks or raw
    CV diagnostics. A download/engine failure is returned as accepted=false.
    """
    result = await db.execute(
        select(Photo).where(
            and_(Photo.id == photo_id, Photo.tenant_id == current_user.tenant_id)
        )
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    tmp_path = None
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(photo.url) as response:
                response.raise_for_status()
                raw = await response.read()

        fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
        os.write(fd, raw)
        os.close(fd)

        triage_result = ImageTriageEngine().process_image(tmp_path)
        public = _public_triage_contract(photo_id, triage_result)
        return APIResponse(data=public, message="Photo triage completed")
    except Exception:
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
