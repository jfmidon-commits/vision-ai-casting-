import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import Analysis, Photo, Photoshoot
from app.schemas import AnalysisCreate, APIResponse
from app.services.ai_service import AIService

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


@router.post("/analyze/visagism/upload", response_model=APIResponse)
async def analyze_visagism_upload(
    file: UploadFile = File(...),
    angle: str = Form("front"),
    current_user=Depends(get_current_user),
):
    del current_user  # Authentication is required; tenant persistence is not needed here.

    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="O arquivo enviado nao e uma imagem")

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Imagem excede o limite de {settings.MAX_UPLOAD_SIZE_MB} MB",
        )

    suffix = Path(file.filename or "portrait.jpg").suffix or ".jpg"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        photo = SimpleNamespace(
            id=uuid4(),
            url=temp_path,
            angle=angle,
        )
        result = await AIService.analyze_visagism(photo)
        return APIResponse(data=result)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


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
