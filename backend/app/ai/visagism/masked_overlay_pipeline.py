"""Identity-safe visual overlay orchestration for visagism.

This module does not generate a face. It orchestrates external adapters that must:
1) derive a mask limited to hair/beard,
2) edit only that mask using the original image as init/reference,
3) validate identity against 3-5 real references,
4) fail closed to the untouched original image.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Protocol

from .identity_lock import DEFAULT_IDENTITY_LOCK, IdentityLockPolicy


class MaskAdapter(Protocol):
    def build_hair_beard_mask(self, original_photo: Any) -> Dict[str, Any]: ...


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
        if not 3 <= len(real_reference_photos) <= 5:
            return self._fallback(original_photo, "invalid_reference_count")
        if not self.policy.min_denoising <= denoising <= self.policy.max_denoising:
            return self._fallback(original_photo, "unsafe_denoising")
        if identity_weight < self.policy.min_identity_weight:
            return self._fallback(original_photo, "identity_weight_too_low")

        mask_result = self.mask_adapter.build_hair_beard_mask(original_photo)
        if not mask_result.get("valid"):
            return self._fallback(original_photo, "hair_beard_mask_failed")
        if mask_result.get("protected_regions_touched"):
            return self._fallback(original_photo, "protected_region_in_mask")

        candidate = self.renderer.render(
            init_image=original_photo,
            reference_image=original_photo,
            mask=mask_result["mask"],
            edit_instruction=edit_instruction,
            denoising=denoising,
            identity_weight=identity_weight,
        )

        scores = [self.verifier.compare(candidate, ref) for ref in real_reference_photos]
        if any(score < self.policy.identity_threshold for score in scores):
            return self._fallback(
                original_photo,
                "identity_lock_failed",
                identity_scores=scores,
            )

        return {
            "image": candidate,
            "mode": "hair_beard_overlay",
            "simulationApplied": True,
            "identityVerified": True,
            "identityScores": scores,
            "baseImagePreserved": True,
            "editableRegions": ["hair", "beard"],
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
