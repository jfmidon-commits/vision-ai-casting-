"""DeepFace ArcFace identity verifier for visagism simulation V1.

The adapter returns a *normalized decision score* aligned to the existing
IdentityLock threshold. It is not a native biometric similarity metric.

DeepFace ArcFace + cosine uses a native same-person decision threshold around
0.68. V1 maps distance==threshold to score==0.80 so the existing fail-closed
IdentityLock decision remains equivalent without changing identity_lock.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import numpy as np
from PIL import Image


VerifyCallable = Callable[[Any, Any], Dict[str, Any]]


@dataclass
class DeepFaceArcFaceVerifier:
    """Compare a candidate against a real reference using ArcFace/cosine."""

    native_threshold: float = 0.68
    policy_boundary_score: float = 0.80
    verify_func: Optional[VerifyCallable] = None

    def compare(self, candidate: Any, reference: Any) -> float:
        """Return normalized_identity_score in [0,1], or 0.0 on any failure."""
        details = self.compare_with_details(candidate, reference)
        return float(details["normalized_identity_score"])

    def compare_with_details(self, candidate: Any, reference: Any) -> Dict[str, Any]:
        try:
            result = self._verify(candidate, reference)
            distance = float(result["distance"])
            threshold = float(result.get("threshold") or self.native_threshold)
            if not np.isfinite(distance) or threshold <= 0:
                raise ValueError("invalid ArcFace distance/threshold")

            score = self.normalize_distance(distance, threshold)
            verified = bool(distance <= threshold)
            return {
                "normalized_identity_score": score,
                "distance": distance,
                "native_threshold": threshold,
                "native_verified": verified,
                "model": "ArcFace",
                "distance_metric": "cosine",
                "score_semantics": "normalized_decision_score_not_biometric_similarity",
                "calibration_status": "provisional_domain_calibration_required",
            }
        except Exception as exc:  # fail closed on import/detection/model errors
            return {
                "normalized_identity_score": 0.0,
                "distance": None,
                "native_threshold": self.native_threshold,
                "native_verified": False,
                "model": "ArcFace",
                "distance_metric": "cosine",
                "score_semantics": "normalized_decision_score_not_biometric_similarity",
                "calibration_status": "provisional_domain_calibration_required",
                "reason": "identity_verification_failed",
                "error_type": type(exc).__name__,
            }

    def normalize_distance(self, distance: float, threshold: Optional[float] = None) -> float:
        """Map native ArcFace decision boundary to the policy's 0.80 boundary.

        This mapping preserves the binary decision:
        normalized_score >= 0.80 iff distance <= native threshold.
        """
        threshold = float(threshold or self.native_threshold)
        if threshold <= 0:
            return 0.0
        score = 1.0 - (float(distance) / threshold) * (1.0 - self.policy_boundary_score)
        return float(np.clip(score, 0.0, 1.0))

    def _verify(self, candidate: Any, reference: Any) -> Dict[str, Any]:
        if self.verify_func is not None:
            return self.verify_func(candidate, reference)

        try:
            from deepface import DeepFace
        except ImportError as exc:
            raise RuntimeError("deepface_not_installed") from exc

        # DeepFace accepts paths, numpy arrays and several image-like inputs.
        candidate_input = self._deepface_input(candidate)
        reference_input = self._deepface_input(reference)
        return DeepFace.verify(
            img1_path=candidate_input,
            img2_path=reference_input,
            model_name="ArcFace",
            distance_metric="cosine",
            enforce_detection=True,
            silent=True,
        )

    @staticmethod
    def _deepface_input(image: Any) -> Any:
        if isinstance(image, Image.Image):
            return np.asarray(image.convert("RGB"))
        if isinstance(image, np.ndarray):
            return image
        return image
