"""Fail-closed identity lock for visagism simulations.

The original photograph is immutable. A simulated image may be published only
when an external renderer reports that it edited hair/beard only AND an
identity verifier confirms the face stayed above the configured threshold.

This module deliberately does not fake segmentation, embeddings, or scores.
Production adapters (MediaPipe/InsightFace/RetinaFace + masked inpainting) must
supply those results explicitly.
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class IdentityLockPolicy:
    identity_threshold: float = 0.80
    min_identity_weight: float = 0.85
    min_denoising: float = 0.25
    max_denoising: float = 0.40

    def generation_constraints(self) -> Dict[str, Any]:
        return {
            "base_image_immutable": True,
            "editable_regions": ["hair", "beard"],
            "forbidden_regions": [
                "eyes", "nose", "mouth", "jaw", "ears", "neck", "skin", "background"
            ],
            "mask_required": True,
            "reference_image": "original",
            "denoising_range": [self.min_denoising, self.max_denoising],
            "identity_lock_required": True,
            "identity_weight_min": self.min_identity_weight,
            "identity_validation_required": True,
            "identity_threshold": self.identity_threshold,
            "failure_mode": "original_photo_with_technical_specification",
        }

    def decide_publication(
        self,
        *,
        original_photo: Any,
        simulated_photo: Optional[Any] = None,
        identity_similarity: Optional[float] = None,
        mask_valid: bool = False,
        protected_regions_unchanged: bool = False,
    ) -> Dict[str, Any]:
        valid_score = (
            identity_similarity is not None
            and identity_similarity >= self.identity_threshold
        )
        publish_simulation = bool(
            simulated_photo is not None
            and mask_valid
            and protected_regions_unchanged
            and valid_score
        )

        if publish_simulation:
            return {
                "mode": "simulated",
                "photo": simulated_photo,
                "identity_verified": True,
                "identity_similarity": identity_similarity,
            }

        return {
            "mode": "original",
            "photo": original_photo,
            "identity_verified": False,
            "identity_similarity": identity_similarity,
            "simulation_blocked": True,
            "reason": "Identity lock validation failed or was unavailable",
        }


DEFAULT_IDENTITY_LOCK = IdentityLockPolicy()
