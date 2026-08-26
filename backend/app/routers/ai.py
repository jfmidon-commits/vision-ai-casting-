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
from app.schemas import APIResponse, AnalysisCreate, AnalysisProgress
from app.services.ai_service import AIService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

ANALYSIS_TIMEOUT_SECONDS = 300


async def _mark_analysis_failed(analysis_id: str, error_message: str) -> None:
    """Persist a terminal failure so analyses never remain stuck in processing."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
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
        logger.exception("Failed to persist terminal state for analysis %s", analysis_id)


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
        logger.error("Analysis %s timed out after %ss", analysis_id, ANALYSIS_TIMEOUT_SECONDS)
        await _mark_analysis_failed(analysis_id, message)
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        logger.exception("Analysis %s pipeline failed: %s", analysis_id, message)
        await _mark_analysis_failed(analysis_id, message)


@router.post("/analyze", response_model=APIResponse)
async def analyze_photoshoot(
    request: AnalysisCreate,
    background_tasks: BackgroundTasks,
    photoshoot_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start an AI analysis for a photoshoot."""
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

    photo_result = await db.execute(select(Photo).where(Photo.photoshoot_id == photoshoot_id))
    photos = photo_result.scalars().all()
    if not photos:
        raise HTTPException(status_code=400, detail="No photos found for photoshoot")

    analysis = Analysis(
        photoshoot_id=photoshoot_id,
        tenant_id=current_user.tenant_id,
        status="queued",
        analysis_types=request.analysis_types,
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    logger.info(
        "Analysis %s queued for photoshoot %s types=%s",
        analysis.id,
        photoshoot_id,
        request.analysis_types,
    )

    background_tasks.add_task(
        _run_analysis_safely,
        str(analysis.id),
        str(photoshoot_id),
        request.analysis_types,
        str(current_user.tenant_id),
    )

    return APIResponse(
        success=True,
        data={"analysis_id": str(analysis.id), "status": analysis.status},
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
        pipeline_error = None
        if isinstance(analysis.raw_results, dict):
            pipeline_error = analysis.raw_results.get("pipeline_error")
        detail = (
            pipeline_error.get("message")
            if isinstance(pipeline_error, dict)
            else "Analysis failed"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    return APIResponse(
        success=True,
        data={
            "analysis_id": str(analysis.id),
            "status": analysis.status,
            "progress": 100 if analysis.status == "completed" else 50 if analysis.status == "processing" else 0,
            "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        },
    )
