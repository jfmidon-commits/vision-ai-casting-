"""Fail-closed MediaPipe hair-only mask adapter for visagism simulation.

The mask combines a conservative Face Mesh hair ROI with person segmentation.
Only pixels that belong to the person AND sit above the protected face oval are
editable. Beard, face and background remain outside the haircut mask.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

Landmark = Tuple[float, float]
LandmarkDetector = Callable[[np.ndarray], Optional[Sequence[Landmark]]]
PersonSegmenter = Callable[[np.ndarray], Optional[np.ndarray]]


@dataclass
class MediaPipeHairBeardMaskAdapter:
    """Build a conservative hair-only mask.

    The historical class name is retained for compatibility. Beard editing is
    intentionally disabled. ``build_hair_beard_mask`` remains as a temporary
    alias for older callers and returns the same hair-only result.

    All expensive mask construction now runs on a bounded working image. This
    is important on the Render free worker because phone photos can be 10-20 MP
    and a full-resolution float32 segmentation map alone can consume tens of
    megabytes. Only the final uint8 mask is restored to source resolution.
    """

    coverage_min: float = 0.02
    coverage_max: float = 0.45
    protected_overlap_max: float = 0.002
    side_expand_ratio: float = 0.15
    top_expand_ratio: float = 0.30
    person_threshold: float = 0.70
    inference_max_side: int = 512
    detector: Optional[LandmarkDetector] = None
    person_segmenter: Optional[PersonSegmenter] = None

    FACE_OVAL: Tuple[int, ...] = (
        10,
        338,
        297,
        332,
        284,
        251,
        389,
        356,
        454,
        323,
        361,
        288,
        397,
        365,
        379,
        378,
        400,
        377,
        152,
        148,
        176,
        149,
        150,
        136,
        172,
        58,
        132,
        93,
        234,
        127,
        162,
        21,
        54,
        103,
        67,
        109,
    )
    LEFT_EYE: Tuple[int, ...] = (33, 246, 161, 160, 159, 158, 157, 173, 133)
    RIGHT_EYE: Tuple[int, ...] = (362, 398, 384, 385, 386, 387, 388, 466, 263)
    LEFT_EYEBROW: Tuple[int, ...] = (70, 63, 105, 66, 107, 55, 65, 52, 53, 46)
    RIGHT_EYEBROW: Tuple[int, ...] = (336, 296, 334, 293, 300, 276, 283, 282, 295, 285)
    NOSE: Tuple[int, ...] = (1, 2, 98, 327, 168, 195, 5, 4, 275, 440, 305)
    MOUTH: Tuple[int, ...] = (61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 17)

    def build_hair_mask(self, original_photo: Any) -> Dict[str, Any]:
        rgb, source_height, source_width = self._prepare_working_rgb(original_photo)
        height, width = rgb.shape[:2]
        landmarks = self._detect_landmarks(rgb)
        if not landmarks:
            return self._invalid("face_not_detected", source_height, source_width)
        if max(self.FACE_OVAL) >= len(landmarks):
            return self._invalid("insufficient_landmarks", source_height, source_width)

        person_probability = self._segment_person(rgb)
        if person_probability is None or person_probability.shape != (height, width):
            return self._invalid(
                "person_segmentation_failed", source_height, source_width
            )

        face_points = self._points(landmarks, self.FACE_OVAL, width, height)
        xs = face_points[:, 0]
        ys = face_points[:, 1]
        x_min, x_max = int(xs.min()), int(xs.max())
        y_min, y_max = int(ys.min()), int(ys.max())
        face_w = max(1, x_max - x_min)
        face_h = max(1, y_max - y_min)

        roi_left = max(0, int(x_min - face_w * self.side_expand_ratio))
        roi_right = min(width, int(x_max + face_w * self.side_expand_ratio))
        roi_bottom = max(0, y_min)
        roi_top = max(0, int(y_min - face_h * self.top_expand_ratio))
        if roi_right <= roi_left or roi_bottom <= roi_top:
            return self._invalid("hair_roi_unreliable", source_height, source_width)

        roi = np.zeros((height, width), dtype=np.uint8)
        roi[roi_top:roi_bottom, roi_left:roi_right] = 255

        import cv2

        person = (person_probability >= self.person_threshold).astype(np.uint8) * 255
        person = np.asarray(
            cv2.erode(person, np.ones((3, 3), dtype=np.uint8), iterations=1),
            dtype=np.uint8,
        )
        mask = np.where((roi > 0) & (person > 0), 255, 0).astype(np.uint8)

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
            return self._invalid("hair_roi_empty", source_height, source_width)

        overlap_count = int(np.logical_and(active, protected > 0).sum())
        protected_overlap_ratio = overlap_count / active_count
        protected_touched = protected_overlap_ratio > self.protected_overlap_max

        head_area = max(1, (roi_right - roi_left) * max(1, y_max - roi_top))
        coverage_ratio = active_count / head_area
        if coverage_ratio < self.coverage_min or coverage_ratio > self.coverage_max:
            return {
                **self._invalid(
                    "hair_roi_coverage_out_of_range", source_height, source_width
                ),
                "coverage_ratio": float(coverage_ratio),
                "protected_overlap_ratio": float(protected_overlap_ratio),
            }
        if protected_touched:
            return {
                **self._invalid("protected_region_in_mask", source_height, source_width),
                "coverage_ratio": float(coverage_ratio),
                "protected_overlap_ratio": float(protected_overlap_ratio),
                "protected_regions_touched": True,
            }

        if (width, height) != (source_width, source_height):
            mask = np.asarray(
                cv2.resize(
                    mask,
                    (source_width, source_height),
                    interpolation=cv2.INTER_NEAREST,
                ),
                dtype=np.uint8,
            )

        return {
            "valid": True,
            "mask": mask,
            "protected_regions_touched": False,
            "coverage_ratio": float(coverage_ratio),
            "protected_overlap_ratio": float(protected_overlap_ratio),
            "reason": None,
            "mask_kind": "person_intersection_hair_roi_v2",
            "beard_enabled": False,
            "background_locked": True,
            "calibration_status": "conservative_person_intersection",
        }

    def build_hair_beard_mask(self, original_photo: Any) -> Dict[str, Any]:
        """Compatibility alias; beard remains explicitly disabled."""
        return self.build_hair_mask(original_photo)

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
            refine_landmarks=False,
            min_detection_confidence=0.5,
        )
        try:
            result = face_mesh.process(rgb)
        finally:
            face_mesh.close()
        if not result.multi_face_landmarks:
            return None
        return [(lm.x, lm.y) for lm in result.multi_face_landmarks[0].landmark]

    def _segment_person(self, rgb: np.ndarray) -> Optional[np.ndarray]:
        if self.person_segmenter is not None:
            result = self.person_segmenter(rgb)
            if result is None:
                return None
            return np.asarray(result, dtype=np.float32)
        try:
            import mediapipe as mp
        except ImportError:
            return None

        segmenter = mp.solutions.selfie_segmentation.SelfieSegmentation(
            model_selection=0
        )
        try:
            result = segmenter.process(rgb)
        finally:
            segmenter.close()
        mask = getattr(result, "segmentation_mask", None)
        if mask is None:
            return None
        return np.asarray(mask, dtype=np.float32)

    def _prepare_working_rgb(self, image: Any) -> Tuple[np.ndarray, int, int]:
        if isinstance(image, Image.Image):
            source_width, source_height = image.size
            working = image if image.mode == "RGB" else image.convert("RGB")
            if max(source_height, source_width) > self.inference_max_side:
                scale = self.inference_max_side / float(
                    max(source_height, source_width)
                )
                working_width = max(1, int(round(source_width * scale)))
                working_height = max(1, int(round(source_height * scale)))
                working = working.resize(
                    (working_width, working_height), Image.Resampling.LANCZOS
                )
            return np.asarray(working, dtype=np.uint8), source_height, source_width

        rgb = self._to_rgb_array(image)
        source_height, source_width = rgb.shape[:2]
        return self._resize_for_inference(rgb), source_height, source_width

    def _resize_for_inference(self, rgb: np.ndarray) -> np.ndarray:
        height, width = rgb.shape[:2]
        longest = max(height, width)
        if longest <= self.inference_max_side:
            return rgb

        import cv2

        scale = self.inference_max_side / float(longest)
        resized_width = max(1, int(round(width * scale)))
        resized_height = max(1, int(round(height * scale)))
        return np.asarray(
            cv2.resize(
                rgb,
                (resized_width, resized_height),
                interpolation=cv2.INTER_AREA,
            ),
            dtype=np.uint8,
        )

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
        import cv2

        if len(points) >= 3:
            cv2.fillPoly(  # type: ignore[call-overload]
                mask, [points.astype(np.int32)], value
            )

    @staticmethod
    def _invalid(reason: str, height: int, width: int) -> Dict[str, Any]:
        return {
            "valid": False,
            "mask": np.zeros((height, width), dtype=np.uint8),
            "protected_regions_touched": False,
            "coverage_ratio": 0.0,
            "protected_overlap_ratio": 0.0,
            "reason": reason,
            "mask_kind": "person_intersection_hair_roi_v2",
            "beard_enabled": False,
            "background_locked": True,
            "calibration_status": "conservative_person_intersection",
        }
