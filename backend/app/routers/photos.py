from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID

from app.database import get_db
from app.models import Photo, Photoshoot
from app.schemas import PhotoBase, PhotoResponse, APIResponse
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/photos", tags=["photos"])

@router.get("/{photo_id}", response_model=APIResponse)
async def get_photo(
    photo_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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

@router.put("/{photo_id}", response_model=APIResponse)
async def update_photo(
    photo_id: UUID,
    photo_update: PhotoBase,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
