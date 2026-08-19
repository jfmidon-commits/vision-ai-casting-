"""
ImageTriageEngine - Classificação automática de imagens para protocolo de visagismo.

Usa MediaPipe Tasks API (0.10+) para detecção facial e de pose, sem depender de
serviços externos.
"""

import cv2
import numpy as np
from PIL import Image
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging
import os
import urllib.request

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
    """Engine de triagem de imagens para protocolo de visagismo."""

    def __init__(self):
        self._face_landmarker = None
        self._pose_landmarker = None
        self._initialized = False
        self._model_dir = "/tmp/mediapipe_models"
        os.makedirs(self._model_dir, exist_ok=True)
        self._init_mediapipe()

    def _download_model(self, url: str, path: str):
        """Baixa modelo do MediaPipe se não existir."""
        if not os.path.exists(path):
            logger.info(f"Baixando modelo: {url}")
            urllib.request.urlretrieve(url, path)
            logger.info(f"Modelo salvo: {path}")

    def _init_mediapipe(self):
        """Inicializa modelos MediaPipe Tasks."""
        try:
            import mediapipe as mp
            from mediapipe.tasks.python.vision import (
                FaceLandmarker, FaceLandmarkerOptions, RunningMode,
                PoseLandmarker, PoseLandmarkerOptions,
            )
            from mediapipe.tasks.python import BaseOptions

            self.mp = mp

            # Face Landmarker
            face_model = os.path.join(self._model_dir, "face_landmarker.task")
            self._download_model(
                "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
                face_model
            )

            face_options = FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=face_model),
                running_mode=RunningMode.IMAGE,
                num_faces=1,
                min_face_detection_confidence=0.3,
                min_tracking_confidence=0.3,
            )
            self._face_landmarker = FaceLandmarker.create_from_options(face_options)

            # Pose Landmarker
            pose_model = os.path.join(self._model_dir, "pose_landmarker_lite.task")
            self._download_model(
                "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
                pose_model
            )

            pose_options = PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=pose_model),
                running_mode=RunningMode.IMAGE,
                min_pose_detection_confidence=0.3,
                min_tracking_confidence=0.3,
            )
            self._pose_landmarker = PoseLandmarker.create_from_options(pose_options)

            self._initialized = True
            logger.info("ImageTriageEngine: MediaPipe Tasks inicializado")
        except Exception as e:
            logger.warning(f"ImageTriageEngine: MediaPipe não disponível - {e}")
            self._initialized = False

    def process_image(self, image_path: str) -> TriageResult:
        """Processa uma única imagem."""
        filename = os.path.basename(image_path)

        try:
            image = Image.open(image_path).convert('RGB')
            img_array = np.array(image)
        except Exception as e:
            return TriageResult(
                filename=filename,
                category=TriageCategory.REJECTED,
                confidence=0.0,
                rejection_reasons=[f"Erro ao carregar: {str(e)}"],
            )

        h, w = img_array.shape[:2]
        if h < 240 or w < 240:
            return TriageResult(
                filename=filename,
                category=TriageCategory.REJECTED,
                confidence=0.0,
                scores={"width": w, "height": h},
                rejection_reasons=[f"Resolução baixa: {w}x{h}"],
            )

        # Análise de pose (independente de face)
        pose_result = self._analyze_pose(img_array)

        # 1. Verificar POSTERIOR primeiro (antes da face - pode não ter face visível)
        posterior_score = self._detect_posterior(img_array, pose_result)
        if posterior_score > 0.6:
            return TriageResult(
                filename=filename,
                category=TriageCategory.POSTERIOR,
                confidence=posterior_score,
                scores={"posterior_score": posterior_score},
                metadata={"pose_detected": pose_result.get("has_pose", False)},
                selected=True,
            )

        # 2. Análise facial para categorias principais
        face_result = self._analyze_face(img_array)

        # Se detectou face, classificar por ângulo/sorriso primeiro
        if face_result.get("has_face", False):
            category, confidence, scores = self._classify_face(face_result, img_array, pose_result)

            # Verificar HAIRLINE (cabelo puxado) - pode ter face mas ser HAIRLINE
            hairline_score = self._detect_hairline(img_array, pose_result, face_result)
            if hairline_score > 0.6 and category != TriageCategory.SMILING:
                return TriageResult(
                    filename=filename,
                    category=TriageCategory.HAIRLINE,
                    confidence=hairline_score,
                    scores={"hairline_score": hairline_score, **scores},
                    metadata={"face_detected": True, "hair_pulled_back": True},
                    selected=True,
                )

            # Verificar HALF_BODY apenas para frontais com pose corporal clara
            if category in (TriageCategory.FRONTAL, TriageCategory.FRONTAL_CLOSE):
                half_body_score = self._detect_half_body(img_array, pose_result)
                # HALF_BODY precisa ter pose detectada com quadril visível E joelho não visível
                if half_body_score > 0.75 and pose_result.get("has_pose", False):
                    landmarks = pose_result.get("landmarks", [])
                    if len(landmarks) > 25:
                        left_knee_vis = landmarks[25].get("visibility", 0)
                        left_hip_vis = landmarks[23].get("visibility", 0) if len(landmarks) > 23 else 0
                        if left_hip_vis > 0.5 and left_knee_vis < 0.3:
                            return TriageResult(
                                filename=filename,
                                category=TriageCategory.HALF_BODY,
                                confidence=half_body_score,
                                scores={"half_body_score": half_body_score, **scores},
                                metadata={"pose_detected": True},
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
                selected=category not in (TriageCategory.UNKNOWN, TriageCategory.REJECTED),
            )

        # 3. Sem face detectada - verificar HAIRLINE ou HALF_BODY
        hairline_score = self._detect_hairline(img_array, pose_result)
        if hairline_score > 0.5:
            return TriageResult(
                filename=filename,
                category=TriageCategory.HAIRLINE,
                confidence=hairline_score,
                scores={"hairline_score": hairline_score},
                metadata={"face_detected": False},
                selected=True,
            )

        # HALF_BODY sem face só se tiver pose corporal clara (quadril visível, joelho não)
        half_body_score = self._detect_half_body(img_array, pose_result)
        if half_body_score > 0.7 and pose_result.get("has_pose", False):
            landmarks = pose_result.get("landmarks", [])
            if len(landmarks) > 25:
                left_knee_vis = landmarks[25].get("visibility", 0)
                left_hip_vis = landmarks[23].get("visibility", 0) if len(landmarks) > 23 else 0
                if left_hip_vis > 0.5 and left_knee_vis < 0.3:
                    return TriageResult(
                        filename=filename,
                        category=TriageCategory.HALF_BODY,
                        confidence=half_body_score,
                        scores={"half_body_score": half_body_score},
                        metadata={"pose_detected": True, "no_face": True},
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
        """Analisa face usando MediaPipe FaceLandmarker."""
        if not self._initialized or self._face_landmarker is None:
            return {"has_face": False}

        try:
            mp_image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=img_array)
            results = self._face_landmarker.detect(mp_image)

            if not results.face_landmarks:
                return {"has_face": False}

            landmarks = []
            for lm in results.face_landmarks[0]:
                landmarks.append({"x": lm.x, "y": lm.y, "z": lm.z})

            return {
                "has_face": True,
                "landmarks": landmarks,
                "landmarks_count": len(landmarks),
            }
        except Exception as e:
            return {"has_face": False, "error": str(e)}

    def _analyze_pose(self, img_array: np.ndarray) -> Dict:
        """Analisa pose usando MediaPipe PoseLandmarker."""
        if not self._initialized or self._pose_landmarker is None:
            return {"has_pose": False}

        try:
            mp_image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=img_array)
            results = self._pose_landmarker.detect(mp_image)

            if not results.pose_landmarks:
                return {"has_pose": False}

            landmarks = []
            for lm in results.pose_landmarks[0]:
                landmarks.append({
                    "x": lm.x, "y": lm.y, "z": lm.z,
                    "visibility": getattr(lm, 'visibility', 1.0)
                })

            return {
                "has_pose": True,
                "landmarks": landmarks,
                "landmarks_count": len(landmarks),
            }
        except Exception as e:
            return {"has_pose": False, "error": str(e)}

    def _detect_posterior(self, img_array: np.ndarray, pose_result: Dict) -> float:
        """Detecta vista posterior (costas)."""
        score = 0.0
        h, w = img_array.shape[:2]

        if pose_result.get("has_pose", False):
            landmarks = pose_result.get("landmarks", [])
            if len(landmarks) >= 33:
                nose_vis = landmarks[0].get("visibility", 0)
                left_eye_vis = landmarks[2].get("visibility", 0) if len(landmarks) > 2 else 0
                right_eye_vis = landmarks[5].get("visibility", 0) if len(landmarks) > 5 else 0
                left_shoulder_vis = landmarks[11].get("visibility", 0) if len(landmarks) > 11 else 0
                right_shoulder_vis = landmarks[12].get("visibility", 0) if len(landmarks) > 12 else 0

                if nose_vis < 0.3 and left_eye_vis < 0.3 and right_eye_vis < 0.3:
                    if left_shoulder_vis > 0.5 or right_shoulder_vis > 0.5:
                        score += 0.5

                if left_shoulder_vis > 0.5 and right_shoulder_vis > 0.5:
                    left_y = landmarks[11]["y"]
                    right_y = landmarks[12]["y"]
                    if abs(left_y - right_y) < 0.1:
                        score += 0.2

        top_region = img_array[int(h*0.1):int(h*0.5), int(w*0.3):int(w*0.7)]
        if top_region.size > 0:
            gray = cv2.cvtColor(top_region, cv2.COLOR_RGB2GRAY)
            if np.var(gray) > 500:
                score += 0.15

        try:
            gray_full = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray_full, 1.1, 3)
            if len(faces) == 0:
                score += 0.15
        except:
            pass

        return min(score, 1.0)

    def _detect_half_body(self, img_array: np.ndarray, pose_result: Dict) -> float:
        """Detecta meio corpo."""
        score = 0.0
        h, w = img_array.shape[:2]
        aspect_ratio = h / w if w > 0 else 1.0

        # Aspect ratio menos importante sozinho
        if 1.3 <= aspect_ratio <= 1.8:
            score += 0.1

        if pose_result.get("has_pose", False):
            landmarks = pose_result.get("landmarks", [])
            if len(landmarks) >= 33:
                # Quadril visível é obrigatório para meio corpo
                left_hip_vis = landmarks[23].get("visibility", 0) if len(landmarks) > 23 else 0
                right_hip_vis = landmarks[24].get("visibility", 0) if len(landmarks) > 24 else 0

                if left_hip_vis > 0.5 or right_hip_vis > 0.5:
                    score += 0.4
                else:
                    return score  # Sem quadril visível, não é meio corpo

                # Joelhos NÃO visíveis (diferencia de corpo inteiro)
                left_knee_vis = landmarks[25].get("visibility", 0) if len(landmarks) > 25 else 0
                right_knee_vis = landmarks[26].get("visibility", 0) if len(landmarks) > 26 else 0
                if left_knee_vis < 0.3 and right_knee_vis < 0.3:
                    score += 0.25

                # Ombros visíveis
                left_shoulder_vis = landmarks[11].get("visibility", 0) if len(landmarks) > 11 else 0
                if left_shoulder_vis > 0.5:
                    score += 0.1

        # Face detectada = bônus pequeno
        try:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, 1.1, 3)
            if len(faces) > 0:
                score += 0.05
        except:
            pass

        return min(score, 1.0)

    def _detect_hairline(self, img_array: np.ndarray, pose_result: Dict,
                         face_result: Optional[Dict] = None) -> float:
        """Detecta implantação capilar (cabelo puxado)."""
        score = 0.0

        if face_result and face_result.get("has_face", False):
            landmarks = face_result.get("landmarks", [])
            if len(landmarks) >= 478:
                forehead_top = landmarks[10]["y"]
                brow_y = landmarks[105]["y"] if len(landmarks) > 105 else landmarks[70]["y"]
                chin_y = landmarks[152]["y"]

                face_height = chin_y - forehead_top
                forehead_height = brow_y - forehead_top

                if face_height > 0:
                    forehead_ratio = forehead_height / face_height
                    if forehead_ratio > 0.35:
                        score += 0.5

        h, w = img_array.shape[:2]
        top_region = img_array[0:int(h*0.3), :]
        if top_region.size > 0:
            hsv = cv2.cvtColor(top_region, cv2.COLOR_RGB2HSV)
            mean_sat = np.mean(hsv[:, :, 1])
            if mean_sat < 60:
                score += 0.2

        return min(score, 1.0)

    def _classify_face(self, face_result: Dict, img_array: np.ndarray,
                       pose_result: Dict) -> Tuple[TriageCategory, float, Dict]:
        """Classifica imagem facial em categorias do protocolo."""
        landmarks = face_result.get("landmarks", [])
        if len(landmarks) < 478:
            return TriageCategory.UNKNOWN, 0.0, {"error": "Landmarks insuficientes"}

        yaw = self._estimate_yaw(landmarks)
        pitch = self._estimate_pitch(landmarks)
        smile_score = self._detect_smile(landmarks)

        scores = {"yaw": yaw, "pitch": pitch, "smile_score": smile_score}

        if smile_score > 0.5:
            return TriageCategory.SMILING, smile_score, scores

        if abs(yaw) < 15:
            if pitch < -10:
                return TriageCategory.FRONTAL_CLOSE, 0.85, scores
            return TriageCategory.FRONTAL, 0.9, scores
        elif 15 <= yaw < 45:
            return TriageCategory.THREE_QUARTER_RIGHT, 0.8, scores
        elif -45 < yaw <= -15:
            return TriageCategory.THREE_QUARTER_LEFT, 0.8, scores
        elif yaw >= 45:
            return TriageCategory.PROFILE_RIGHT, 0.75, scores
        elif yaw <= -45:
            return TriageCategory.PROFILE_LEFT, 0.75, scores

        return TriageCategory.UNKNOWN, 0.3, scores

    def _estimate_yaw(self, landmarks: List[Dict]) -> float:
        """Estima ângulo yaw em graus."""
        if len(landmarks) < 454:
            return 0.0

        nose = landmarks[1]
        left_face = landmarks[234]
        right_face = landmarks[454]

        dist_left = abs(nose["x"] - left_face["x"])
        dist_right = abs(right_face["x"] - nose["x"])
        total = dist_left + dist_right

        if total < 0.001:
            return 0.0

        yaw_ratio = (dist_right - dist_left) / total
        return yaw_ratio * 90

    def _estimate_pitch(self, landmarks: List[Dict]) -> float:
        """Estima ângulo pitch em graus."""
        if len(landmarks) < 152:
            return 0.0

        nose = landmarks[1]
        chin = landmarks[152]
        left_eye = landmarks[33]
        right_eye = landmarks[263]

        eye_level = (left_eye["y"] + right_eye["y"]) / 2
        face_height = chin["y"] - eye_level

        if face_height < 0.001:
            return 0.0

        nose_offset = eye_level - nose["y"]
        return (nose_offset / face_height) * 45

    def _detect_smile(self, landmarks: List[Dict]) -> float:
        """Detecta sorriso combinando MAR e curvatura labial."""
        if len(landmarks) < 478:
            return 0.0

        mouth_top = landmarks[13]
        mouth_bottom = landmarks[14]
        mouth_left = landmarks[61]
        mouth_right = landmarks[291]

        height = abs(mouth_top["y"] - mouth_bottom["y"])
        width = abs(mouth_left["x"] - mouth_right["x"])
        mar = height / width if width > 0 else 0

        mouth_center_y = (mouth_top["y"] + mouth_bottom["y"]) / 2
        left_corner_y = mouth_left["y"]
        right_corner_y = mouth_right["y"]

        curve = (mouth_center_y - left_corner_y) + (mouth_center_y - right_corner_y)
        curve_score = max(0, min(1, curve * 10))

        mar_score = 0.0
        if 0.15 <= mar <= 0.5:
            mar_score = 1.0 - abs(mar - 0.3) / 0.3
        elif mar > 0.5:
            mar_score = 0.5

        smile_score = curve_score * 0.5 + mar_score * 0.3
        if curve_score > 0.5 and mar_score > 0.3:
            smile_score += 0.2

        return min(smile_score, 1.0)

    def process_dataset(self, dataset_path: str) -> List[TriageResult]:
        """Processa todas as imagens de um diretório."""
        results = []
        if not os.path.exists(dataset_path):
            logger.warning(f"Diretório não encontrado: {dataset_path}")
            return results

        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
        for filename in sorted(os.listdir(dataset_path)):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in valid_extensions:
                continue
            filepath = os.path.join(dataset_path, filename)
            result = self.process_image(filepath)
            results.append(result)

        return results

    def select_best_by_category(self, results: List[TriageResult]) -> Dict[TriageCategory, TriageResult]:
        """Seleciona a melhor imagem por categoria."""
        best = {}
        for category in TriageCategory:
            if category in (TriageCategory.UNKNOWN, TriageCategory.REJECTED):
                continue
            category_results = [r for r in results if r.category == category and r.selected]
            if category_results:
                best[category] = max(category_results, key=lambda r: r.confidence)
        return best
