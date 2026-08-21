"""Fail-closed identity lock for visagism simulations.

Golden rule: NEVER regenerate the person. The original photo is the immutable
base layer. Only hair and beard overlays may be changed. Face, body, clothing
and background remain untouched. If any identity validation is missing or
fails, the system MUST publish the original photo plus the technical spec.

This module does not invent masks, embeddings, scores, or image edits.
Production adapters must provide real segmentation/inpainting and real identity
similarity values (e.g. MediaPipe/InsightFace/RetinaFace + ArcFace/InsightFace).
"""
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class IdentityLockPolicy:
    identity_threshold: float = 0.80
    min_identity_weight: float = 0.85
    min_denoising: float = 0.25
    max_denoising: float = 0.40
    min_reference_validations: int = 3
    max_reference_validations: int = 5

    def generation_constraints(self) -> Dict[str, Any]:
        """Contract that every renderer must obey before generation starts."""
        return {
            "never_generate_person_from_scratch": True,
            "init_image_required": True,
            "reference_image_required": True,
            "init_image": "original_photo",
            "reference_image": "original_photo",
            "base_image_immutable": True,
            "card_layers": {
                "layer_1": "original_photo_immutable",
                "layer_2": "optional_hair_beard_overlay_only",
            },
            "editable_regions": ["hair", "beard"],
            "forbidden_regions": [
                "eyes",
                "eyebrows",
                "nose",
                "mouth",
                "teeth",
                "jaw",
                "ears",
                "neck",
                "skin",
                "face_shape",
                "head_shape",
                "body",
                "shoulders",
                "clothing",
                "background",
            ],
            "mask_required": True,
            "mask_scope": "hair_and_beard_only",
            "denoising_range": [self.min_denoising, self.max_denoising],
            "identity_lock_required": True,
            "identity_weight_min": self.min_identity_weight,
            "identity_validation_required": True,
            "identity_threshold": self.identity_threshold,
            "reference_validation_count": [
                self.min_reference_validations,
                self.max_reference_validations,
            ],
            "all_reference_validations_must_pass": True,
            "publish_similar_face_forbidden": True,
            "failure_mode": "original_plus_spec",
        }

    def _validate_reference_scores(
        self, identity_scores: Optional[Iterable[float]]
    ) -> Dict[str, Any]:
        if identity_scores is None:
            return {"valid": False, "scores": [], "reason": "identity_scores_missing"}

        scores: List[float] = list(identity_scores)
        count_valid = self.min_reference_validations <= len(scores) <= self.max_reference_validations
        threshold_valid = bool(scores) and all(
            score >= self.identity_threshold for score in scores
        )
        return {
            "valid": bool(count_valid and threshold_valid),
            "scores": scores,
            "count_valid": count_valid,
            "threshold_valid": threshold_valid,
            "reason": None if count_valid and threshold_valid else "identity_lock_failed",
        }

    def decide_publication(
        self,
        *,
        original_photo: Any,
        simulated_photo: Optional[Any] = None,
        identity_scores: Optional[Iterable[float]] = None,
        mask_valid: bool = False,
        protected_regions_unchanged: bool = False,
        body_unchanged: bool = False,
    ) -> Dict[str, Any]:
        """Allow simulation only when EVERY protection and identity check passes."""
        validation = self._validate_reference_scores(identity_scores)
        publish_simulation = bool(
            simulated_photo is not None
            and mask_valid
            and protected_regions_unchanged
            and body_unchanged
            and validation["valid"]
        )

        audit_event = {
            "event": "visagism_identity_validation",
            "identity_threshold": self.identity_threshold,
            "identity_scores": validation["scores"],
            "mask_valid": mask_valid,
            "protected_regions_unchanged": protected_regions_unchanged,
            "body_unchanged": body_unchanged,
            "simulation_allowed": publish_simulation,
        }

        if publish_simulation:
            return {
                "image": simulated_photo,
                "mode": "hair_beard_overlay",
                "simulationApplied": True,
                "identityVerified": True,
                "identityScores": validation["scores"],
                "layers": {
                    "base": original_photo,
                    "overlay": simulated_photo,
                },
                "audit": audit_event,
            }

        # Explicit fail-closed fallback. Never publish a merely similar person.
        return {
            "image": original_photo,
            "mode": "original_plus_spec",
            "simulationApplied": False,
            "identityVerified": False,
            "identityScores": validation["scores"],
            "reason": "identity_lock_failed",
            "simulationBlocked": True,
            "layers": {
                "base": original_photo,
                "overlay": None,
            },
            "audit": audit_event,
        }


DEFAULT_IDENTITY_LOCK = IdentityLockPolicy()
