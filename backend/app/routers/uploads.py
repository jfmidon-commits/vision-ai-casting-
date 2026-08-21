from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from datetime import datetime
import uuid

from app.database import get_db
from app.models import Photo, Photoshoot
from app.schemas import PhotoUploadResponse, PhotoResponse, APIResponse
from app.middleware.auth import get_current_user
from app.services.storage_service import StorageService

router = APIRouter(prefix="/api/v1/photoshoots", tags=["uploads"])


@router.get("/{photoshoot_id}/photos", response_model=APIResponse)
async def list_photos(
    photoshoot_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    photoshoot_result = await db.execute(
        select(Photoshoot).where(
            and_(
                Photoshoot.id == photoshoot_id,
                Photoshoot.tenant_id == current_user.tenant_id,
            )
        )
    )
    if not photoshoot_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Photoshoot not found")

    result = await db.execute(
        select(Photo)
        .where(
            and_(
                Photo.photoshoot_id == photoshoot_id,
                Photo.tenant_id == current_user.tenant_id,
            )
        )
        .order_by(Photo.created_at.asc())
    )
    photos = result.scalars().all()
    return APIResponse(data=[PhotoResponse.model_validate(photo) for photo in photos])


@router.post("/{photoshoot_id}/photos", response_model=APIResponse)
async def upload_photo(
    photoshoot_id: UUID,
    file: UploadFile = File(...),
    angle: str = "front",
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Photoshoot).where(
            and_(
                Photoshoot.id == photoshoot_id,
                Photoshoot.tenant_id == current_user.tenant_id,
            )
        )
    )
    photoshoot = result.scalar_one_or_none()
    if not photoshoot:
        raise HTTPException(status_code=404, detail="Photoshoot not found")

    photo_id = uuid.uuid4()
    url, thumbnail_url = await StorageService.upload(file, str(photo_id))

    photo = Photo(
        id=photo_id,
        tenant_id=current_user.tenant_id,
        photoshoot_id=photoshoot_id,
        profile_id=photoshoot.profile_id,
        url=url,
        thumbnail_url=thumbnail_url,
        angle=angle,
        format=file.filename.split(".")[-1].lower(),
    )
    db.add(photo)
    await db.commit()
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
