import asyncio
import hashlib
import io
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.visagism.adapters.mediapipe_hair_mask import MediaPipeHairBeardMaskAdapter
from app.ai.visagism.barber_brief import build_barber_brief_for_haircut
from app.ai.visagism.interpretation import build_visagism_interpretation
from app.ai.visagism.prompt_builder import build_haircut_edit_instruction
from app.ai.visagism.runtime import create_simulation_runtime
from app.ai.visagism.simulation_cache import (
    cache_key,
    find_ready,
    object_key,
    ready_for_source,
    with_ready_entry,
)
from app.ai.visagism.simulation_service import VisagismSimulationService
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import Analysis, Photo
from app.schemas import APIResponse, AnalysisResponse
from app.services.storage_service import StorageService
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])
logger = get_logger(__name__)


class VisagismSimulationRequest(BaseModel):
    haircut_name: str = Field(..., min_length=1, max_length=200)


def _read_pil_storage_image(url: str) -> Image.Image:
    raw = StorageService.read_object_from_url(url)
    with Image.open(io.BytesIO(raw)) as image:
        return image.convert("RGB").copy()


def _pil_to_png_bytes(image: Any) -> bytes:
    if not isinstance(image, Image.Image):
        raise TypeError("simulation_output_must_be_pil_image")
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _presigned_source_url(url: str) -> str:
    try:
        key = urlparse(url).path.lstrip("/")
        if key:
            return StorageService.get_presigned_url(key, expires_in=3600)
    except Exception:
        pass
    return url


def _with_interpretation(visagism: Any) -> Dict[str, Any]:
    raw = dict(visagism) if isinstance(visagism, dict) else {}
    raw["interpretation"] = build_visagism_interpretation(raw)
    return raw


def _public_simulation_contract(
    *,
    analysis_id: UUID,
    haircut_name: str,
    original_url: str,
    display_url: Optional[str] = None,
    simulation_status: str = "blocked",
    reason: Optional[str] = None,
    provider_configured: bool = False,
    ready_enabled: bool = False,
    reference_count: int = 0,
    cached: bool = False,
    barber_brief: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ready = simulation_status == "ready" and bool(display_url)
    return {
        "analysis_id": str(analysis_id),
        "selected_haircut": haircut_name,
        "simulation_status": "ready" if ready else simulation_status,
        "reason": None if ready else reason or "simulation_blocked",
        "provider_configured": provider_configured,
        "ready_enabled": bool(ready_enabled or ready),
        "reference_count": reference_count,
        "cached": cached,
        "barber_brief": barber_brief,
        "card_media": {
            "personPhoto": original_url,
            "displayImage": display_url if ready else original_url,
            "displayMode": "validated_hair_overlay" if ready else "original_plus_spec",
            "realPhotoRequired": True,
            "realPhotoVerified": True,
            "simulationApplied": ready,
            "identityVerified": ready,
            "fallbackUsed": not ready,
        },
    }


def _advisory_lock_id(*parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).digest()[:8]
    value = int.from_bytes(digest, "big", signed=False)
    return value - (1 << 64) if value >= (1 << 63) else value


async def _try_simulation_lock(db: AsyncSession, lock_id: int) -> bool:
    result = await db.execute(
        text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}
    )
    return bool(result.scalar())


