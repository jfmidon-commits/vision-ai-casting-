from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID

from app.database import get_db
from app.models import Photoshoot, Photo, Analysis
from app.schemas import AnalysisCreate, APIResponse, AnalysisProgress
from app.schemas.visagism import FullVisagismRequest
from app.middleware.auth import get_current_user
from app.services.ai_service import AIService
from app.core.websocket import manager

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.post("/analyze", response_model=APIResponse)
async def analyze_photoshoot(
    photoshoot_id: UUID,
    analysis_request: AnalysisCreate,
    background_tasks: BackgroundTasks,
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

    analysis = Analysis(
        tenant_id=current_user.tenant_id,
        photoshoot_id=photoshoot_id,
        profile_id=photoshoot.profile_id,
        photo_id=photoshoot.photos[0].id if photoshoot.photos else None,
        status="queued",
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    background_tasks.add_task(
        AIService.run_analysis,
        str(analysis.id),
        str(photoshoot_id),
        analysis_request.analysis_types,
        str(current_user.tenant_id),
    )
    return APIResponse(
        data={
            "analysis_id": str(analysis.id),
            "status": "queued",
            "estimated_time_seconds": 45,
        },
        message="Analysis started",
    )


@router.post("/analyze/visagism/full", response_model=APIResponse)
async def analyze_visagism_full(
    request: FullVisagismRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue the real multi-photo reproducible visagism pipeline."""
    photoshoot_result = await db.execute(
        select(Photoshoot).where(
            and_(
                Photoshoot.id == request.photoshoot_id,
                Photoshoot.tenant_id == current_user.tenant_id,
            )
        )
    )
    photoshoot = photoshoot_result.scalar_one_or_none()
    if not photoshoot:
        raise HTTPException(status_code=404, detail="Photoshoot not found")

    photo_result = await db.execute(
        select(Photo).where(
            and_(
                Photo.photoshoot_id == request.photoshoot_id,
                Photo.tenant_id == current_user.tenant_id,
            )
        )
    )
    photos = list(photo_result.scalars().all())
    if len(photos) < 3:
        raise HTTPException(
            status_code=400,
            detail="At least 3 photos are required for full visagism analysis",
        )

    analysis = Analysis(
        tenant_id=current_user.tenant_id,
        photoshoot_id=request.photoshoot_id,
        profile_id=photoshoot.profile_id,
        photo_id=photos[0].id,
        status="queued",
        model_version="visagism-real-pipeline-v1",
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    background_tasks.add_task(
        AIService.run_full_visagism_analysis,
        str(analysis.id),
        str(request.photoshoot_id),
        str(current_user.tenant_id),
        request.cut_limit,
        request.generate_card,
    )
    return APIResponse(
        data={
            "analysis_id": str(analysis.id),
            "photoshoot_id": str(request.photoshoot_id),
            "status": "queued",
            "pipeline": "visagism-real-pipeline-v1",
            "photo_count": len(photos),
        },
        message="Full visagism analysis started",
    )


@router.post("/analyze/facial", response_model=APIResponse)
async def analyze_facial(
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

    result = await AIService.analyze_facial(photo)
    return APIResponse(data=result)


@router.post("/analyze/visagism", response_model=APIResponse)
async def analyze_visagism(
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

    result = await AIService.analyze_visagism(photo)
    return APIResponse(data=result)


@router.post("/analyze/casting", response_model=APIResponse)
async def analyze_casting(
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

    result = await AIService.analyze_casting(photo)
    return APIResponse(data=result)
