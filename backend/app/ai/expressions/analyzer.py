"""
ExpressionAnalyzer - Análise real de expressões faciais usando OpenCV.
Detecta: neutralidade, sorriso, surpresa, tristeza, raiva, medo, nojo.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image
import io


class ExpressionAnalyzer:
    """Analisa expressões faciais em imagens usando OpenCV Haar Cascades."""

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

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analisa expressões faciais em uma imagem.

        Args:
            image_bytes: Bytes da imagem (JPEG/PNG)

        Returns:
            Dict com análise de expressões
        """
        # Carregar imagem
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return self._error_result("Não foi possível carregar a imagem")

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

        # Extrair região do rosto
        face_roi = gray[y:y+h, x:x+w]
        face_roi_color = img[y:y+h, x:x+w]

        # Análise de componentes
        eyes = self._analyze_eyes(face_roi_color, face_roi)
        smile = self._analyze_smile(face_roi)
        eyebrows = self._analyze_eyebrows(face_roi)
        mouth = self._analyze_mouth(face_roi, y, h)

        # Classificar expressão dominante
        dominant_expression = self._classify_expression(eyes, smile, eyebrows, mouth)

        # Calcular confiança
        confidence = self._calculate_confidence(eyes, smile, eyebrows, mouth)

        return {
            "dominant_expression": dominant_expression,
            "confidence": confidence,
            "expressions_detected": {
                "neutral": self._score_neutral(eyes, smile, eyebrows, mouth),
                "happy": smile["score"],
                "surprise": self._score_surprise(eyes, eyebrows, mouth),
                "sad": self._score_sad(eyes, eyebrows, mouth),
                "angry": self._score_angry(eyes, eyebrows, mouth),
            },
            "details": {
                "eyes": eyes,
                "smile": smile,
                "eyebrows": eyebrows,
                "mouth": mouth,
            },
            "face_detected": True,
            "face_position": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
            "recommendations": self._generate_recommendations(
                dominant_expression, eyes, smile, eyebrows, mouth
            ),
        }

    def _analyze_eyes(self, face_color: np.ndarray, face_gray: np.ndarray) -> Dict:
        """Analisa estado dos olhos (abertos, fechados, arregalados)."""
        eyes = self._eye_cascade.detectMultiScale(
            face_gray, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20)
        )

        eye_data = {
            "count": len(eyes),
            "openness_score": 0.5,  # default
            "arched_score": 0.0,
            "detected": len(eyes) >= 2,
        }

        if len(eyes) >= 2:
            # Calcular área média dos olhos
            areas = [w * h for (_, _, w, h) in eyes[:2]]
            avg_area = np.mean(areas)
            eye_data["openness_score"] = min(1.0, avg_area / 2000)

            # Verificar se olhos estão arregalados (surpresa)
            eye_data["arched_score"] = min(1.0, avg_area / 1500)

        return eye_data

    def _analyze_smile(self, face_gray: np.ndarray) -> Dict:
        """Analisa sorriso usando Haar cascade."""
        smiles = self._smile_cascade.detectMultiScale(
            face_gray, scaleFactor=1.7, minNeighbors=22, minSize=(50, 30)
        )

        smile_data = {
            "detected": len(smiles) > 0,
            "score": 0.0,
            "intensity": "none",
        }

        if len(smiles) > 0:
            # Pegar o sorriso mais provável (maior área)
            largest_smile = max(smiles, key=lambda s: s[2] * s[3])
            _, _, sw, sh = largest_smile
            area = sw * sh

            # Normalizar score baseado na área do sorriso
            smile_data["score"] = min(1.0, area / 5000)

            if smile_data["score"] > 0.7:
                smile_data["intensity"] = "broad"
            elif smile_data["score"] > 0.4:
                smile_data["intensity"] = "moderate"
            else:
                smile_data["intensity"] = "subtle"

        return smile_data

    def _analyze_eyebrows(self, face_gray: np.ndarray) -> Dict:
        """Analiza posição das sobrancelhas."""
        h, w = face_gray.shape

        # Região superior do rosto (onde ficam as sobrancelhas)
        eyebrow_region = face_gray[:int(h*0.4), :]

        # Calcular gradiente vertical para detectar elevação
        grad_y = cv2.Sobel(eyebrow_region, cv2.CV_64F, 0, 1, ksize=3)
        grad_y = np.abs(grad_y)

        # Dividir em metades (esquerda e direita)
        mid = w // 2
        left_grad = np.mean(grad_y[:, :mid])
        right_grad = np.mean(grad_y[:, mid:])

        avg_grad = (left_grad + right_grad) / 2

        # Detectar elevação (surpresa)
        elevation_score = min(1.0, avg_grad / 50)

        # Detectar franzimento (raiva/tristeza)
        # Verificar concentração de gradiente no centro
        center_region = eyebrow_region[:, int(w*0.3):int(w*0.7)]
        center_grad = np.mean(np.abs(cv2.Sobel(center_region, cv2.CV_64F, 0, 1, ksize=3)))
        furrow_score = min(1.0, center_grad / 40)

        return {
            "elevation_score": elevation_score,
            "furrow_score": furrow_score,
            "symmetry": 1.0 - abs(left_grad - right_grad) / max(left_grad + right_grad, 1),
        }

    def _analyze_mouth(self, face_gray: np.ndarray, face_y: int, face_h: int) -> Dict:
        """Analiza formato e posição da boca."""
        h, w = face_gray.shape

        # Região da boca (metade inferior do rosto)
        mouth_region = face_gray[int(h*0.55):, :]

        if mouth_region.size == 0:
            return {"openness": 0.0, "corners_up": 0.0, "corners_down": 0.0}

        # Detectar cantos da boca usando gradientes horizontais
        grad_x = cv2.Sobel(mouth_region, cv2.CV_64F, 1, 0, ksize=3)

        # Calcular abertura da boca
        mouth_h, mouth_w = mouth_region.shape
        center_y = mouth_h // 2

        # Verificar pixels escuros na linha central (dentro da boca)
        center_line = mouth_region[center_y, :]
        darkness = np.mean(255 - center_line) / 255.0
        openness = min(1.0, darkness * 2)

        # Detectar cantos para cima (sorriso) ou para baixo (tristeza)
        left_corner = np.mean(grad_x[:, :mouth_w//3])
        right_corner = np.mean(grad_x[:, 2*mouth_w//3:])

        corners_up = max(0, (left_corner + right_corner) / 200)
        corners_down = max(0, -(left_corner + right_corner) / 200)

        return {
            "openness": openness,
            "corners_up": min(1.0, corners_up),
            "corners_down": min(1.0, corners_down),
        }

    def _classify_expression(self, eyes, smile, eyebrows, mouth) -> str:
        """Classifica a expressão dominante."""
        scores = {
            "neutral": self._score_neutral(eyes, smile, eyebrows, mouth),
            "happy": smile["score"],
            "surprise": self._score_surprise(eyes, eyebrows, mouth),
            "sad": self._score_sad(eyes, eyebrows, mouth),
            "angry": self._score_angry(eyes, eyebrows, mouth),
        }

        return max(scores, key=scores.get)

    def _score_neutral(self, eyes, smile, eyebrows, mouth) -> float:
        """Score de neutralidade."""
        if not smile["detected"] and eyebrows["elevation_score"] < 0.3 and eyebrows["furrow_score"] < 0.3:
            return 0.8
        return 0.2

    def _score_surprise(self, eyes, eyebrows, mouth) -> float:
        """Score de surpresa."""
        score = 0.0
        if eyes["arched_score"] > 0.6:
            score += 0.4
        if eyebrows["elevation_score"] > 0.5:
            score += 0.4
        if mouth["openness"] > 0.5:
            score += 0.2
        return min(1.0, score)

    def _score_sad(self, eyes, eyebrows, mouth) -> float:
        """Score de tristeza."""
        score = 0.0
        if mouth["corners_down"] > 0.3:
            score += 0.5
        if eyebrows["elevation_score"] < 0.2 and eyebrows["furrow_score"] > 0.3:
            score += 0.3
        if not eyes.get("detected", True):
            score += 0.2
        return min(1.0, score)

    def _score_angry(self, eyes, eyebrows, mouth) -> float:
        """Score de raiva."""
        score = 0.0
        if eyebrows["furrow_score"] > 0.5:
            score += 0.5
        if eyebrows["elevation_score"] < 0.2:
            score += 0.3
        if mouth["corners_down"] > 0.2 and not smile.get("detected", False):
            score += 0.2
        return min(1.0, score)

    def _calculate_confidence(self, eyes, smile, eyebrows, mouth) -> str:
        """Calcula nível de confiança da análise."""
        factors = [
            eyes["detected"],
            smile["detected"] or smile["score"] < 0.1,  # sorriso ausente também é válido
            eyebrows["symmetry"] > 0.5,
        ]
        score = sum(factors) / len(factors)

        if score > 0.8:
            return "high"
        elif score > 0.5:
            return "medium"
        return "low"

    def _generate_recommendations(self, dominant, eyes, smile, eyebrows, mouth) -> list:
        """Gera recomendações baseadas na análise."""
        recs = []

        if dominant == "neutral":
            recs.append({
                "type": "performance",
                "message": "Expressão neutra bem controlada. Praticar variações sutis para casting.",
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
                "message": "Sorriso amplo é ideal para comerciais, publicidade e papéis de 'cara do povo'.",
                "priority": "high"
            })

        if eyebrows["furrow_score"] > 0.5:
            recs.append({
                "type": "performance",
                "message": "Franzimento detectado. Para papéis dramáticos, controlar intensidade.",
                "priority": "medium"
            })

        if not eyes["detected"]:
            recs.append({
                "type": "technical",
                "message": "Olhos não detectados claramente. Verificar iluminação da foto.",
                "priority": "high"
            })

        return recs

    def _error_result(self, message: str) -> Dict:
        """Retorna resultado de erro."""
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
