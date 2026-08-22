import asyncio
import io
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.visagism.adapters.deepface_identity import DeepFaceArcFaceVerifier
from app.ai.visagism.adapters.mediapipe_hair_mask import MediaPipeHairBeardMaskAdapter
from app.ai.visagism.simulation_service import VisagismSimulationService
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import Analysis, Photo
from app.schemas import APIResponse, AnalysisResponse

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])


class VisagismSimulationRequest(BaseModel):
    """Request a local fail-closed simulation preflight for one grounded haircut."""

    haircut_name: str = Field(..., min_length=1, max_length=200)


async def _download_pil_image(session: Any, url: str) -> Image.Image:
    """Download a repository-owned photo URL and decode it as RGB.

    The endpoint never sends the decoded image to a third-party renderer in V1;
    it is used only by local mask and identity gates.
    """
    async with session.get(url) as response:
        response.raise_for_status()
        raw = await response.read()
    with Image.open(io.BytesIO(raw)) as image:
        return image.convert("RGB").copy()


def _public_simulation_contract(
    *,
    analysis_id: UUID,
    haircut_name: str,
    original_url: str,
    reference_count: int,
    service_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Return only JSON-safe, user-facing fail-closed simulation state.

    The local endpoint deliberately has no renderer/provider configured. Even if
    a future code change accidentally hands back ``ready``, this boundary keeps
    the public API blocked until a separately reviewed provider-enabled endpoint
    is explicitly activated.
    """
    service_status = service_result.get("simulation_status")
    reason = service_result.get("reason") or "simulation_blocked"
    if service_status != "blocked":
        reason = "simulation_ready_not_enabled"

    return {
        "analysis_id": str(analysis_id),
        "selected_haircut": haircut_name,
        "simulation_status": "blocked",
        "reason": reason,
        "provider_configured": False,
        "ready_enabled": False,
        "reference_count": reference_count,
        "card_media": {
            "personPhoto": original_url,
            "displayImage": original_url,
            "displayMode": "original_plus_spec",
            "realPhotoRequired": True,
            "realPhotoVerified": True,
            "simulationApplied": False,
            "identityVerified": False,
            "fallbackUsed": True,
        },
    }


@router.get("", response_model=APIResponse)
async def list_analyses(
    photoshoot_id: Optional[UUID] = None,
    profile_id: Optional[UUID] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
    return APIResponse(data=AnalysisResponse.model_validate(analysis))


@router.get("/{analysis_id}/facial", response_model=APIResponse)
async def get_facial_analysis(
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
    return APIResponse(data=analysis.facial_structure)


@router.get("/{analysis_id}/visagism", response_model=APIResponse)
async def get_visagism_analysis(
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
    return APIResponse(data=analysis.visagism)


@router.post("/{analysis_id}/visagism/simulate", response_model=APIResponse)
async def simulate_visagism_haircut_fail_closed(
    analysis_id: UUID,
    request: VisagismSimulationRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run local simulation preflight while keeping user-visible state blocked.

    This V1 endpoint intentionally configures no inpainting renderer. It can run
    the local MediaPipe mask and ArcFace identity gates, but the public response
    always displays the original real photo and never activates ``ready``.
    """
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

    visagism = analysis.visagism if isinstance(analysis.visagism, dict) else {}
    grounded_haircuts = visagism.get("recommended_hairstyles") or []
    if request.haircut_name not in grounded_haircuts:
        raise HTTPException(
            status_code=400,
            detail="Haircut must belong to the grounded visagism recommendations",
        )

    photo_result = await db.execute(
        select(Photo)
        .where(
            and_(
                Photo.photoshoot_id == analysis.photoshoot_id,
                Photo.tenant_id == current_user.tenant_id,
            )
        )
        .order_by(Photo.created_at.asc())
    )
    photos = list(photo_result.scalars().all())
    if not photos:
        raise HTTPException(status_code=409, detail="Analysis has no source photos")

    original = next((photo for photo in photos if photo.id == analysis.photo_id), photos[0])
    reference_photos = [photo for photo in photos if photo.id != original.id][:5]

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            tasks = [_download_pil_image(session, original.url)] + [
                _download_pil_image(session, photo.url) for photo in reference_photos
            ]
            downloaded = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception:
        downloaded = [RuntimeError("photo_download_failed")]

    original_image = downloaded[0] if downloaded and not isinstance(downloaded[0], Exception) else None
    if original_image is None:
        safe = _public_simulation_contract(
            analysis_id=analysis_id,
            haircut_name=request.haircut_name,
            original_url=original.url,
            reference_count=0,
            service_result={
                "simulation_status": "blocked",
                "reason": "original_photo_download_failed",
            },
        )
        return APIResponse(data=safe, message="Simulation blocked safely")

    reference_images = [
        item for item in downloaded[1:] if not isinstance(item, Exception)
    ]
    source_images = [{"image": original_image}] + [
        {"image": image} for image in reference_images
    ]

    service = VisagismSimulationService(
        mask_adapter=MediaPipeHairBeardMaskAdapter(),
        verifier=DeepFaceArcFaceVerifier(),
        renderer=None,
    )
    service_result = service.simulate(
        original_photo=original_image,
        real_reference_photos=reference_images,
        source_photos=source_images,
        preferred_original=original_image,
        edit_instruction=request.haircut_name,
    )

    safe = _public_simulation_contract(
        analysis_id=analysis_id,
        haircut_name=request.haircut_name,
        original_url=original.url,
        reference_count=len(reference_images),
        service_result=service_result,
    )
    return APIResponse(data=safe, message="Local simulation preflight completed")


@router.get("/{analysis_id}/casting", response_model=APIResponse)
async def get_casting_analysis(
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
    return APIResponse(data=analysis.casting)
