from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.models import Profile
from app.schemas import ProfileCreate, ProfileUpdate, APIResponse, PaginatedResponse
from app.middleware.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])


def profile_payload(profile: Profile) -> dict:
    return {
        "id": str(profile.id),
        "tenant_id": str(profile.tenant_id),
        "code": profile.code,
        "full_name": profile.full_name,
        "artistic_name": profile.artistic_name,
        "birth_date": profile.birth_date,
        "gender": profile.gender,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "eye_color": profile.eye_color,
        "hair_color": profile.hair_color,
        "skin_tone": profile.skin_tone,
        "body_type": profile.body_type,
        "shoe_size": profile.shoe_size,
        "dress_size": profile.dress_size,
        "pants_size": profile.pants_size,
        "shirt_size": profile.shirt_size,
        "languages": profile.languages or [],
        "skills": profile.skills or [],
        "experience_years": profile.experience_years,
        "bio": profile.bio,
        "instagram": profile.instagram,
        "portfolio_url": profile.portfolio_url,
        "status": profile.status,
        "metadata": profile._metadata or {},
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "age": None,
        "photoshoot_count": 0,
        "latest_analysis": None,
        "latest_report": None,
    }


@router.get("", response_model=PaginatedResponse)
async def list_profiles(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Profile).where(Profile.tenant_id == current_user.tenant_id)
    if status:
        query = query.where(Profile.status == status)
    if search:
        query = query.where(
            Profile.full_name.ilike(f"%{search}%") |
            Profile.artistic_name.ilike(f"%{search}%")
        )

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    profiles = result.scalars().all()

    return PaginatedResponse(
        data=[profile_payload(p) for p in profiles],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page,
    )


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile: ProfileCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    db_profile = Profile(**profile.model_dump(), tenant_id=current_user.tenant_id)
    db.add(db_profile)
    await db.commit()
    await db.refresh(db_profile)
    return APIResponse(data=profile_payload(db_profile), message="Profile created")


@router.get("/{profile_id}", response_model=APIResponse)
async def get_profile(
    profile_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Profile).where(
            and_(Profile.id == profile_id, Profile.tenant_id == current_user.tenant_id)
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return APIResponse(data=profile_payload(profile))


@router.put("/{profile_id}", response_model=APIResponse)
async def update_profile(
    profile_id: UUID,
    profile_update: ProfileUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Profile).where(
            and_(Profile.id == profile_id, Profile.tenant_id == current_user.tenant_id)
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    for field, value in profile_update.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return APIResponse(data=profile_payload(profile), message="Profile updated")


@router.delete("/{profile_id}", response_model=APIResponse)
async def delete_profile(
    profile_id: UUID,
    current_user = Depends(require_role(["admin", "manager"])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Profile).where(
            and_(Profile.id == profile_id, Profile.tenant_id == current_user.tenant_id)
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile.status = "archived"
    await db.commit()
    return APIResponse(message="Profile archived")
