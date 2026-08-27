"""AWS Rekognition identity verifier for visagism simulation.

This adapter avoids shipping a heavyweight local face-recognition runtime on
the free Render worker. AWS returns face similarity in [0, 100]; the adapter
normalizes that value to [0, 1] for IdentityLockPolicy.
"""

from __future__ import annotations

import io
from typing import Any, Optional

import boto3
import numpy as np
from PIL import Image

from app.config import settings


class AWSRekognitionIdentityVerifier:
    def __init__(self, client: Optional[Any] = None) -> None:
        self.client = client or boto3.client(
            "rekognition",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

    @staticmethod
    def _to_jpeg_bytes(image: Any) -> bytes:
        if isinstance(image, np.ndarray):
            pil = Image.fromarray(image.astype(np.uint8)).convert("RGB")
        elif isinstance(image, Image.Image):
            pil = image.convert("RGB")
        else:
            raise TypeError("identity verifier requires PIL.Image or numpy.ndarray")

        buffer = io.BytesIO()
        pil.save(buffer, format="JPEG", quality=95)
        return buffer.getvalue()

    def compare(self, candidate: Any, reference: Any) -> float:
        if candidate is reference:
            return 1.0
        try:
            response = self.client.compare_faces(
                SourceImage={"Bytes": self._to_jpeg_bytes(reference)},
                TargetImage={"Bytes": self._to_jpeg_bytes(candidate)},
                SimilarityThreshold=0,
                QualityFilter="AUTO",
            )
            matches = response.get("FaceMatches") or []
            if not matches:
                return 0.0
            similarity = max(float(item.get("Similarity") or 0.0) for item in matches)
            return max(0.0, min(1.0, similarity / 100.0))
        except Exception:
            # Identity publication must always fail closed on provider errors.
            return 0.0
