"""Landmark-based facial measurements for the real visagism pipeline.

Measurements are normalized image-space ratios derived from MediaPipe FaceMesh
landmarks. They are not presented as centimetres because there is no physical
scale reference in a normal photograph.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

from app.ai.image_triage.engine import ImageTriageEngine


@dataclass(frozen=True)
class Measurement:
    value: Optional[float]
    unit: str
    confidence: float
    source: str
    status: str = "observed"

    def to_dict(self) -> Dict:
        return {
            "value": self.value,
            "unit": self.unit,
            "confidence": self.confidence,
            "source": self.source,
            "status": self.status,
        }


class FacialMeasurementEngine:
    """Calculate traceable facial ratios from full FaceMesh landmarks."""

    def __init__(self, triage_engine: Optional[ImageTriageEngine] = None) -> None:
        self.triage_engine = triage_engine or ImageTriageEngine()

    def analyze_image(self, image_path: str) -> Dict:
        img_array = np.array(Image.open(image_path).convert("RGB"))
        face = self.triage_engine._analyze_face(img_array)
        if not face.get("has_face", False):
            return {
                "face_detected": False,
                "measurements": {},
                "limitations": ["face_not_detected"],
                "evidence_source": "MediaPipe FaceLandmarker",
            }

        landmarks = face.get("landmarks", [])
        return self.from_landmarks(landmarks)

    @classmethod
    def from_landmarks(cls, landmarks: List[Dict]) -> Dict:
        if len(landmarks) < 468:
            return {
                "face_detected": False,
                "measurements": {},
                "limitations": ["insufficient_facemesh_landmarks"],
                "evidence_source": "MediaPipe FaceLandmarker",
            }

        face_width = cls._distance_2d(landmarks[234], landmarks[454])
        face_height = cls._distance_2d(landmarks[10], landmarks[152])
        interocular = cls._distance_2d(landmarks[33], landmarks[263])
        jaw_width = cls._distance_2d(landmarks[58], landmarks[288])
        mouth_width = cls._distance_2d(landmarks[61], landmarks[291])

        brow_y = (landmarks[105]["y"] + landmarks[334]["y"]) / 2.0
        top_y = landmarks[10]["y"]
        nose_y = landmarks[1]["y"]
        chin_y = landmarks[152]["y"]
        total_vertical = chin_y - top_y

        symmetry = cls._symmetry_score(landmarks)
        shape = cls._classify_shape(face_width, face_height, jaw_width)

        measurements = {
            "face_width": cls._measurement(face_width, "normalized_image_ratio"),
            "face_height": cls._measurement(face_height, "normalized_image_ratio"),
            "face_height_to_width": cls._safe_ratio(face_height, face_width),
            "interocular_distance": cls._measurement(
                interocular, "normalized_image_ratio"
            ),
            "jaw_width": cls._measurement(jaw_width, "normalized_image_ratio"),
            "jaw_to_face_width": cls._safe_ratio(jaw_width, face_width),
            "mouth_width": cls._measurement(mouth_width, "normalized_image_ratio"),
            "symmetry_score": cls._measurement(symmetry, "score_0_1", confidence=0.82),
        }

        if total_vertical > 1e-6:
            measurements.update(
                {
                    "upper_third": cls._measurement(
                        (brow_y - top_y) / total_vertical,
                        "face_height_ratio",
                        confidence=0.85,
                    ),
                    "middle_third": cls._measurement(
                        (nose_y - brow_y) / total_vertical,
                        "face_height_ratio",
                        confidence=0.85,
                    ),
                    "lower_third": cls._measurement(
                        (chin_y - nose_y) / total_vertical,
                        "face_height_ratio",
                        confidence=0.85,
                    ),
                }
            )

        return {
            "face_detected": True,
            "landmarks_count": len(landmarks),
            "measurements": {key: value.to_dict() for key, value in measurements.items()},
            "face_shape": {
                "value": shape,
                "confidence": 0.72,
                "source": "FaceMesh proportions heuristic",
                "status": "estimated",
            },
            "limitations": [
                "measurements_are_normalized_not_physical",
                "face_shape_is_heuristic_estimate",
            ],
            "evidence_source": "MediaPipe FaceLandmarker",
        }

    @staticmethod
    def _distance_2d(a: Dict, b: Dict) -> float:
        return float(np.hypot(a["x"] - b["x"], a["y"] - b["y"]))

    @classmethod
    def _safe_ratio(cls, numerator: float, denominator: float) -> Measurement:
        if denominator <= 1e-6:
            return Measurement(
                value=None,
                unit="ratio",
                confidence=0.0,
                source="MediaPipe FaceMesh landmarks",
                status="not_determinable",
            )
        return cls._measurement(numerator / denominator, "ratio")

    @staticmethod
    def _measurement(value: float, unit: str, confidence: float = 0.9) -> Measurement:
        return Measurement(
            value=round(float(value), 4),
            unit=unit,
            confidence=confidence,
            source="MediaPipe FaceMesh landmarks",
        )

    @staticmethod
    def _symmetry_score(landmarks: List[Dict]) -> float:
        pairs = ((33, 263), (133, 362), (61, 291), (234, 454), (58, 288))
        center_x = landmarks[1]["x"]
        scores = []
        for left_idx, right_idx in pairs:
            left_dist = abs(landmarks[left_idx]["x"] - center_x)
            right_dist = abs(landmarks[right_idx]["x"] - center_x)
            total = left_dist + right_dist
            if total > 1e-6:
                scores.append(1.0 - abs(left_dist - right_dist) / total)
        if not scores:
            return 0.0
        return float(np.clip(np.mean(scores), 0.0, 1.0))

    @staticmethod
    def _classify_shape(face_width: float, face_height: float, jaw_width: float) -> str:
        if face_width <= 1e-6:
            return "unknown"
        ratio = face_height / face_width
        jaw_ratio = jaw_width / face_width
        if ratio > 1.5:
            return "oblong"
        if ratio < 1.2 and jaw_ratio > 0.85:
            return "round"
        if jaw_ratio < 0.75:
            return "heart"
        if abs(ratio - 1.3) < 0.1 and jaw_ratio > 0.78:
            return "oval"
        if jaw_ratio > 0.88:
            return "square"
        return "mixed"
