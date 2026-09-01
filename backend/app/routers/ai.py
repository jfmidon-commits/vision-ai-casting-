import asyncio
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.websocket import manager
from app.database import AsyncSessionLocal, get_db
from app.middleware.auth import get_current_user
from app.models import Analysis, Photo, Photoshoot
from app.schemas import AnalysisCreate, AnalysisProgress, APIResponse
from app.services.ai_service import AIService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

ANALYSIS_TIMEOUT_SECONDS = 300


async def _mark_analysis_failed(
    analysis_id: str, error_message: str, tenant_id: str
) -> None:
    """Persist a terminal failure so analyses never remain stuck in processing."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Analysis).where(
                    and_(
                        Analysis.id == analysis_id,
                        Analysis.tenant_id == tenant_id,
                    )
                )
            )
            analysis = result.scalar_one_or_none()
            if not analysis or analysis.status == "completed":
                return

            raw_results = (
                dict(analysis.raw_results)
                if isinstance(analysis.raw_results, dict)
                else {}
            )
            raw_results["pipeline_error"] = {
                "message": error_message,
                "failed_at": datetime.utcnow().isoformat(),
            }
            analysis.raw_results = raw_results
            analysis.status = "failed"
            analysis.completed_at = datetime.utcnow()
            await db.commit()
    except Exception:
        logger.exception(
            "Failed to persist terminal state for analysis %s", analysis_id
        )


async def _run_analysis_safely(
    analysis_id: str,
    photoshoot_id: str,
    analysis_types: list[str],
    tenant_id: str,
) -> None:
    """Run the AI pipeline with a hard timeout and terminal failure handling."""
    logger.info(
        "Analysis %s background pipeline started for photoshoot %s",
        analysis_id,
        photoshoot_id,
    )
    try:
        await asyncio.wait_for(
            AIService.run_analysis(
                analysis_id,
                photoshoot_id,
                analysis_types,
                tenant_id,
            ),
            timeout=ANALYSIS_TIMEOUT_SECONDS,
        )
        logger.info("Analysis %s background pipeline completed", analysis_id)
    except asyncio.TimeoutError:
        message = f"analysis_timeout_after_{ANALYSIS_TIMEOUT_SECONDS}s"
        logger.error(
            "Analysis %s timed out after %ss", analysis_id, ANALYSIS_TIMEOUT_SECONDS
        )
        await _mark_analysis_failed(analysis_id, message, tenant_id)
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        logger.exception("Analysis %s pipeline failed: %s", analysis_id, message)
        await _mark_analysis_failed(analysis_id, message, tenant_id)


@router.post("/analyze", response_model=APIResponse)
async def analyze_photoshoot(
    photoshoot_id: UUID,
    analysis_request: AnalysisCreate,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info(
        "Starting analysis for photoshoot %s by user %s",
        photoshoot_id,
        current_user.id,
    )

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
        status="queued",
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    logger.info(
        "Analysis %s queued for photoshoot %s; scheduling background task",
        analysis.id,
        photoshoot_id,
    )

    background_tasks.add_task(
        _run_analysis_safely,
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


@router.get("/status/{analysis_id}", response_model=APIResponse)
async def get_analysis_status(
    analysis_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis).where(
            and_(
                Analysis.id == analysis_id,
                Analysis.tenant_id == current_user.tenant_id,
            )
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.status == "failed":
        error_message = "A análise falhou no backend."
        if isinstance(analysis.raw_results, dict):
            pipeline_error = analysis.raw_results.get("pipeline_error")
            if isinstance(pipeline_error, dict) and pipeline_error.get("message"):
                error_message = str(pipeline_error["message"])
        raise HTTPException(status_code=409, detail=error_message)

    return APIResponse(
        data={
            "id": str(analysis.id),
            "status": analysis.status,
            "processing_time_ms": analysis.processing_time_ms,
            "completed_at": analysis.completed_at,
        }
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
