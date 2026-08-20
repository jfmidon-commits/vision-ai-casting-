"""Automatic image triage for the Vision visagism capture protocol."""

import logging
import os
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class TriageCategory(Enum):
    FRONTAL_CLOSE = "frontal_close"
    FRONTAL = "frontal"
    THREE_QUARTER_LEFT = "three_quarter_left"
    THREE_QUARTER_RIGHT = "three_quarter_right"
    PROFILE_LEFT = "profile_left"
    PROFILE_RIGHT = "profile_right"
    SMILING = "smiling"
    HAIRLINE = "hairline"
    POSTERIOR = "posterior"
    HALF_BODY = "half_body"
    UNKNOWN = "unknown"
    REJECTED = "rejected"


@dataclass
class TriageResult:
    filename: str
    category: TriageCategory
    confidence: float
    scores: Dict[str, float] = field(default_factory=dict)
    rejection_reasons: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    selected: bool = False


class ImageTriageEngine:
    """Classify photos using MediaPipe face/pose landmarks plus CV heuristics."""

    def __init__(self):
        self._face_landmarker = None
        self._pose_landmarker = None
        self._initialized = False
        self._model_dir = "/tmp/mediapipe_models"
        os.makedirs(self._model_dir, exist_ok=True)
        self._init_mediapipe()

    def _download_model(self, url: str, path: str) -> None:
        if not os.path.exists(path):
            logger.info("Downloading MediaPipe model: %s", url)
            urllib.request.urlretrieve(url, path)

    def _init_mediapipe(self) -> None:
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import BaseOptions
            from mediapipe.tasks.python.vision import (
                FaceLandmarker,
                FaceLandmarkerOptions,
                PoseLandmarker,
                PoseLandmarkerOptions,
                RunningMode,
            )

            self.mp = mp
            face_model = os.path.join(self._model_dir, "face_landmarker.task")
            self._download_model(
                "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
                face_model,
            )
            face_options = FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=face_model),
                running_mode=RunningMode.IMAGE,
                num_faces=1,
                min_face_detection_confidence=0.3,
                min_tracking_confidence=0.3,
                output_face_blendshapes=True,
            )
            self._face_landmarker = FaceLandmarker.create_from_options(face_options)

            pose_model = os.path.join(self._model_dir, "pose_landmarker_lite.task")
            self._download_model(
                "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
                pose_model,
            )
            pose_options = PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=pose_model),
                running_mode=RunningMode.IMAGE,
                min_pose_detection_confidence=0.3,
                min_tracking_confidence=0.3,
            )
            self._pose_landmarker = PoseLandmarker.create_from_options(pose_options)
            self._initialized = True
        except Exception as exc:
            logger.warning("ImageTriageEngine MediaPipe unavailable: %s", exc)
            self._initialized = False

    def process_image(self, image_path: str) -> TriageResult:
        filename = os.path.basename(image_path)
        try:
            img_array = np.array(Image.open(image_path).convert("RGB"))
        except Exception as exc:
            return TriageResult(
                filename=filename,
                category=TriageCategory.REJECTED,
                confidence=0.0,
                rejection_reasons=[f"Erro ao carregar: {exc}"],
            )

        h, w = img_array.shape[:2]
        if h < 240 or w < 240:
            return TriageResult(
                filename=filename,
                category=TriageCategory.REJECTED,
                confidence=0.0,
                scores={"width": float(w), "height": float(h)},
                rejection_reasons=[f"Resolução baixa: {w}x{h}"],
            )

        pose_result = self._analyze_pose(img_array)
        face_result = self._analyze_face(img_array)

        posterior_score = self._detect_posterior(img_array, pose_result, face_result)
        if posterior_score >= 0.5:
            return TriageResult(
                filename=filename,
                category=TriageCategory.POSTERIOR,
                confidence=posterior_score,
                scores={"posterior_score": posterior_score},
                metadata={
                    "pose_detected": pose_result.get("has_pose", False),
                    "face_detected": face_result.get("has_face", False),
                },
                selected=True,
            )

        if face_result.get("has_face", False):
            category, confidence, scores = self._classify_face(
                face_result, img_array, pose_result
            )

            if category in (
                TriageCategory.FRONTAL,
                TriageCategory.FRONTAL_CLOSE,
                TriageCategory.THREE_QUARTER_LEFT,
                TriageCategory.THREE_QUARTER_RIGHT,
            ):
                half_body_score = self._detect_half_body(img_array, pose_result)
                if self._is_half_body_pose(pose_result, half_body_score):
                    return TriageResult(
                        filename=filename,
                        category=TriageCategory.HALF_BODY,
                        confidence=half_body_score,
                        scores={"half_body_score": half_body_score, **scores},
                        metadata={"pose_detected": True},
                        selected=True,
                    )

            hairline_score = self._detect_hairline(img_array, pose_result, face_result)
            if (
                hairline_score >= 0.42
                and category != TriageCategory.SMILING
                and abs(scores.get("yaw", 0.0)) < 30
            ):
                return TriageResult(
                    filename=filename,
                    category=TriageCategory.HAIRLINE,
                    confidence=hairline_score,
                    scores={"hairline_score": hairline_score, **scores},
                    metadata={"face_detected": True, "hairline_visible": True},
                    selected=True,
                )

            return TriageResult(
                filename=filename,
                category=category,
                confidence=confidence,
                scores=scores,
                metadata={
                    "landmarks_count": face_result.get("landmarks_count", 0),
                    "pose": pose_result,
                },
                selected=category not in (
                    TriageCategory.UNKNOWN,
                    TriageCategory.REJECTED,
                ),
            )

        half_body_score = self._detect_half_body(img_array, pose_result)
        if self._is_half_body_pose(pose_result, half_body_score):
            return TriageResult(
                filename=filename,
                category=TriageCategory.HALF_BODY,
                confidence=half_body_score,
                scores={"half_body_score": half_body_score},
                metadata={"pose_detected": True, "no_face": True},
                selected=True,
            )

        hairline_score = self._detect_hairline(img_array, pose_result)
        if hairline_score >= 0.42:
            return TriageResult(
                filename=filename,
                category=TriageCategory.HAIRLINE,
                confidence=hairline_score,
                scores={"hairline_score": hairline_score},
                metadata={"face_detected": False},
                selected=True,
            )

        return TriageResult(
            filename=filename,
            category=TriageCategory.REJECTED,
            confidence=0.0,
            scores={"face_detected": 0.0},
            rejection_reasons=["Nenhuma face detectada"],
        )

    def _analyze_face(self, img_array: np.ndarray) -> Dict:
        if not self._initialized or self._face_landmarker is None:
            return {"has_face": False}
        try:
            mp_image = self.mp.Image(
                image_format=self.mp.ImageFormat.SRGB, data=img_array
            )
            results = self._face_landmarker.detect(mp_image)
            if not results.face_landmarks:
                return {"has_face": False}
            landmarks = [
                {"x": lm.x, "y": lm.y, "z": lm.z}
                for lm in results.face_landmarks[0]
            ]
            blendshapes: Dict[str, float] = {}
            if results.face_blendshapes:
                for item in results.face_blendshapes[0]:
                    name = getattr(item, "category_name", "")
                    if name:
                        blendshapes[name] = float(getattr(item, "score", 0.0))
            return {
                "has_face": True,
                "landmarks": landmarks,
                "landmarks_count": len(landmarks),
                "blendshapes": blendshapes,
            }
        except Exception as exc:
            return {"has_face": False, "error": str(exc)}

    def _analyze_pose(self, img_array: np.ndarray) -> Dict:
        if not self._initialized or self._pose_landmarker is None:
            return {"has_pose": False}
        try:
            mp_image = self.mp.Image(
                image_format=self.mp.ImageFormat.SRGB, data=img_array
            )
            results = self._pose_landmarker.detect(mp_image)
            if not results.pose_landmarks:
                return {"has_pose": False}
            landmarks = [
                {
                    "x": lm.x,
                    "y": lm.y,
                    "z": lm.z,
                    "visibility": float(getattr(lm, "visibility", 1.0)),
                }
                for lm in results.pose_landmarks[0]
            ]
            return {
                "has_pose": True,
                "landmarks": landmarks,
                "landmarks_count": len(landmarks),
            }
        except Exception as exc:
            return {"has_pose": False, "error": str(exc)}

    def _detect_posterior(
        self, img_array: np.ndarray, pose_result: Dict, face_result: Optional[Dict] = None
    ) -> float:
        score = 0.0
        if pose_result.get("has_pose", False):
            landmarks = pose_result.get("landmarks", [])
            if len(landmarks) >= 33:
                nose = landmarks[0].get("visibility", 0.0)
                eye_l = landmarks[2].get("visibility", 0.0)
                eye_r = landmarks[5].get("visibility", 0.0)
                shoulder_l = landmarks[11].get("visibility", 0.0)
                shoulder_r = landmarks[12].get("visibility", 0.0)
                shoulders_visible = shoulder_l > 0.45 and shoulder_r > 0.45

                if shoulders_visible:
                    score += 0.22
                    if abs(landmarks[11]["y"] - landmarks[12]["y"]) < 0.12:
                        score += 0.12
                if nose < 0.45 and eye_l < 0.45 and eye_r < 0.45:
                    score += 0.38
                elif nose < 0.55 and (eye_l < 0.45 or eye_r < 0.45):
                    score += 0.2

        if face_result is not None:
            if face_result.get("has_face", False):
                score -= 0.35
            elif pose_result.get("has_pose", False):
                score += 0.18

        h, w = img_array.shape[:2]
        central = img_array[
            int(h * 0.12) : int(h * 0.55), int(w * 0.25) : int(w * 0.75)
        ]
        if central.size:
            gray = cv2.cvtColor(central, cv2.COLOR_RGB2GRAY)
            if np.var(gray) > 350:
                score += 0.08
        return max(0.0, min(score, 1.0))

    def _detect_half_body(self, img_array: np.ndarray, pose_result: Dict) -> float:
        score = 0.0
        h, w = img_array.shape[:2]
        aspect_ratio = h / w if w else 1.0
        if 1.1 <= aspect_ratio <= 2.2:
            score += 0.08
        if not pose_result.get("has_pose", False):
            return score

        landmarks = pose_result.get("landmarks", [])
        if len(landmarks) < 27:
            return score
        hip_l = landmarks[23].get("visibility", 0.0)
        hip_r = landmarks[24].get("visibility", 0.0)
        knee_l = landmarks[25].get("visibility", 0.0)
        knee_r = landmarks[26].get("visibility", 0.0)
        shoulder_l = landmarks[11].get("visibility", 0.0)
        shoulder_r = landmarks[12].get("visibility", 0.0)

        if max(hip_l, hip_r) > 0.30:
            score += 0.42
        if (knee_l + knee_r) / 2 < 0.68:
            score += 0.27
        if max(shoulder_l, shoulder_r) > 0.45:
            score += 0.12
        return min(score, 1.0)

    def _is_half_body_pose(self, pose_result: Dict, score: float) -> bool:
        if score < 0.54 or not pose_result.get("has_pose", False):
            return False
        landmarks = pose_result.get("landmarks", [])
        if len(landmarks) < 27:
            return False
        hip_visibility = max(
            landmarks[23].get("visibility", 0.0),
            landmarks[24].get("visibility", 0.0),
        )
        knee_visibility = (
            landmarks[25].get("visibility", 0.0)
            + landmarks[26].get("visibility", 0.0)
        ) / 2
        return hip_visibility > 0.30 and knee_visibility < 0.68

    def _detect_hairline(
        self,
        img_array: np.ndarray,
        pose_result: Dict,
        face_result: Optional[Dict] = None,
    ) -> float:
        score = 0.0
        if face_result and face_result.get("has_face", False):
            landmarks = face_result.get("landmarks", [])
            if len(landmarks) >= 478:
                forehead_top = landmarks[10]["y"]
                brow_y = (landmarks[70]["y"] + landmarks[300]["y"]) / 2
                chin_y = landmarks[152]["y"]
                face_height = chin_y - forehead_top
                if face_height > 0:
                    forehead_ratio = (brow_y - forehead_top) / face_height
                    if forehead_ratio >= 0.25:
                        score += 0.52
                    elif forehead_ratio >= 0.21:
                        score += 0.44

                h, w = img_array.shape[:2]
                y1 = max(0, int(forehead_top * h))
                y2 = min(h, int(brow_y * h))
                xs = [landmarks[70]["x"], landmarks[300]["x"]]
                x1 = max(0, int((min(xs) - 0.08) * w))
                x2 = min(w, int((max(xs) + 0.08) * w))
                region = img_array[y1:y2, x1:x2]
                if region.size:
                    gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
                    edges = cv2.Canny(gray, 50, 120)
                    edge_density = float(np.mean(edges > 0))
                    if edge_density < 0.18:
                        score += 0.12
        return min(score, 1.0)

    def _classify_face(
        self, face_result: Dict, img_array: np.ndarray, pose_result: Dict
    ) -> Tuple[TriageCategory, float, Dict]:
        landmarks = face_result.get("landmarks", [])
        if len(landmarks) < 478:
            return TriageCategory.UNKNOWN, 0.0, {"error": "Landmarks insuficientes"}

        yaw = self._estimate_yaw(landmarks)
        pitch = self._estimate_pitch(landmarks)
        smile_score = self._detect_smile(face_result)

        right_eye_width = abs(landmarks[33]["x"] - landmarks[133]["x"])
        left_eye_width = abs(landmarks[362]["x"] - landmarks[263]["x"])
        max_eye_width = max(right_eye_width, left_eye_width)
        eye_compression = (
            min(right_eye_width, left_eye_width) / max_eye_width
            if max_eye_width > 0.001
            else 1.0
        )

        scores = {
            "yaw": yaw,
            "pitch": pitch,
            "smile_score": smile_score,
            "eye_compression": eye_compression,
        }

        if smile_score >= 0.38:
            return TriageCategory.SMILING, min(1.0, 0.55 + smile_score * 0.45), scores

        abs_yaw = abs(yaw)
        if abs_yaw < 6:
            if pitch < -10:
                return TriageCategory.FRONTAL_CLOSE, 0.85, scores
            return TriageCategory.FRONTAL, 0.9, scores

        # Reserve PROFILE_RIGHT for genuinely profile-like geometry. A face in
        # the 3/4 range must also show clear far-eye foreshortening; yaw alone
        # only wins when the rotation is truly extreme.
        right_profile_extreme = yaw >= 70
        right_profile_geometry = yaw >= 50 and eye_compression <= 0.60
        right_profile_near = yaw >= 42 and eye_compression <= 0.42
        if right_profile_extreme or right_profile_geometry or right_profile_near:
            return TriageCategory.PROFILE_RIGHT, 0.78, scores
        if yaw <= -48:
            return TriageCategory.PROFILE_LEFT, 0.78, scores
        if yaw > 0:
            return TriageCategory.THREE_QUARTER_RIGHT, 0.82, scores
        return TriageCategory.THREE_QUARTER_LEFT, 0.82, scores

    def _estimate_yaw(self, landmarks: List[Dict]) -> float:
        if len(landmarks) < 455:
            return 0.0
        nose = landmarks[1]
        left_face = landmarks[234]
        right_face = landmarks[454]
        dist_left = abs(nose["x"] - left_face["x"])
        dist_right = abs(right_face["x"] - nose["x"])
        total = dist_left + dist_right
        if total < 0.001:
            return 0.0
        ratio = (dist_right - dist_left) / total

        z_left = abs(nose["z"] - left_face["z"])
        z_right = abs(right_face["z"] - nose["z"])
        z_total = z_left + z_right
        if z_total > 0.001:
            z_ratio = (z_right - z_left) / z_total
            ratio = ratio * 0.75 + z_ratio * 0.25
        return float(np.clip(ratio * 90, -90, 90))

    def _estimate_pitch(self, landmarks: List[Dict]) -> float:
        if len(landmarks) < 264:
            return 0.0
        nose = landmarks[1]
        chin = landmarks[152]
        eye_level = (landmarks[33]["y"] + landmarks[263]["y"]) / 2
        face_height = chin["y"] - eye_level
        if face_height < 0.001:
            return 0.0
        return ((eye_level - nose["y"]) / face_height) * 45

    def _detect_smile(self, face_result: Dict) -> float:
        if isinstance(face_result, list):
            face_result = {"landmarks": face_result, "blendshapes": {}}
        elif not isinstance(face_result, dict):
            return 0.0

        blendshapes = face_result.get("blendshapes", {})
        smile_blend = (
            blendshapes.get("mouthSmileLeft", 0.0)
            + blendshapes.get("mouthSmileRight", 0.0)
        ) / 2
        cheek_blend = (
            blendshapes.get("cheekSquintLeft", 0.0)
            + blendshapes.get("cheekSquintRight", 0.0)
        ) / 2
        blend_score = min(1.0, smile_blend * 0.85 + cheek_blend * 0.15)

        landmarks = face_result.get("landmarks", [])
        if len(landmarks) < 292:
            return blend_score
        top = landmarks[13]
        bottom = landmarks[14]
        left = landmarks[61]
        right = landmarks[291]
        width = abs(left["x"] - right["x"])
        if width <= 0:
            return blend_score
        mar = abs(top["y"] - bottom["y"]) / width
        center_y = (top["y"] + bottom["y"]) / 2
        curve = (center_y - left["y"]) + (center_y - right["y"])
        curve_score = float(np.clip(curve * 14, 0, 1))
        mar_score = float(np.clip((mar - 0.08) / 0.22, 0, 1))
        geometry_score = curve_score * 0.65 + mar_score * 0.35
        return max(blend_score, geometry_score)

    def process_dataset(self, dataset_path: str) -> List[TriageResult]:
        results: List[TriageResult] = []
        if not os.path.exists(dataset_path):
            logger.warning("Directory not found: %s", dataset_path)
            return results
        valid_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        for filename in sorted(os.listdir(dataset_path)):
            if os.path.splitext(filename)[1].lower() not in valid_extensions:
                continue
            results.append(self.process_image(os.path.join(dataset_path, filename)))
        return results

    def select_best_by_category(
        self, results: List[TriageResult]
    ) -> Dict[TriageCategory, TriageResult]:
        best: Dict[TriageCategory, TriageResult] = {}
        for category in TriageCategory:
            if category in (TriageCategory.UNKNOWN, TriageCategory.REJECTED):
                continue
            candidates = [
                result
                for result in results
                if result.category == category and result.selected
            ]
            if candidates:
                best[category] = max(candidates, key=lambda result: result.confidence)
        return best
