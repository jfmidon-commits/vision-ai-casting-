import uuid
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import Photo, Photoshoot, Profile
from app.schemas import APIResponse, PhotoUploadResponse
from app.services.storage_service import StorageService

router = APIRouter(prefix="/api/v1/photoshoots", tags=["uploads"])


@router.post("/{photoshoot_id}/photos", response_model=APIResponse)
async def upload_photo(
    photoshoot_id: UUID,
    file: UploadFile = File(...),
    angle: str = "front",
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Photoshoot)
        .join(Profile, Photoshoot.profile_id == Profile.id)
        .where(
            and_(
                Photoshoot.id == photoshoot_id,
                Photoshoot.tenant_id == current_user.tenant_id,
                Profile.tenant_id == current_user.tenant_id,
            )
        )
    )
    photoshoot = result.scalar_one_or_none()
    if not photoshoot:
        raise HTTPException(status_code=404, detail="Photoshoot not found")

    photo_id = uuid.uuid4()
    try:
        url, thumbnail_url = await StorageService.upload(
            file,
            str(photo_id),
            str(current_user.tenant_id),
        )
    except ValueError as exc:
        errors = {
            "unsupported_image_type": (415, "Unsupported image type"),
            "invalid_image_content": (415, "File content is not a valid image"),
            "image_too_large": (413, "Image exceeds the 15 MB limit"),
            "empty_image": (400, "Image is empty"),
        }
        status_code, detail = errors.get(str(exc), (400, "Invalid image"))
        raise HTTPException(status_code=status_code, detail=detail) from exc

    photo = Photo(
        id=photo_id,
        tenant_id=current_user.tenant_id,
        photoshoot_id=photoshoot_id,
        profile_id=photoshoot.profile_id,
        url=url,
        thumbnail_url=thumbnail_url,
        angle=angle,
        format=StorageService.ALLOWED_IMAGE_TYPES[file.content_type.lower()],
    )
    db.add(photo)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        await StorageService.delete_file(StorageService.key_from_url(url))
        raise
    await db.refresh(photo)

    return APIResponse(
        data=PhotoUploadResponse(
            id=photo_id,
            url=url,
            thumbnail_url=thumbnail_url,
            upload_url=url,
            expires_at=datetime.utcnow(),
        ),
        message="Photo uploaded successfully",
    )
