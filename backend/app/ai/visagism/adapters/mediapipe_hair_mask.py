"""Fail-closed MediaPipe hair-region mask adapter for visagism V1.

V1 deliberately uses a conservative geometric ROI anchored to Face Mesh.
It is *not* semantic hair segmentation. If the geometry is uncertain, the
adapter returns ``valid=False`` so the simulation pipeline falls back to the
original photo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image


Landmark = Tuple[float, float]
LandmarkDetector = Callable[[np.ndarray], Optional[Sequence[Landmark]]]


@dataclass
class MediaPipeHairBeardMaskAdapter:
    """Build a conservative hair-only V1 mask from Face Mesh landmarks.

    The class keeps the historical ``HairBeard`` name for Protocol compatibility,
    but beard editing is intentionally disabled in V1 because the current
    IdentityLock policy forbids skin/jaw changes. A later semantic segmentation
    adapter can safely extend the editable region.
    """

    coverage_min: float = 0.03
    coverage_max: float = 0.45
    protected_overlap_max: float = 0.005
    side_expand_ratio: float = 0.15
    top_expand_ratio: float = 0.25
    detector: Optional[LandmarkDetector] = None

    # Face oval indices used elsewhere in the project (GroomingAnalyzer).
    FACE_OVAL: Tuple[int, ...] = (
        10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
        397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
        172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
    )
    LEFT_EYE: Tuple[int, ...] = (33, 246, 161, 160, 159, 158, 157, 173, 133)
    RIGHT_EYE: Tuple[int, ...] = (362, 398, 384, 385, 386, 387, 388, 466, 263)
    LEFT_EYEBROW: Tuple[int, ...] = (70, 63, 105, 66, 107, 55, 65, 52, 53, 46)
    RIGHT_EYEBROW: Tuple[int, ...] = (336, 296, 334, 293, 300, 276, 283, 282, 295, 285)
    NOSE: Tuple[int, ...] = (1, 2, 98, 327, 168, 195, 5, 4, 275, 440, 305)
    MOUTH: Tuple[int, ...] = (61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 17)

    def build_hair_beard_mask(self, original_photo: Any) -> Dict[str, Any]:
        rgb = self._to_rgb_array(original_photo)
        height, width = rgb.shape[:2]
        landmarks = self._detect_landmarks(rgb)
        if not landmarks:
            return self._invalid("face_not_detected", height, width)

        if max(self.FACE_OVAL) >= len(landmarks):
            return self._invalid("insufficient_landmarks", height, width)

        face_points = self._points(landmarks, self.FACE_OVAL, width, height)
        xs = face_points[:, 0]
        ys = face_points[:, 1]
        x_min, x_max = int(xs.min()), int(xs.max())
        y_min, y_max = int(ys.min()), int(ys.max())
        face_w = max(1, x_max - x_min)
        face_h = max(1, y_max - y_min)

        # Conservative V1: only the region above the upper face oval is editable.
        # This avoids forehead/skin by construction but may block valid haircuts;
        # those blocked cases are preferable to unsafe edits.
        roi_left = max(0, int(x_min - face_w * self.side_expand_ratio))
        roi_right = min(width, int(x_max + face_w * self.side_expand_ratio))
        roi_bottom = max(0, y_min)
        roi_top = max(0, int(y_min - face_h * self.top_expand_ratio))

        if roi_right <= roi_left or roi_bottom <= roi_top:
            return self._invalid("hair_roi_unreliable", height, width)

        mask = np.zeros((height, width), dtype=np.uint8)
        mask[roi_top:roi_bottom, roi_left:roi_right] = 255

        protected = np.zeros_like(mask)
        self._fill_polygon(protected, face_points, 255)
        for indices in (
            self.LEFT_EYE,
            self.RIGHT_EYE,
            self.LEFT_EYEBROW,
            self.RIGHT_EYEBROW,
            self.NOSE,
            self.MOUTH,
        ):
            pts = self._points_safe(landmarks, indices, width, height)
            if pts is not None:
                self._fill_polygon(protected, pts, 255)

        active = mask > 0
        active_count = int(active.sum())
        if active_count == 0:
            return self._invalid("hair_roi_empty", height, width)

        overlap_count = int(np.logical_and(active, protected > 0).sum())
        protected_overlap_ratio = overlap_count / active_count
        protected_touched = protected_overlap_ratio > self.protected_overlap_max

        # Coverage is relative to the conservative expanded head box, not the
        # full image, so distant background does not dilute the gate.
        head_top = roi_top
        head_bottom = max(roi_bottom, y_max)
        head_area = max(1, (roi_right - roi_left) * (head_bottom - head_top))
        coverage_ratio = active_count / head_area

        if coverage_ratio < self.coverage_min or coverage_ratio > self.coverage_max:
            return {
                **self._invalid("hair_roi_coverage_out_of_range", height, width),
                "coverage_ratio": float(coverage_ratio),
                "protected_overlap_ratio": float(protected_overlap_ratio),
            }
        if protected_touched:
            return {
                **self._invalid("protected_region_in_mask", height, width),
                "coverage_ratio": float(coverage_ratio),
                "protected_overlap_ratio": float(protected_overlap_ratio),
                "protected_regions_touched": True,
            }

        return {
            "valid": True,
            "mask": mask,
            "protected_regions_touched": False,
            "coverage_ratio": float(coverage_ratio),
            "protected_overlap_ratio": float(protected_overlap_ratio),
            "reason": None,
            "mask_kind": "geometric_hair_roi_v1",
            "beard_enabled": False,
            "calibration_status": "provisional",
        }

    def _detect_landmarks(self, rgb: np.ndarray) -> Optional[Sequence[Landmark]]:
        if self.detector is not None:
            return self.detector(rgb)
        try:
            import mediapipe as mp
        except ImportError:
            return None

        face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        )
        try:
            result = face_mesh.process(rgb)
        finally:
            face_mesh.close()
        if not result.multi_face_landmarks:
            return None
        return [(lm.x, lm.y) for lm in result.multi_face_landmarks[0].landmark]

    @staticmethod
    def _to_rgb_array(image: Any) -> np.ndarray:
        if isinstance(image, Image.Image):
            return np.asarray(image.convert("RGB"))
        if isinstance(image, np.ndarray):
            arr = image
            if arr.ndim != 3 or arr.shape[2] < 3:
                raise TypeError("mask adapter requires an RGB-like image")
            return arr[..., :3].astype(np.uint8, copy=False)
        raise TypeError("mask adapter requires PIL.Image or numpy.ndarray")

    @staticmethod
    def _points(
        landmarks: Sequence[Landmark], indices: Iterable[int], width: int, height: int
    ) -> np.ndarray:
        return np.array(
            [
                [
                    int(np.clip(landmarks[i][0] * width, 0, width - 1)),
                    int(np.clip(landmarks[i][1] * height, 0, height - 1)),
                ]
                for i in indices
            ],
            dtype=np.int32,
        )

    def _points_safe(
        self,
        landmarks: Sequence[Landmark],
        indices: Iterable[int],
        width: int,
        height: int,
    ) -> Optional[np.ndarray]:
        indices = tuple(indices)
        if not indices or max(indices) >= len(landmarks):
            return None
        return self._points(landmarks, indices, width, height)

    @staticmethod
    def _fill_polygon(mask: np.ndarray, points: np.ndarray, value: int) -> None:
        # OpenCV is already a project dependency and gives deterministic polygon fill.
        import cv2

        if len(points) >= 3:
            cv2.fillPoly(mask, [points.astype(np.int32)], value)

    @staticmethod
    def _invalid(reason: str, height: int, width: int) -> Dict[str, Any]:
        return {
            "valid": False,
            "mask": np.zeros((height, width), dtype=np.uint8),
            "protected_regions_touched": False,
            "coverage_ratio": 0.0,
            "protected_overlap_ratio": 0.0,
            "reason": reason,
            "mask_kind": "geometric_hair_roi_v1",
            "beard_enabled": False,
            "calibration_status": "provisional",
        }
