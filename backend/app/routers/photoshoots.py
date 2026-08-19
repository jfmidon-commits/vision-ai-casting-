from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import Photoshoot, Photo, Profile
from app.schemas import PhotoshootCreate, PhotoshootResponse, APIResponse, PaginatedResponse
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/photoshoots", tags=["photoshoots"])

@router.get("", response_model=PaginatedResponse)
async def list_photoshoots(
    profile_id: Optional[UUID] = None,
    page: int = 1,
    per_page: int = 20,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Photoshoot).where(Photoshoot.tenant_id == current_user.tenant_id)
    if profile_id:
        query = query.where(Photoshoot.profile_id == profile_id)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    photoshoots = result.scalars().all()

    return PaginatedResponse(
        data=[PhotoshootResponse.model_validate(p) for p in photoshoots],
        total=total, page=page, per_page=per_page,
        total_pages=(total + per_page - 1) // per_page
    )

@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_photoshoot(
    photoshoot: PhotoshootCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    db_photoshoot = Photoshoot(**photoshoot.model_dump(), tenant_id=current_user.tenant_id)
    db.add(db_photoshoot)
    await db.commit()
    await db.refresh(db_photoshoot)
    return APIResponse(data=PhotoshootResponse.model_validate(db_photoshoot), message="Photoshoot created")

@router.get("/{photoshoot_id}", response_model=APIResponse)
async def get_photoshoot(
    photoshoot_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Photoshoot).where(
            and_(Photoshoot.id == photoshoot_id, Photoshoot.tenant_id == current_user.tenant_id)
        )
    )
    photoshoot = result.scalar_one_or_none()
    if not photoshoot:
        raise HTTPException(status_code=404, detail="Photoshoot not found")
    return APIResponse(data=PhotoshootResponse.model_validate(photoshoot))
