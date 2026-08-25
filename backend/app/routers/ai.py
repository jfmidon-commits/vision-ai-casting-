from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID

from app.database import get_db
from app.models import Photoshoot, Photo, Analysis
from app.schemas import AnalysisCreate, APIResponse, AnalysisProgress
from app.middleware.auth import get_current_user
from app.services.ai_service import AIService
from app.core.websocket import manager

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

@router.post("/analyze", response_model=APIResponse)
async def analyze_photoshoot(
    photoshoot_id: UUID,
    analysis_request: AnalysisCreate,
    background_tasks: BackgroundTasks,
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

    photo_result = await db.execute(
        select(Photo)
        .where(
            and_(
                Photo.photoshoot_id == photoshoot_id,
                Photo.tenant_id == current_user.tenant_id,
            )
        )
        .order_by(Photo.created_at.asc())
        .limit(1)
    )
    first_photo = photo_result.scalar_one_or_none()
    if not first_photo:
        raise HTTPException(status_code=400, detail="Photoshoot has no photos")

    analysis = Analysis(
        tenant_id=current_user.tenant_id,
        photoshoot_id=photoshoot_id,
        profile_id=photoshoot.profile_id,
        photo_id=first_photo.id,
        status="queued"
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    background_tasks.add_task(
        AIService.run_analysis,
        str(analysis.id),
        str(photoshoot_id),
        analysis_request.analysis_types,
        str(current_user.tenant_id)
    )

    return APIResponse(
        data={
            "analysis_id": str(analysis.id),
            "status": "queued",
            "estimated_time_seconds": 45
        },
        message="Analysis started"
    )

@router.post("/analyze/facial", response_model=APIResponse)
async def analyze_facial(
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

    result = await AIService.analyze_facial(photo)
    return APIResponse(data=result)

@router.post("/analyze/visagism", response_model=APIResponse)
async def analyze_visagism(
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

    result = await AIService.analyze_visagism(photo)
    return APIResponse(data=result)

@router.post("/analyze/casting", response_model=APIResponse)
async def analyze_casting(
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

    result = await AIService.analyze_casting(photo)
    return APIResponse(data=result)
