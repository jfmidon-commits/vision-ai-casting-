"""
PhotogenicAnalyzer - Análise real de fotogenia usando OpenCV.
Avalia: simetria, iluminação, enquadramento, nitidez, proporções.
"""

import cv2
import numpy as np
from typing import Dict, Any, List


class PhotogenicAnalyzer:
    """Analisa fotogenia de imagens faciais usando métricas objetivas."""

    def __init__(self):
        self._face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
        )
        self._profile_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_profileface.xml'
        )

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analisa fotogenia de uma imagem.

        Args:
            image_bytes: Bytes da imagem

        Returns:
            Dict com análise de fotogenia
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return self._error_result("Não foi possível carregar a imagem")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detectar faces
        faces = self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100)
        )

        if len(faces) == 0:
            return self._error_result("Nenhum rosto detectado")

        # Analisar maior face
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = largest_face

        face_roi = gray[y:y+h, x:x+w]
        face_roi_color = img[y:y+h, x:x+w]

        # Análises individuais
        symmetry = self._analyze_symmetry(face_roi)
        lighting = self._analyze_lighting(face_roi_color, face_roi)
        framing = self._analyze_framing(x, y, w, h, img.shape)
        sharpness = self._analyze_sharpness(face_roi)
        proportions = self._analyze_proportions(w, h, face_roi)
        exposure = self._analyze_exposure(face_roi_color)

        # Score geral de fotogenia
        overall_score = self._calculate_overall_score(
            symmetry, lighting, framing, sharpness, proportions, exposure
        )

        return {
            "overall_score": round(overall_score, 2),
            "score_out_of_10": round(overall_score * 10, 1),
            "photogenic_level": self._level_from_score(overall_score),
            "confidence": self._calculate_confidence(symmetry, lighting, framing, sharpness),
            "dimensions": {
                "symmetry": symmetry,
                "lighting": lighting,
                "framing": framing,
                "sharpness": sharpness,
                "proportions": proportions,
                "exposure": exposure,
            },
            "face_detected": True,
            "face_position": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
            "recommendations": self._generate_recommendations(
                symmetry, lighting, framing, sharpness, proportions, exposure
            ),
        }

    def _analyze_symmetry(self, face_gray: np.ndarray) -> Dict:
        """Analisa simetria facial."""
        h, w = face_gray.shape

        # Dividir rosto ao meio
        left_half = face_gray[:, :w//2]
        right_half = face_gray[:, w//2:]

        # Espelhar metade direita para comparar
        right_flipped = cv2.flip(right_half, 1)

        # Redimensionar para mesmo tamanho
        min_w = min(left_half.shape[1], right_flipped.shape[1])
        left_cropped = left_half[:, :min_w]
        right_cropped = right_flipped[:, :min_w]

        # Calcular diferença
        diff = cv2.absdiff(left_cropped, right_cropped)
        mean_diff = np.mean(diff)

        # Normalizar: 0 = perfeitamente simétrico, 255 = completamente assimétrico
        symmetry_score = max(0, 1.0 - (mean_diff / 255.0))

        # Leve assimetria é natural e pode adicionar caráter
        # Score ideal: 0.7-0.9 (não perfeito, mas harmonioso)
        if 0.65 <= symmetry_score <= 0.92:
            harmony_score = 1.0
        else:
            harmony_score = 1.0 - abs(symmetry_score - 0.78) * 2

        return {
            "score": round(symmetry_score, 3),
            "harmony_score": round(harmony_score, 3),
            "level": "high" if symmetry_score > 0.8 else "medium" if symmetry_score > 0.6 else "low",
            "note": "Leve assimetria natural acrescenta caráter e autenticidade" if symmetry_score < 0.9 else "Simetria muito alta pode parecer artificial",
        }

    def _analyze_lighting(self, face_color: np.ndarray, face_gray: np.ndarray) -> Dict:
        """Analisa qualidade da iluminação."""
        # Calcular histograma
        hist = cv2.calcHist([face_gray], [0], None, [256], [0, 256])
        hist = hist.flatten() / hist.sum()

        # Entropia do histograma (distribuição de tons)
        entropy = -np.sum(hist * np.log2(hist + 1e-10))
        max_entropy = 8.0  # 8 bits
        entropy_score = entropy / max_entropy

        # Verificar se há sombras duras
        grad_x = cv2.Sobel(face_gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(face_gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)

        # Gradientes muito altos indicam sombras duras
        hard_shadow_ratio = np.sum(gradient_magnitude > 100) / gradient_magnitude.size
        shadow_score = max(0, 1.0 - hard_shadow_ratio * 5)

        # Verificar preenchimento (fill light)
        # Comparar metades iluminadas
        left_brightness = np.mean(face_gray[:, :face_gray.shape[1]//2])
        right_brightness = np.mean(face_gray[:, face_gray.shape[1]//2:])
        fill_ratio = 1.0 - abs(left_brightness - right_brightness) / 255.0

        overall_lighting = (entropy_score * 0.3 + shadow_score * 0.4 + fill_ratio * 0.3)

        return {
            "score": round(overall_lighting, 3),
            "entropy": round(entropy_score, 3),
            "shadow_quality": round(shadow_score, 3),
            "fill_quality": round(fill_ratio, 3),
            "level": "high" if overall_lighting > 0.75 else "medium" if overall_lighting > 0.5 else "low",
            "note": self._lighting_note(overall_lighting, hard_shadow_ratio),
        }

    def _lighting_note(self, score: float, hard_shadow_ratio: float) -> str:
        if score > 0.8:
            return "Iluminação excelente, luz difusa e bem distribuída"
        elif hard_shadow_ratio > 0.15:
            return "Sombras duras detectadas. Preferir luz difusa para retratos"
        elif score > 0.5:
            return "Iluminação adequada, pode melhorar com preenchimento"
        else:
            return "Iluminação insuficiente ou desbalanceada"

    def _analyze_framing(self, x: int, y: int, w: int, h: int, img_shape: tuple) -> Dict:
        """Analisa enquadramento do rosto."""
        img_h, img_w = img_shape[:2]

        # Regra dos terços
        face_center_x = x + w // 2
        face_center_y = y + h // 2

        third_x = img_w // 3
        third_y = img_h // 3

        # Distância até linhas dos terços
        dist_to_third_x = min(abs(face_center_x - third_x), abs(face_center_x - 2 * third_x))
        dist_to_third_y = min(abs(face_center_y - third_y), abs(face_center_y - 2 * third_y))

        thirds_score = 1.0 - (dist_to_third_x / img_w + dist_to_third_y / img_h) / 2

        # Proporção do rosto na imagem
        face_area = w * h
        img_area = img_w * img_h
        face_ratio = face_area / img_area

        # Proporção ideal para retrato: 15-40% da imagem
        if 0.15 <= face_ratio <= 0.40:
            ratio_score = 1.0
        else:
            ratio_score = max(0, 1.0 - abs(face_ratio - 0.275) * 3)

        # Cabeça não cortada
        margin = 20  # pixels
        head_complete = (x > margin and y > margin and
                        x + w < img_w - margin and y + h < img_h - margin)

        completeness_score = 1.0 if head_complete else 0.5

        overall_framing = (thirds_score * 0.3 + ratio_score * 0.5 + completeness_score * 0.2)

        return {
            "score": round(overall_framing, 3),
            "thirds_composition": round(thirds_score, 3),
            "face_ratio": round(face_ratio, 3),
            "ratio_score": round(ratio_score, 3),
            "head_complete": head_complete,
            "level": "high" if overall_framing > 0.75 else "medium" if overall_framing > 0.5 else "low",
        }

    def _analyze_sharpness(self, face_gray: np.ndarray) -> Dict:
        """Analisa nitidez/foco da imagem."""
        # Usar Laplacian para detectar bordas
        laplacian = cv2.Laplacian(face_gray, cv2.CV_64F)
        laplacian_var = laplacian.var()

        # Normalizar: valores típicos
        # < 100 = muito borrado
        # 100-500 = aceitável
        # > 500 = nítido
        if laplacian_var > 500:
            sharpness_score = 1.0
        elif laplacian_var > 100:
            sharpness_score = (laplacian_var - 100) / 400
        else:
            sharpness_score = laplacian_var / 100 * 0.5

        # Verificar motion blur
        # Comparar gradientes em X e Y
        grad_x = cv2.Sobel(face_gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(face_gray, cv2.CV_64F, 0, 1, ksize=3)

        grad_x_mean = np.mean(np.abs(grad_x))
        grad_y_mean = np.mean(np.abs(grad_y))

        # Se um gradiente for muito maior que o outro, pode indicar motion blur
        motion_ratio = max(grad_x_mean, grad_y_mean) / (min(grad_x_mean, grad_y_mean) + 1e-10)
        motion_blur_score = max(0, 1.0 - (motion_ratio - 1.0) * 0.5)

        overall_sharpness = sharpness_score * 0.7 + motion_blur_score * 0.3

        return {
            "score": round(overall_sharpness, 3),
            "laplacian_variance": round(laplacian_var, 1),
            "motion_blur_score": round(motion_blur_score, 3),
            "level": "high" if overall_sharpness > 0.8 else "medium" if overall_sharpness > 0.5 else "low",
            "note": "Imagem nítida" if overall_sharpness > 0.8 else "Leve desfoque aceitável" if overall_sharpness > 0.5 else "Imagem muito borrada",
        }

    def _analyze_proportions(self, w: int, h: int, face_gray: np.ndarray) -> Dict:
        """Analisa proporções faciais."""
        # Proporção largura/altura do rosto
        face_ratio = w / h

        # Proporção ideal (rosto oval): 0.75 - 0.85
        ideal_ratio = 0.80
        ratio_deviation = abs(face_ratio - ideal_ratio)
        ratio_score = max(0, 1.0 - ratio_deviation * 3)

        # Detectar olhos para proporção olhos/rosto
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        eyes = eye_cascade.detectMultiScale(face_gray, scaleFactor=1.1, minNeighbors=3)

        eye_score = 0.5
        if len(eyes) >= 2:
            # Distância entre olhos ideal = 1 olho de distância
            eyes = sorted(eyes, key=lambda e: e[0])[:2]
            eye_distance = eyes[1][0] - (eyes[0][0] + eyes[0][2])
            avg_eye_width = (eyes[0][2] + eyes[1][2]) / 2

            if avg_eye_width > 0:
                distance_ratio = eye_distance / avg_eye_width
                # Ideal: 0.8 - 1.2 (distância entre olhos ≈ largura de um olho)
                eye_score = max(0, 1.0 - abs(distance_ratio - 1.0))

        overall_proportions = ratio_score * 0.6 + eye_score * 0.4

        return {
            "score": round(overall_proportions, 3),
            "face_ratio": round(face_ratio, 3),
            "ratio_score": round(ratio_score, 3),
            "eye_proportion_score": round(eye_score, 3),
            "level": "high" if overall_proportions > 0.8 else "medium" if overall_proportions > 0.6 else "low",
        }

    def _analyze_exposure(self, face_color: np.ndarray) -> Dict:
        """Analisa exposição da imagem."""
        # Converter para LAB para análise de luminosidade
        lab = cv2.cvtColor(face_color, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]

        # Histograma do canal L
        mean_l = np.mean(l_channel)
        std_l = np.std(l_channel)

        # Exposição ideal: média em torno de 128 (meio tom)
        exposure_deviation = abs(mean_l - 128) / 128
        exposure_score = max(0, 1.0 - exposure_deviation)

        # Contraste ideal: std em torno de 40-80
        if 30 <= std_l <= 90:
            contrast_score = 1.0
        else:
            contrast_score = max(0, 1.0 - abs(std_l - 60) / 60)

        # Verificar clipping (áreas muito claras ou escuras)
        dark_pixels = np.sum(l_channel < 20) / l_channel.size
        bright_pixels = np.sum(l_channel > 240) / l_channel.size
        clipping_score = max(0, 1.0 - (dark_pixels + bright_pixels) * 5)

        overall_exposure = exposure_score * 0.4 + contrast_score * 0.4 + clipping_score * 0.2

        return {
            "score": round(overall_exposure, 3),
            "mean_brightness": round(mean_l, 1),
            "contrast": round(std_l, 1),
            "clipping_score": round(clipping_score, 3),
            "level": "high" if overall_exposure > 0.8 else "medium" if overall_exposure > 0.5 else "low",
            "note": self._exposure_note(mean_l, std_l, dark_pixels, bright_pixels),
        }

    def _exposure_note(self, mean_l: float, std_l: float, dark: float, bright: float) -> str:
        if mean_l < 50:
            return "Imagem subexposta (muito escura)"
        elif mean_l > 200:
            return "Imagem superexposta (muito clara)"
        elif dark > 0.1:
            return "Sombras muito profundas (crushed blacks)"
        elif bright > 0.1:
            return "Highlights estourados"
        elif std_l < 30:
            return "Contraste muito baixo (imagem plana)"
        else:
            return "Exposição bem balanceada"

    def _calculate_overall_score(self, symmetry, lighting, framing, sharpness, proportions, exposure) -> float:
        """Calcula score geral de fotogenia."""
        weights = {
            "symmetry": 0.15,
            "lighting": 0.25,
            "framing": 0.20,
            "sharpness": 0.15,
            "proportions": 0.15,
            "exposure": 0.10,
        }

        score = (
            symmetry["score"] * weights["symmetry"] +
            lighting["score"] * weights["lighting"] +
            framing["score"] * weights["framing"] +
            sharpness["score"] * weights["sharpness"] +
            proportions["score"] * weights["proportions"] +
            exposure["score"] * weights["exposure"]
        )

        return min(1.0, max(0.0, score))

    def _calculate_confidence(self, symmetry, lighting, framing, sharpness) -> str:
        """Calcula confiança da análise."""
        scores = [symmetry["score"], lighting["score"], framing["score"], sharpness["score"]]
        avg = np.mean(scores)

        if avg > 0.7 and all(s > 0.3 for s in scores):
            return "high"
        elif avg > 0.4:
            return "medium"
        return "low"

    def _level_from_score(self, score: float) -> str:
        """Converte score numérico em nível descritivo."""
        if score >= 0.85:
            return "excellent"
        elif score >= 0.70:
            return "very_good"
        elif score >= 0.55:
            return "good"
        elif score >= 0.40:
            return "average"
        elif score >= 0.25:
            return "below_average"
        return "poor"

    def _generate_recommendations(self, symmetry, lighting, framing, sharpness, proportions, exposure) -> List[Dict]:
        """Gera recomendações baseadas na análise."""
        recs = []

        if symmetry["score"] < 0.6:
            recs.append({
                "type": "pose",
                "message": "Rosto ligeiramente de perfil pode criar linhas mais dinâmicas",
                "priority": "medium"
            })

        if lighting["score"] < 0.6:
            recs.append({
                "type": "lighting",
                "message": "Preferir luz difusa (janela com cortina) para suavizar sombras",
                "priority": "high"
            })

        if framing["score"] < 0.6:
            recs.append({
                "type": "framing",
                "message": "Posicionar rosto ocupando 20-30% da imagem, seguindo regra dos terços",
                "priority": "medium"
            })

        if sharpness["score"] < 0.5:
            recs.append({
                "type": "technical",
                "message": "Verificar foco da câmera. Usar estabilização ou tripé.",
                "priority": "high"
            })

        if proportions["score"] < 0.6:
            recs.append({
                "type": "angle",
                "message": "Ângulo da câmera ligeiramente acima do nível dos olhos valoriza proporções",
                "priority": "medium"
            })

        if exposure["score"] < 0.5:
            recs.append({
                "type": "exposure",
                "message": "Ajustar exposição para evitar áreas muito claras ou escuras",
                "priority": "high"
            })

        if not recs:
            recs.append({
                "type": "general",
                "message": "Fotogenia excelente. Manter este padrão para todos os ensaios.",
                "priority": "low"
            })

        return recs

    def _error_result(self, message: str) -> Dict:
        return {
            "overall_score": 0.0,
            "score_out_of_10": 0.0,
            "photogenic_level": "unknown",
            "confidence": "low",
            "dimensions": {},
            "face_detected": False,
            "error": message,
            "recommendations": [{
                "type": "technical",
                "message": message,
                "priority": "high"
            }],
        }
