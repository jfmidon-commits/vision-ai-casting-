"""Concrete local adapters for identity-safe visagism simulation.

These adapters intentionally fail closed. They do not enable remote inpainting
by themselves; the ready state remains unavailable until a provider is
explicitly configured and validated.
"""

from .deepface_identity import DeepFaceArcFaceVerifier
from .mediapipe_hair_mask import MediaPipeHairBeardMaskAdapter

__all__ = [
    "DeepFaceArcFaceVerifier",
    "MediaPipeHairBeardMaskAdapter",
]
