"""Hair-only adapter over the existing real GroomingAnalyzer.

The reproducible haircut pipeline only needs hair evidence. Running the full
skin/beard/eyebrow workflow couples haircut recommendations to unrelated
analysis stages, so this adapter reuses the same OpenCV + MediaPipe internals
but executes only the hair stage.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import cv2
import numpy as np

from app.ai.grooming.analyzer import GroomingAnalyzer


class GroomingHairEvidenceAdapter:
    """Extract the real hair metrics without executing unrelated grooming stages."""

    def __init__(self, analyzer: Optional[GroomingAnalyzer] = None) -> None:
        self.analyzer = analyzer or GroomingAnalyzer()

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return self._error("image_decode_failed")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.analyzer._face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(100, 100),
        )
        if len(faces) == 0:
            return self._error("face_not_detected")

        x, y, w, h = max(faces, key=lambda face: face[2] * face[3])
        landmarks = self.analyzer._get_mediapipe_landmarks(img)
        hair = self.analyzer._analyze_hair(
            img,
            gray,
            landmarks,
            int(x),
            int(y),
            int(w),
            int(h),
        )
        hair_dict = self.analyzer._hair_to_dict(hair)
        confidence = 0.9 if landmarks else 0.6

        return {
            "confidence": confidence,
            "landmarks_detected": landmarks is not None,
            "landmark_count": len(landmarks) if landmarks else 0,
            "dimensions": {"hair": hair_dict},
            "evidence_source": "GroomingAnalyzer._analyze_hair",
            "scope": "hair_only",
        }

    @staticmethod
    def _error(reason: str) -> Dict[str, Any]:
        return {
            "confidence": 0.0,
            "landmarks_detected": False,
            "dimensions": {},
            "evidence_source": "GroomingAnalyzer._analyze_hair",
            "scope": "hair_only",
            "error": reason,
        }
