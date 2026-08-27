"""Fail-closed orchestration for identity-safe haircut simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .card_photo_guard import DEFAULT_CARD_PHOTO_GUARD, CardPhotoGuard
from .identity_lock import DEFAULT_IDENTITY_LOCK, IdentityLockPolicy
from .masked_overlay_pipeline import (
    IdentityVerifier,
    MaskAdapter,
    MaskedOverlayPipeline,
    OverlayRenderer,
)
from .pixel_locked_renderer import PixelLockedRenderer


@dataclass
class VisagismSimulationService:
    mask_adapter: MaskAdapter
    verifier: IdentityVerifier
    renderer: Optional[OverlayRenderer] = None
    policy: IdentityLockPolicy = DEFAULT_IDENTITY_LOCK
    card_guard: CardPhotoGuard = DEFAULT_CARD_PHOTO_GUARD

    def preflight(
        self,
        *,
        original_photo: Any,
        real_reference_photos: List[Any],
    ) -> Dict[str, Any]:
        if (
            not self.policy.min_reference_validations
            <= len(real_reference_photos)
            <= self.policy.max_reference_validations
        ):
            return {
                "eligible": False,
                "reason": "invalid_reference_count",
                "mask": None,
                "reference_identity_scores": [],
            }

        mask_result = self.mask_adapter.build_hair_mask(original_photo)
        if not mask_result.get("valid"):
            return {
                "eligible": False,
                "reason": mask_result.get("reason") or "hair_mask_failed",
                "mask": mask_result,
                "reference_identity_scores": [],
            }
        if mask_result.get("protected_regions_touched"):
            return {
                "eligible": False,
                "reason": "protected_region_in_mask",
                "mask": mask_result,
                "reference_identity_scores": [],
            }
        if mask_result.get("beard_enabled") is True:
            return {
                "eligible": False,
                "reason": "beard_region_not_allowed",
                "mask": mask_result,
                "reference_identity_scores": [],
            }
        if mask_result.get("background_locked") is not True:
            return {
                "eligible": False,
                "reason": "background_lock_not_confirmed",
                "mask": mask_result,
                "reference_identity_scores": [],
            }

        scores = [
            1.0 if ref is original_photo else self.verifier.compare(original_photo, ref)
            for ref in real_reference_photos
        ]
        if any(score < self.policy.identity_threshold for score in scores):
            return {
                "eligible": False,
                "reason": "reference_identity_gate_failed",
                "mask": mask_result,
                "reference_identity_scores": scores,
            }

        return {
            "eligible": True,
            "reason": None,
            "mask": mask_result,
            "reference_identity_scores": scores,
        }

    def simulate(
        self,
        *,
        original_photo: Any,
        real_reference_photos: List[Any],
        source_photos: Iterable[Mapping[str, Any]],
        edit_instruction: str,
        preferred_original: Optional[Any] = None,
        denoising: float = 0.30,
        identity_weight: float = 0.90,
        preflight_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if self.renderer is None:
            return self._blocked(
                source_photos=source_photos,
                preferred_original=preferred_original,
                reason="inpaint_provider_not_configured",
            )

        preflight = (
            dict(preflight_result)
            if isinstance(preflight_result, dict)
            else self.preflight(
                original_photo=original_photo,
                real_reference_photos=real_reference_photos,
            )
        )
        if not preflight.get("eligible"):
            return self._blocked(
                source_photos=source_photos,
                preferred_original=preferred_original,
                reason=str(preflight.get("reason") or "simulation_blocked"),
                diagnostics={"preflight": preflight},
            )

        pixel_locked = PixelLockedRenderer(delegate=self.renderer)
        pipeline = MaskedOverlayPipeline(
            mask_adapter=self.mask_adapter,
            renderer=pixel_locked,
            verifier=self.verifier,
            policy=self.policy,
        )
        try:
            result = pipeline.run(
                original_photo=original_photo,
                real_reference_photos=real_reference_photos,
                edit_instruction=edit_instruction,
                denoising=denoising,
                identity_weight=identity_weight,
                validated_mask_result=(
                    preflight.get("mask")
                    if isinstance(preflight.get("mask"), dict)
                    else None
                ),
            )
        except Exception as exc:
            reason = getattr(exc, "reason_code", "simulation_pipeline_error")
            return self._blocked(
                source_photos=source_photos,
                preferred_original=preferred_original,
                reason=reason,
                diagnostics={
                    "preflight": preflight,
                    "error_type": type(exc).__name__,
                },
            )

        if not result.get("simulationApplied"):
            return self._blocked(
                source_photos=source_photos,
                preferred_original=preferred_original,
                reason=result.get("reason") or "simulation_blocked",
                diagnostics={"preflight": preflight, "pipeline": result},
            )

        publication = self.policy.decide_publication(
            original_photo=original_photo,
            simulated_photo=result.get("image"),
            identity_scores=result.get("identityScores"),
            mask_valid=True,
            protected_regions_unchanged=True,
            body_unchanged=True,
        )
        card_media = self.card_guard.build_card_media(
            photos=source_photos,
            publication=publication,
            preferred_original=preferred_original,
        )

        if not card_media.get("simulationApplied"):
            return {
                "simulation_status": "blocked",
                "reason": card_media.get("reason") or "card_photo_guard_blocked",
                "card_media": card_media,
                "diagnostics": {"preflight": preflight},
            }

        return {
            "simulation_status": "ready",
            "reason": None,
            "card_media": card_media,
            "identity_scores": result.get("identityScores", []),
            "mask": result.get("mask") or {},
            "diagnostics": {"preflight": preflight},
        }

    def not_requested(
        self,
        *,
        source_photos: Iterable[Mapping[str, Any]],
        preferred_original: Optional[Any] = None,
    ) -> Dict[str, Any]:
        card_media = self.card_guard.build_card_media(
            photos=source_photos,
            preferred_original=preferred_original,
        )
        return {
            "simulation_status": "not_requested",
            "reason": None,
            "card_media": card_media,
        }

    def _blocked(
        self,
        *,
        source_photos: Iterable[Mapping[str, Any]],
        preferred_original: Optional[Any],
        reason: str,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        original = self.card_guard.select_person_photo(
            source_photos, preferred_original
        )
        publication = {
            "image": original,
            "mode": "original_plus_spec",
            "simulationApplied": False,
            "identityVerified": False,
            "simulationBlocked": True,
            "reason": reason,
            "layers": {"base": original, "overlay": None},
        }
        card_media = self.card_guard.build_card_media(
            photos=source_photos,
            publication=publication,
            preferred_original=preferred_original,
        )
        return {
            "simulation_status": "blocked",
            "reason": reason,
            "card_media": card_media,
            "diagnostics": diagnostics or {},
        }