async def _release_simulation_lock(db: AsyncSession, lock_id: int) -> None:
    try:
        await db.execute(
            text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id}
        )
    except Exception:
        logger.exception("Failed to release visagism simulation advisory lock")


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
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis).where(
            and_(Analysis.id == analysis_id, Analysis.tenant_id == current_user.tenant_id)
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return APIResponse(data=_with_interpretation(analysis.visagism))


@router.get("/{analysis_id}/visagism/barber-brief", response_model=APIResponse)
async def get_visagism_barber_brief(
    analysis_id: UUID,
    haircut_name: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis).where(
            and_(Analysis.id == analysis_id, Analysis.tenant_id == current_user.tenant_id)
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    visagism = analysis.visagism if isinstance(analysis.visagism, dict) else {}
    if haircut_name:
        brief = build_barber_brief_for_haircut(visagism, haircut_name)
        if brief is None:
            raise HTTPException(
                status_code=400,
                detail="Haircut must belong to the grounded visagism recommendations",
            )
        return APIResponse(data=brief)

    interpretation = build_visagism_interpretation(visagism)
    return APIResponse(data=interpretation.get("barber_brief"))


@router.get("/{analysis_id}/visagism/simulations", response_model=APIResponse)
async def list_visagism_simulations(
    analysis_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis).where(
            and_(Analysis.id == analysis_id, Analysis.tenant_id == current_user.tenant_id)
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    photo_result = await db.execute(
        select(Photo).where(
            and_(Photo.id == analysis.photo_id, Photo.tenant_id == current_user.tenant_id)
        )
    )
    original = photo_result.scalar_one_or_none()
    if not original:
        return APIResponse(data=[])

    visagism = analysis.visagism if isinstance(analysis.visagism, dict) else {}
    original_url = _presigned_source_url(original.url)
    seen = set()
    public_items = []
    for item in ready_for_source(visagism, source_photo_id=str(original.id)):
        haircut_name = item.get("haircut_name")
        stored_key = item.get("object_key")
        if not isinstance(haircut_name, str) or haircut_name in seen or not stored_key:
            continue
        seen.add(haircut_name)
        try:
            display_url = StorageService.get_presigned_url(str(stored_key), expires_in=3600)
        except Exception:
            continue
        public_items.append(
            _public_simulation_contract(
                analysis_id=analysis.id,
                haircut_name=haircut_name,
                original_url=original_url,
                display_url=display_url,
                simulation_status="ready",
                ready_enabled=True,
                cached=True,
                barber_brief=build_barber_brief_for_haircut(visagism, haircut_name),
            )
        )
    return APIResponse(data=public_items)


@router.post("/{analysis_id}/visagism/simulate", response_model=APIResponse)
async def simulate_visagism_haircut(
    analysis_id: UUID,
    request: VisagismSimulationRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis).where(
            and_(Analysis.id == analysis_id, Analysis.tenant_id == current_user.tenant_id)
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
    barber_brief = build_barber_brief_for_haircut(visagism, request.haircut_name)

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
    source_photo_id = str(original.id)
    original_url = _presigned_source_url(original.url)

    # A previously approved simulation remains usable even if the external
    # provider is currently unavailable. This is the zero-cost reopen path.
    cached_any = find_ready(
        visagism,
        haircut_name=request.haircut_name,
        source_photo_id=source_photo_id,
    )
    if cached_any:
        try:
            display_url = StorageService.get_presigned_url(
                str(cached_any["object_key"]), expires_in=3600
            )
            return APIResponse(
                data=_public_simulation_contract(
                    analysis_id=analysis_id,
                    haircut_name=request.haircut_name,
                    original_url=original_url,
                    display_url=display_url,
                    simulation_status="ready",
                    ready_enabled=True,
                    cached=True,
                    barber_brief=barber_brief,
                ),
                message="Cached simulation loaded",
            )
        except Exception:
            logger.warning("Cached simulation object could not be signed; regenerating")

    runtime = create_simulation_runtime()
    if not runtime.provider_configured:
        return APIResponse(
            data=_public_simulation_contract(
                analysis_id=analysis_id,
                haircut_name=request.haircut_name,
                original_url=original_url,
                reason="inpaint_provider_not_configured",
                provider_configured=False,
                barber_brief=barber_brief,
            ),
            message="Simulation blocked safely",
        )
    if not runtime.identity_configured or runtime.verifier is None:
        return APIResponse(
            data=_public_simulation_contract(
                analysis_id=analysis_id,
                haircut_name=request.haircut_name,
                original_url=original_url,
                reason="identity_verifier_not_configured",
                provider_configured=True,
                barber_brief=barber_brief,
            ),
            message="Simulation blocked safely",
        )

    # The normal mobile flow has three real photos total. The original source
    # is also a legitimate identity reference, giving the required 3 refs.
    selected_photos = [original] + [photo for photo in photos if photo.id != original.id][:4]
    downloaded = await asyncio.gather(
        *[asyncio.to_thread(_read_pil_storage_image, photo.url) for photo in selected_photos],
        return_exceptions=True,
    )
    original_image = downloaded[0] if downloaded and not isinstance(downloaded[0], Exception) else None
    if original_image is None:
        return APIResponse(
            data=_public_simulation_contract(
                analysis_id=analysis_id,
                haircut_name=request.haircut_name,
                original_url=original_url,
                reason="original_photo_download_failed",
                provider_configured=True,
                barber_brief=barber_brief,
            ),
            message="Simulation blocked safely",
        )

    reference_images = [
        item for item in downloaded if not isinstance(item, Exception)
    ]
    if not 3 <= len(reference_images) <= 5:
        return APIResponse(
            data=_public_simulation_contract(
                analysis_id=analysis_id,
                haircut_name=request.haircut_name,
                original_url=original_url,
                reason="invalid_reference_count",
                provider_configured=True,
                reference_count=len(reference_images),
                barber_brief=barber_brief,
            ),
            message="Simulation blocked safely",
        )

    exact_key = cache_key(
        haircut_name=request.haircut_name,
        source_photo_id=source_photo_id,
        provider=runtime.provider,
        model=runtime.model,
    )
    lock_id = _advisory_lock_id(
        str(current_user.tenant_id), str(analysis_id), exact_key
    )
    if not await _try_simulation_lock(db, lock_id):
        return APIResponse(
            data=_public_simulation_contract(
                analysis_id=analysis_id,
                haircut_name=request.haircut_name,
                original_url=original_url,
                simulation_status="processing",
                reason="simulation_in_progress",
                provider_configured=True,
                reference_count=len(reference_images),
                barber_brief=barber_brief,
            ),
            message="Simulation already in progress",
        )

    try:
        await db.refresh(analysis)
        visagism = analysis.visagism if isinstance(analysis.visagism, dict) else {}
        cached_exact = find_ready(
            visagism,
            haircut_name=request.haircut_name,
            source_photo_id=source_photo_id,
            provider=runtime.provider,
            model=runtime.model,
        )
        if cached_exact:
            display_url = StorageService.get_presigned_url(
                str(cached_exact["object_key"]), expires_in=3600
            )
            return APIResponse(
                data=_public_simulation_contract(
                    analysis_id=analysis_id,
                    haircut_name=request.haircut_name,
                    original_url=original_url,
                    display_url=display_url,
                    simulation_status="ready",
                    provider_configured=True,
                    ready_enabled=True,
                    reference_count=len(reference_images),
                    cached=True,
                    barber_brief=barber_brief,
                ),
                message="Cached simulation loaded",
            )

        source_images = [{"image": image} for image in reference_images]
        service = VisagismSimulationService(
            mask_adapter=MediaPipeHairBeardMaskAdapter(),
            verifier=runtime.verifier,
            renderer=runtime.renderer,
        )
        instruction = build_haircut_edit_instruction(request.haircut_name, visagism)
        service_result = await asyncio.to_thread(
            service.simulate,
            original_photo=original_image,
            real_reference_photos=reference_images,
            source_photos=source_images,
            preferred_original=original_image,
            edit_instruction=instruction,
        )

        if service_result.get("simulation_status") != "ready":
            reason = str(service_result.get("reason") or "simulation_blocked")
            logger.info(
                "Visagism simulation blocked analysis=%s haircut=%s provider=%s reason=%s",
                analysis_id,
                request.haircut_name,
                runtime.provider,
                reason,
            )
            return APIResponse(
                data=_public_simulation_contract(
                    analysis_id=analysis_id,
                    haircut_name=request.haircut_name,
                    original_url=original_url,
                    reason=reason,
                    provider_configured=True,
                    reference_count=len(reference_images),
                    barber_brief=barber_brief,
                ),
                message="Simulation blocked safely",
            )

        card_media = service_result.get("card_media") or {}
        simulated_image = card_media.get("displayImage")
        raw_png = _pil_to_png_bytes(simulated_image)
        stored_key = object_key(
            tenant_id=str(current_user.tenant_id),
            analysis_id=str(analysis_id),
            key=exact_key,
        )
        await StorageService.upload_file(raw_png, stored_key, content_type="image/png")

        scores = [float(score) for score in service_result.get("identity_scores") or []]
        min_score = min(scores) if scores else 0.0
        mask_meta = service_result.get("mask") if isinstance(service_result.get("mask"), dict) else {}
        analysis.visagism = with_ready_entry(
            visagism,
            key=exact_key,
            haircut_name=request.haircut_name,
            source_photo_id=source_photo_id,
            provider=runtime.provider,
            model=runtime.model,
            stored_object_key=stored_key,
            identity_score_min=min_score,
            mask_kind=mask_meta.get("kind"),
        )
        await db.commit()

        display_url = StorageService.get_presigned_url(stored_key, expires_in=3600)
        logger.info(
            "Visagism simulation ready analysis=%s haircut=%s provider=%s cached=false",
            analysis_id,
            request.haircut_name,
            runtime.provider,
        )
        return APIResponse(
            data=_public_simulation_contract(
                analysis_id=analysis_id,
                haircut_name=request.haircut_name,
                original_url=original_url,
                display_url=display_url,
                simulation_status="ready",
                provider_configured=True,
                ready_enabled=True,
                reference_count=len(reference_images),
                cached=False,
                barber_brief=barber_brief,
            ),
            message="Simulation completed successfully",
        )
    finally:
        await _release_simulation_lock(db, lock_id)


@router.get("/{analysis_id}/casting", response_model=APIResponse)
async def get_casting_analysis(
    analysis_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
