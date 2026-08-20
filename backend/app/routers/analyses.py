from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID

from app.database import get_db
from app.models import Analysis, Photo, Photoshoot
from app.schemas import AnalysisCreate, AnalysisResponse, APIResponse
from app.middleware.auth import get_current_user
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])

@router.get("", response_model=APIResponse)
async def list_analyses(
    photoshoot_id: Optional[UUID] = None,
    profile_id: Optional[UUID] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Analysis).where(Analysis.tenant_id == current_user.tenant_id)
    if photoshoot_id:
        query = query.where(Analysis.photoshoot_id == photoshoot_id)
    if profile_id:
        query = query.where(Analysis.profile_id == profile_id)

    result = await db.execute(query)
    analyses = result.scalars().all()
    return APIResponse(data=[AnalysisResponse.model_validate(a) for a in analyses])

@router.get("/{analysis_id}", response_model=APIResponse)
async def get_analysis(
    analysis_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Analysis).where(
            and_(Analysis.id == analysis_id, Analysis.tenant_id == current_user.tenant_id)
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return APIResponse(data=AnalysisResponse.model_validate(analysis))

@router.get("/{analysis_id}/facial", response_model=APIResponse)
async def get_facial_analysis(
    analysis_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Analysis).where(
            and_(Analysis.id == analysis_id, Analysis.tenant_id == current_user.tenant_id)
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return APIResponse(data=analysis.facial_structure)

@router.get("/{analysis_id}/visagism", response_model=APIResponse)
async def get_visagism_analysis(
    analysis_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Analysis).where(
            and_(Analysis.id == analysis_id, Analysis.tenant_id == current_user.tenant_id)
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.visagism:
        data = dict(analysis.visagism)
        data["status"] = analysis.status
        return APIResponse(data=data)

    return APIResponse(
        data={
            "schema_version": "1.0",
            "analysis_id": str(analysis.id),
            "photoshoot_id": str(analysis.photoshoot_id),
            "status": analysis.status,
            "processed_images": 0,
            "selected_views": {},
            "face_shape": None,
            "measurements": {},
            "hair_analysis": {},
            "recommendations": [],
            "top_recommendation": None,
            "card_url": None,
            "manifest_url": None,
            "analysis_sources": [],
            "limitations": ["analysis_failed"] if analysis.status == "failed" else [],
            "integrity": {},
        }
    )

@router.get("/{analysis_id}/casting", response_model=APIResponse)
async def get_casting_analysis(
    analysis_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Analysis).where(
            and_(Analysis.id == analysis_id, Analysis.tenant_id == current_user.tenant_id)
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return APIResponse(data=analysis.casting)
