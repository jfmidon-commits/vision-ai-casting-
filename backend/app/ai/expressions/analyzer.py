"""
ExpressionAnalyzer - Analise real de expressoes faciais usando MediaPipe FaceMesh + DeepFace.
Detecta: neutralidade, sorriso, surpresa, tristeza, raiva, medo, nojo.

Usa MediaPipe FaceMesh (468 landmarks) para deteccao precisa de landmarks faciais
e DeepFace para classificacao de emocoes com fallback para analise heuristica OpenCV.
"""

import cv2
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ExpressionAnalyzer:
    """
    Analisa expressoes faciais usando MediaPipe FaceMesh + DeepFace.
    Fallback para OpenCV Haar Cascades quando bibliotecas nao estao disponiveis.
    """

    def __init__(self):
        self._face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
        )
        self._eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        self._smile_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_smile.xml'
        )

        # MediaPipe FaceMesh
        self._mp_face_mesh = None
        self._face_mesh = None
        self._mp_drawing = None
        self._mp_drawing_styles = None

        # DeepFace
        self._deepface_available = False
        self._deepface_backend = "opencv"

        self._init_mediapipe()
        self._init_deepface()

    def _init_mediapipe(self):
        """Inicializa MediaPipe FaceMesh."""
        try:
            import mediapipe as mp
            self._mp_face_mesh = mp.solutions.face_mesh
            self._face_mesh = self._mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
            )
            self._mp_drawing = mp.solutions.drawing_utils
            self._mp_drawing_styles = mp.solutions.drawing_styles
            logger.info("MediaPipe FaceMesh inicializado com sucesso")
        except ImportError:
            logger.warning("MediaPipe nao disponivel. Usando fallback OpenCV.")
            self._face_mesh = None

    def _init_deepface(self):
        """Inicializa DeepFace."""
        try:
            from deepface import DeepFace
            self._deepface_available = True
            logger.info("DeepFace disponivel")
        except ImportError:
            logger.warning("DeepFace nao disponivel. Usando analise heuristica.")
            self._deepface_available = False

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analisa expressoes faciais em uma imagem.

        Args:
            image_bytes: Bytes da imagem (JPEG/PNG)

        Returns:
            Dict com analise de expressoes
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return self._error_result("Nao foi possivel carregar a imagem")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        # Detectar faces
        faces = self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100)
        )

        if len(faces) == 0:
            return self._error_result("Nenhum rosto detectado na imagem")

        # Analisar a maior face
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = largest_face

        # Extrair regiao do rosto
        face_roi = gray[y:y+h, x:x+w]
        face_roi_color = img[y:y+h, x:x+w]

        # Tentar MediaPipe FaceMesh primeiro
        landmarks = self._get_mediapipe_landmarks(img, x, y, w, h)

        # Tentar DeepFace para emocoes
        deepface_emotions = self._get_deepface_emotions(image_bytes)

        # Analise de componentes com landmarks (MediaPipe ou fallback)
        eyes = self._analyze_eyes(face_roi_color, face_roi, landmarks)
        smile = self._analyze_smile(face_roi, landmarks)
        eyebrows = self._analyze_eyebrows(face_roi, landmarks)
        mouth = self._analyze_mouth(face_roi, y, h, landmarks)

        # Combinar resultados DeepFace + heuristica
        expressions = self._combine_results(deepface_emotions, eyes, smile, eyebrows, mouth)

        # Classificar expressao dominante
        dominant_expression = max(expressions, key=expressions.get)

        # Calcular confianca
        confidence = self._calculate_confidence(eyes, smile, eyebrows, mouth, deepface_emotions)

        return {
            "dominant_expression": dominant_expression,
            "confidence": confidence,
            "expressions_detected": expressions,
            "details": {
                "eyes": eyes,
                "smile": smile,
                "eyebrows": eyebrows,
                "mouth": mouth,
                "deepface_raw": deepface_emotions if deepface_emotions else None,
                "landmarks_detected": landmarks is not None,
                "landmark_count": len(landmarks) if landmarks else 0,
            },
            "face_detected": True,
            "face_position": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
            "recommendations": self._generate_recommendations(
                dominant_expression, eyes, smile, eyebrows, mouth
            ),
        }

    # ========== MEDIAPIPE FACE MESH ==========

    def _get_mediapipe_landmarks(
        self, img: np.ndarray, face_x: int, face_y: int, face_w: int, face_h: int
    ) -> Optional[list]:
        """
        Extrai landmarks do MediaPipe FaceMesh (468 pontos).
        """
        if self._face_mesh is None:
            return None

        try:
            import mediapipe as mp

            # Converter BGR -> RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Processar
            results = self._face_mesh.process(img_rgb)

            if not results.multi_face_landmarks:
                return None

            # Pegar primeiro rosto
            face_landmarks = results.multi_face_landmarks[0]

            # Converter para lista de coordenadas normalizadas
            landmarks = []
            h, w = img.shape[:2]
            for lm in face_landmarks.landmark:
                landmarks.append({
                    "x": lm.x,
                    "y": lm.y,
                    "z": lm.z,
                    "px_x": int(lm.x * w),
                    "px_y": int(lm.y * h),
                })

            return landmarks

        except Exception as e:
            logger.warning(f"Erro no MediaPipe FaceMesh: {e}")
            return None

    def _get_landmark_region(
        self, landmarks: list, indices: list
    ) -> list:
        """Extrai coordenadas de uma regiao especifica de landmarks."""
        return [landmarks[i] for i in indices if i < len(landmarks)]

    def _calculate_distance(self, p1: dict, p2: dict) -> float:
        """Calcula distancia euclidiana entre dois landmarks."""
        return np.sqrt((p1["x"] - p2["x"])**2 + (p1["y"] - p2["y"])**2)

    # ========== DEEPFACE ==========

    def _get_deepface_emotions(self, image_bytes: bytes) -> Optional[Dict[str, float]]:
        """
        Analisa emocoes usando DeepFace.
        Retorna dict com scores de cada emocao.
        """
        if not self._deepface_available:
            return None

        try:
            from deepface import DeepFace
            import tempfile
            import os

            # Salvar bytes em arquivo temporario
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name

            try:
                result = DeepFace.analyze(
                    img_path=tmp_path,
                    actions=["emotion"],
                    enforce_detection=False,
                    silent=True,
                )

                if isinstance(result, list) and len(result) > 0:
                    emotions = result[0].get("emotion", {})
                else:
                    emotions = result.get("emotion", {})

                # Normalizar para 0-1
                return {k.lower(): round(v / 100.0, 3) for k, v in emotions.items()}

            finally:
                os.unlink(tmp_path)

        except Exception as e:
            logger.warning(f"Erro no DeepFace: {e}")
            return None

    # ========== ANALISE DE COMPONENTES ==========

    def _analyze_eyes(
        self, face_color: np.ndarray, face_gray: np.ndarray, landmarks: Optional[list]
    ) -> Dict:
        """Analisa estado dos olhos usando landmarks MediaPipe ou Haar."""
        eye_data = {
            "count": 0,
            "openness_score": 0.5,
            "arched_score": 0.0,
            "detected": False,
            "method": "unknown",
        }

        # MediaPipe landmarks para olhos
        if landmarks:
            # Indices dos olhos no FaceMesh
            LEFT_EYE = [33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7]
            RIGHT_EYE = [362, 398, 384, 385, 386, 387, 388, 466, 263, 249, 390, 373, 374, 380, 381, 382]

            left_eye = self._get_landmark_region(landmarks, LEFT_EYE)
            right_eye = self._get_landmark_region(landmarks, RIGHT_EYE)

            if left_eye and right_eye:
                eye_data["count"] = 2
                eye_data["detected"] = True
                eye_data["method"] = "mediapipe"

                # Calcular abertura do olho (EAR - Eye Aspect Ratio)
                left_ear = self._calculate_ear(left_eye)
                right_ear = self._calculate_ear(right_eye)
                avg_ear = (left_ear + right_ear) / 2

                # EAR normal: ~0.25-0.3 aberto, <0.2 fechado
                eye_data["openness_score"] = min(1.0, max(0.0, avg_ear / 0.3))

                # Olhos arregalados (surpresa) - EAR > 0.35
                eye_data["arched_score"] = min(1.0, max(0.0, (avg_ear - 0.25) / 0.15))

                return eye_data

        # Fallback: Haar Cascades
        eyes = self._eye_cascade.detectMultiScale(
            face_gray, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20)
        )

        eye_data["count"] = len(eyes)
        eye_data["detected"] = len(eyes) >= 2
        eye_data["method"] = "haar"

        if len(eyes) >= 2:
            areas = [w * h for (_, _, w, h) in eyes[:2]]
            avg_area = np.mean(areas)
            eye_data["openness_score"] = min(1.0, avg_area / 2000)
            eye_data["arched_score"] = min(1.0, avg_area / 1500)

        return eye_data

    def _calculate_ear(self, eye_landmarks: list) -> float:
        """
        Calcula Eye Aspect Ratio (EAR) usando landmarks.
        EAR = (|P2-P6| + |P3-P5|) / (2 * |P1-P4|)
        """
        if len(eye_landmarks) < 6:
            return 0.25  # valor padrao

        # Usar landmarks verticais e horizontais
        # Ponto superior, inferior, esquerdo, direito
        vertical_1 = self._calculate_distance(eye_landmarks[1], eye_landmarks[5])
        vertical_2 = self._calculate_distance(eye_landmarks[2], eye_landmarks[4])
        horizontal = self._calculate_distance(eye_landmarks[0], eye_landmarks[3])

        if horizontal == 0:
            return 0.25

        return (vertical_1 + vertical_2) / (2.0 * horizontal)

    def _analyze_smile(
        self, face_gray: np.ndarray, landmarks: Optional[list]
    ) -> Dict:
        """Analisa sorriso usando landmarks ou Haar cascade."""
        smile_data = {
            "detected": False,
            "score": 0.0,
            "intensity": "none",
            "method": "unknown",
        }

        # MediaPipe landmarks para boca
        if landmarks:
            # Indices da boca no FaceMesh
            MOUTH_OUTER = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
            MOUTH_INNER = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]

            outer_mouth = self._get_landmark_region(landmarks, MOUTH_OUTER)
            inner_mouth = self._get_landmark_region(landmarks, MOUTH_INNER)

            if outer_mouth and inner_mouth:
                smile_data["method"] = "mediapipe"
                smile_data["detected"] = True

                # Calcular MAR (Mouth Aspect Ratio)
                mar = self._calculate_mar(outer_mouth, inner_mouth)

                # MAR normal: ~0.15-0.25, sorriso: >0.3
                smile_data["score"] = min(1.0, max(0.0, (mar - 0.15) / 0.25))

                # Intensidade
                if smile_data["score"] > 0.7:
                    smile_data["intensity"] = "broad"
                elif smile_data["score"] > 0.4:
                    smile_data["intensity"] = "moderate"
                else:
                    smile_data["intensity"] = "subtle"

                return smile_data

        # Fallback: Haar cascade
        smiles = self._smile_cascade.detectMultiScale(
            face_gray, scaleFactor=1.7, minNeighbors=22, minSize=(50, 30)
        )

        smile_data["method"] = "haar"
        if len(smiles) > 0:
            smile_data["detected"] = True
            largest_smile = max(smiles, key=lambda s: s[2] * s[3])
            _, _, sw, sh = largest_smile
            area = sw * sh
            smile_data["score"] = min(1.0, area / 5000)

            if smile_data["score"] > 0.7:
                smile_data["intensity"] = "broad"
            elif smile_data["score"] > 0.4:
                smile_data["intensity"] = "moderate"
            else:
                smile_data["intensity"] = "subtle"

        return smile_data

    def _calculate_mar(self, outer_mouth: list, inner_mouth: list) -> float:
        """
        Calcula Mouth Aspect Ratio (MAR).
        """
        if len(outer_mouth) < 6 or len(inner_mouth) < 4:
            return 0.2

        # Altura da boca (vertical)
        mouth_height = self._calculate_distance(outer_mouth[3], outer_mouth[9])

        # Largura da boca (horizontal)
        mouth_width = self._calculate_distance(outer_mouth[0], outer_mouth[6])

        if mouth_width == 0:
            return 0.2

        return mouth_height / mouth_width

    def _analyze_eyebrows(
        self, face_gray: np.ndarray, landmarks: Optional[list]
    ) -> Dict:
        """Analisa posicao das sobrancelhas usando landmarks ou gradientes."""
        eyebrow_data = {
            "elevation_score": 0.0,
            "furrow_score": 0.0,
            "symmetry": 0.5,
            "method": "unknown",
        }

        # MediaPipe landmarks para sobrancelhas
        if landmarks:
            LEFT_EYEBROW = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
            RIGHT_EYEBROW = [336, 296, 334, 293, 300, 276, 283, 282, 295, 285]

            left_brow = self._get_landmark_region(landmarks, LEFT_EYEBROW)
            right_brow = self._get_landmark_region(landmarks, RIGHT_EYEBROW)

            if left_brow and right_brow:
                eyebrow_data["method"] = "mediapipe"

                # Elevação: posição Y média das sobrancelhas (mais alto = mais elevado)
                left_y = np.mean([p["y"] for p in left_brow])
                right_y = np.mean([p["y"] for p in right_brow])
                avg_y = (left_y + right_y) / 2

                # Normalizar: valores menores de Y = mais elevado (coordenadas Y crescem para baixo)
                eyebrow_data["elevation_score"] = min(1.0, max(0.0, (0.5 - avg_y) / 0.2))

                # Franzimento: proximidade entre as sobrancelhas
                left_inner = left_brow[4]  # ponto interno esquerdo
                right_inner = right_brow[4]  # ponto interno direito
                brow_distance = self._calculate_distance(left_inner, right_inner)

                # Distancia menor = mais franzido
                eyebrow_data["furrow_score"] = min(1.0, max(0.0, (0.15 - brow_distance) / 0.1))

                # Simetria
                left_height = max(p["y"] for p in left_brow) - min(p["y"] for p in left_brow)
                right_height = max(p["y"] for p in right_brow) - min(p["y"] for p in right_brow)
                eyebrow_data["symmetry"] = 1.0 - abs(left_height - right_height) / max(left_height + right_height, 0.01)

                return eyebrow_data

        # Fallback: gradientes
        eyebrow_data["method"] = "gradient"
        h, w = face_gray.shape
        eyebrow_region = face_gray[:int(h*0.4), :]

        grad_y = cv2.Sobel(eyebrow_region, cv2.CV_64F, 0, 1, ksize=3)
        grad_y = np.abs(grad_y)

        mid = w // 2
        left_grad = np.mean(grad_y[:, :mid])
        right_grad = np.mean(grad_y[:, mid:])
        avg_grad = (left_grad + right_grad) / 2

        eyebrow_data["elevation_score"] = min(1.0, avg_grad / 50)

        center_region = eyebrow_region[:, int(w*0.3):int(w*0.7)]
        center_grad = np.mean(np.abs(cv2.Sobel(center_region, cv2.CV_64F, 0, 1, ksize=3)))
        eyebrow_data["furrow_score"] = min(1.0, center_grad / 40)
        eyebrow_data["symmetry"] = 1.0 - abs(left_grad - right_grad) / max(left_grad + right_grad, 1)

        return eyebrow_data

    def _analyze_mouth(
        self, face_gray: np.ndarray, face_y: int, face_h: int,
        landmarks: Optional[list]
    ) -> Dict:
        """Analisa formato e posicao da boca."""
        mouth_data = {
            "openness": 0.0,
            "corners_up": 0.0,
            "corners_down": 0.0,
            "method": "unknown",
        }

        # MediaPipe landmarks para boca
        if landmarks:
            MOUTH_OUTER = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]

            mouth = self._get_landmark_region(landmarks, MOUTH_OUTER)
            if mouth:
                mouth_data["method"] = "mediapipe"

                # Abertura: distancia entre pontos superior e inferior
                top = mouth[3]
                bottom = mouth[9]
                mouth_height = self._calculate_distance(top, bottom)

                # Largura
                left = mouth[0]
                right = mouth[6]
                mouth_width = self._calculate_distance(left, right)

                if mouth_width > 0:
                    mouth_data["openness"] = min(1.0, mouth_height / mouth_width * 2)

                # Cantos para cima/baixo
                left_corner_y = mouth[0]["y"]
                right_corner_y = mouth[6]["y"]
                center_y = (mouth[3]["y"] + mouth[9]["y"]) / 2

                # Se cantos estao acima do centro = sorriso
                corner_diff = center_y - (left_corner_y + right_corner_y) / 2
                if corner_diff > 0:
                    mouth_data["corners_up"] = min(1.0, corner_diff / 0.1)
                else:
                    mouth_data["corners_down"] = min(1.0, abs(corner_diff) / 0.1)

                return mouth_data

        # Fallback: gradientes
        mouth_data["method"] = "gradient"
        h, w = face_gray.shape
        mouth_region = face_gray[int(h*0.55):, :]

        if mouth_region.size == 0:
            return mouth_data

        mouth_h, mouth_w = mouth_region.shape
        center_y = mouth_h // 2
        center_line = mouth_region[center_y, :]
        darkness = np.mean(255 - center_line) / 255.0
        mouth_data["openness"] = min(1.0, darkness * 2)

        grad_x = cv2.Sobel(mouth_region, cv2.CV_64F, 1, 0, ksize=3)
        left_corner = np.mean(grad_x[:, :mouth_w//3])
        right_corner = np.mean(grad_x[:, 2*mouth_w//3:])

        corners_up = max(0, (left_corner + right_corner) / 200)
        corners_down = max(0, -(left_corner + right_corner) / 200)

        mouth_data["corners_up"] = min(1.0, corners_up)
        mouth_data["corners_down"] = min(1.0, corners_down)

        return mouth_data

    # ========== COMBINAR RESULTADOS ==========

    def _combine_results(
        self, deepface_emotions: Optional[Dict],
        eyes: Dict, smile: Dict, eyebrows: Dict, mouth: Dict
    ) -> Dict[str, float]:
        """
        Combina resultados do DeepFace com analise heuristica.
        DeepFace tem peso maior quando disponivel.
        """
        # Scores heuristicos
        heuristic = {
            "neutral": self._score_neutral(eyes, smile, eyebrows, mouth),
            "happy": smile["score"],
            "surprise": self._score_surprise(eyes, eyebrows, mouth),
            "sad": self._score_sad(eyes, eyebrows, mouth),
            "angry": self._score_angry(eyes, eyebrows, mouth),
            "fear": self._score_fear(eyes, eyebrows, mouth),
            "disgust": self._score_disgust(eyes, eyebrows, mouth),
        }

        if deepface_emotions:
            # Combinar: 60% DeepFace + 40% heuristica
            combined = {}
            for emotion in heuristic:
                df_score = deepface_emotions.get(emotion, 0)
                h_score = heuristic[emotion]
                combined[emotion] = round(df_score * 0.6 + h_score * 0.4, 3)
            return combined

        return heuristic

    # ========== SCORING ==========

    def _score_neutral(self, eyes, smile, eyebrows, mouth) -> float:
        if not smile["detected"] and eyebrows["elevation_score"] < 0.3 and eyebrows["furrow_score"] < 0.3:
            return 0.8
        return 0.2

    def _score_surprise(self, eyes, eyebrows, mouth) -> float:
        score = 0.0
        if eyes["arched_score"] > 0.6:
            score += 0.35
        if eyebrows["elevation_score"] > 0.5:
            score += 0.35
        if mouth["openness"] > 0.5:
            score += 0.30
        return min(1.0, score)

    def _score_sad(self, eyes, eyebrows, mouth) -> float:
        score = 0.0
        if mouth["corners_down"] > 0.3:
            score += 0.45
        if eyebrows["elevation_score"] < 0.2 and eyebrows["furrow_score"] > 0.3:
            score += 0.35
        if not eyes.get("detected", True):
            score += 0.20
        return min(1.0, score)

    def _score_angry(self, eyes, eyebrows, mouth) -> float:
        score = 0.0
        if eyebrows["furrow_score"] > 0.5:
            score += 0.45
        if eyebrows["elevation_score"] < 0.2:
            score += 0.30
        if mouth["corners_down"] > 0.2 and not smile.get("detected", False):
            score += 0.25
        return min(1.0, score)

    def _score_fear(self, eyes, eyebrows, mouth) -> float:
        score = 0.0
        if eyes["arched_score"] > 0.5 and eyebrows["elevation_score"] > 0.4:
            score += 0.40
        if mouth["openness"] > 0.3 and mouth["openness"] < 0.6:
            score += 0.35
        if eyebrows["furrow_score"] > 0.3:
            score += 0.25
        return min(1.0, score)

    def _score_disgust(self, eyes, eyebrows, mouth) -> float:
        score = 0.0
        if eyebrows["furrow_score"] > 0.4 and eyebrows["elevation_score"] < 0.3:
            score += 0.40
        if mouth["corners_down"] > 0.2:
            score += 0.30
        if not smile.get("detected", False):
            score += 0.30
        return min(1.0, score)

    def _calculate_confidence(
        self, eyes, smile, eyebrows, mouth, deepface_emotions
    ) -> str:
        factors = [
            eyes["detected"],
            smile["detected"] or smile["score"] < 0.1,
            eyebrows.get("symmetry", 0.5) > 0.5,
        ]
        score = sum(factors) / len(factors)

        # Bonus se DeepFace disponivel
        if deepface_emotions:
            score += 0.1

        if score > 0.8:
            return "high"
        elif score > 0.5:
            return "medium"
        return "low"

    def _generate_recommendations(self, dominant, eyes, smile, eyebrows, mouth) -> list:
        recs = []

        if dominant == "neutral":
            recs.append({
                "type": "performance",
                "message": "Expressao neutra bem controlada. Praticar variacoes sutis para casting.",
                "priority": "medium"
            })

        if dominant == "happy":
            recs.append({
                "type": "performance",
                "message": f"Sorriso {smile['intensity']} detectado. Para comerciais, praticar intensidades variadas.",
                "priority": "low"
            })

        if smile["score"] > 0.8:
            recs.append({
                "type": "casting",
                "message": "Sorriso amplo e ideal para comerciais, publicidade e papeis de 'cara do povo'.",
                "priority": "high"
            })

        if eyebrows["furrow_score"] > 0.5:
            recs.append({
                "type": "performance",
                "message": "Franzimento detectado. Para papeis dramaticos, controlar intensidade.",
                "priority": "medium"
            })

        if not eyes["detected"]:
            recs.append({
                "type": "technical",
                "message": "Olhos nao detectados claramente. Verificar iluminacao da foto.",
                "priority": "high"
            })

        return recs

    def _error_result(self, message: str) -> Dict:
        return {
            "dominant_expression": "unknown",
            "confidence": "low",
            "expressions_detected": {},
            "details": {},
            "face_detected": False,
            "error": message,
            "recommendations": [{
                "type": "technical",
                "message": message,
                "priority": "high"
            }],
        }
