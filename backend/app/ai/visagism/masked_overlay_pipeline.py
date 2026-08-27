"""Identity-safe haircut overlay orchestration for visagism.

The pipeline never regenerates the person. It edits only a validated hair mask,
verifies identity against real source photos, and fails closed to the original.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol

from .identity_lock import DEFAULT_IDENTITY_LOCK, IdentityLockPolicy


class MaskAdapter(Protocol):
    def build_hair_mask(self, original_photo: Any) -> Dict[str, Any]: ...


class OverlayRenderer(Protocol):
    def render(
        self,
        *,
        init_image: Any,
        reference_image: Any,
        mask: Any,
        edit_instruction: str,
        denoising: float,
        identity_weight: float,
    ) -> Any: ...


class IdentityVerifier(Protocol):
    def compare(self, candidate: Any, reference: Any) -> float: ...


@dataclass
class MaskedOverlayPipeline:
    mask_adapter: MaskAdapter
    renderer: OverlayRenderer
    verifier: IdentityVerifier
    policy: IdentityLockPolicy = DEFAULT_IDENTITY_LOCK

    def run(
        self,
        *,
        original_photo: Any,
        real_reference_photos: List[Any],
        edit_instruction: str,
        denoising: float = 0.30,
        identity_weight: float = 0.90,
    ) -> Dict[str, Any]:
        if (
            not self.policy.min_reference_validations
            <= len(real_reference_photos)
            <= self.policy.max_reference_validations
        ):
            return self._fallback(original_photo, "invalid_reference_count")
        if not self.policy.min_denoising <= denoising <= self.policy.max_denoising:
            return self._fallback(original_photo, "unsafe_denoising")
        if identity_weight < self.policy.min_identity_weight:
            return self._fallback(original_photo, "identity_weight_too_low")

        mask_result = self.mask_adapter.build_hair_mask(original_photo)
        if not mask_result.get("valid"):
            return self._fallback(
                original_photo, mask_result.get("reason") or "hair_mask_failed"
            )
        if mask_result.get("protected_regions_touched"):
            return self._fallback(original_photo, "protected_region_in_mask")
        if mask_result.get("beard_enabled") is True:
            return self._fallback(original_photo, "beard_region_not_allowed")
        if mask_result.get("background_locked") is not True:
            return self._fallback(original_photo, "background_lock_not_confirmed")

        candidate = self.renderer.render(
            init_image=original_photo,
            reference_image=original_photo,
            mask=mask_result["mask"],
            edit_instruction=edit_instruction,
            denoising=denoising,
            identity_weight=identity_weight,
        )

        scores = [
            self.verifier.compare(candidate, ref) for ref in real_reference_photos
        ]
        if any(score < self.policy.identity_threshold for score in scores):
            return self._fallback(
                original_photo,
                "identity_lock_failed",
                identity_scores=scores,
            )

        return {
            "image": candidate,
            "mode": "hair_overlay",
            "simulationApplied": True,
            "identityVerified": True,
            "identityScores": scores,
            "baseImagePreserved": True,
            "editableRegions": ["hair"],
            "mask": {
                "kind": mask_result.get("mask_kind"),
                "coverage_ratio": mask_result.get("coverage_ratio"),
                "background_locked": True,
                "beard_enabled": False,
            },
        }

    @staticmethod
    def _fallback(original_photo: Any, reason: str, **extra: Any) -> Dict[str, Any]:
        return {
            "image": original_photo,
            "mode": "original_plus_spec",
            "simulationApplied": False,
            "reason": reason,
            "baseImagePreserved": True,
            **extra,
        }
