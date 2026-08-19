"""
GroomingAnalyzer - Análise real de grooming usando OpenCV + MediaPipe.
Avalia: pele, barba, sobrancelhas, cabelo, higiene geral.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class SkinMetrics:
    """Métricas de análise da pele."""
    uniformity_score: float
    brightness_score: float
    texture_score: float
    redness_score: float
    pore_visibility: float
    overall_score: float


@dataclass
class BeardMetrics:
    """Métricas de análise de barba."""
    coverage_score: float
    uniformity_score: float
    length_estimate: str
    neatness_score: float
    edge_definition: float
    overall_score: float


@dataclass
class EyebrowMetrics:
    """Métricas de análise de sobrancelhas."""
    symmetry_score: float
    thickness_score: float
    arch_score: float
    definition_score: float
    overall_score: float


@dataclass
class HairMetrics:
    """Métricas de análise de cabelo."""
    coverage_score: float
    volume_score: float
    texture_score: float
    shine_score: float
    neatness_score: float
    overall_score: float


class GroomingAnalyzer:
    """
    Analisa grooming facial usando OpenCV e heurísticas de visão computacional.
    """

    def __init__(self):
        self._face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
        )
        self._eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analisa grooming em uma imagem facial.

        Args:
            image_bytes: Bytes da imagem

        Returns:
            Dict com análise completa de grooming
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
        skin = self._analyze_skin(face_roi_color, face_roi)
        beard = self._analyze_beard(face_roi_color, face_roi, x, y, w, h)
        eyebrows = self._analyze_eyebrows(face_roi_color, face_roi, x, y, w, h)
        hair = self._analyze_hair(img, gray, x, y, w, h)
        hygiene = self._analyze_hygiene_overall(skin, beard, eyebrows, hair)

        # Score geral
        overall_score = self._calculate_overall_score(skin, beard, eyebrows, hair)

        return {
            "overall_score": round(overall_score, 2),
            "score_out_of_10": round(overall_score * 10, 1),
            "grooming_level": self._level_from_score(overall_score),
            "confidence": self._calculate_confidence(skin, beard, eyebrows, hair),
            "dimensions": {
                "skin": self._skin_to_dict(skin),
                "beard": self._beard_to_dict(beard),
                "eyebrows": self._eyebrow_to_dict(eyebrows),
                "hair": self._hair_to_dict(hair),
                "hygiene": hygiene,
            },
            "face_detected": True,
            "face_position": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
            "recommendations": self._generate_recommendations(skin, beard, eyebrows, hair, hygiene),
            "grooming_plan": self._generate_grooming_plan(skin, beard, eyebrows, hair),
        }

    # ========== SKIN ANALYSIS ==========

    def _analyze_skin(self, face_color: np.ndarray, face_gray: np.ndarray) -> SkinMetrics:
        """Analisa qualidade da pele."""
        h, w = face_gray.shape

        # Uniformidade (variação de tom)
        mean_val = np.mean(face_gray)
        std_val = np.std(face_gray)
        uniformity = max(0, 1.0 - std_val / 80)

        # Brilho (luminosidade média)
        brightness = mean_val / 255.0
        # Ideal: 0.4 - 0.7 (nem muito claro nem muito escuro)
        if 0.4 <= brightness <= 0.7:
            brightness_score = 1.0
        else:
            brightness_score = max(0, 1.0 - abs(brightness - 0.55) * 2)

        # Textura (usar Laplacian para detectar rugosidade)
        laplacian = cv2.Laplacian(face_gray, cv2.CV_64F)
        texture_var = laplacian.var()
        # Textura muito alta = pele irregular; muito baixa = pele muito lisa (possível filtro)
        if 50 <= texture_var <= 300:
            texture_score = 1.0
        else:
            texture_score = max(0, 1.0 - abs(texture_var - 175) / 300)

        # Vermelhidão (análise no canal R do RGB)
        b, g, r = cv2.split(face_color)
        redness = np.mean(r) / 255.0
        greenness = np.mean(g) / 255.0
        # Ratio R/G alto indica vermelhidão
        redness_ratio = redness / (greenness + 0.01)
        redness_score = max(0, 1.0 - abs(redness_ratio - 1.0) * 2)

        # Visibilidade de poros (análise de frequências altas)
        # Usar DCT ou simplesmente variação local
        local_var = np.array([
            np.std(face_gray[i:i+10, j:j+10])
            for i in range(0, h-10, 10)
            for j in range(0, w-10, 10)
        ])
        pore_visibility = min(1.0, np.mean(local_var) / 30)
        pore_score = max(0, 1.0 - pore_visibility)

        overall = (
            uniformity * 0.25 +
            brightness_score * 0.25 +
            texture_score * 0.20 +
            redness_score * 0.15 +
            pore_score * 0.15
        )

        return SkinMetrics(
            uniformity_score=round(uniformity, 3),
            brightness_score=round(brightness_score, 3),
            texture_score=round(texture_score, 3),
            redness_score=round(redness_score, 3),
            pore_visibility=round(pore_visibility, 3),
            overall_score=round(overall, 3),
        )

    # ========== BEARD ANALYSIS ==========

    def _analyze_beard(
        self, face_color: np.ndarray, face_gray: np.ndarray,
        face_x: int, face_y: int, face_w: int, face_h: int
    ) -> BeardMetrics:
        """Analisa barba na região inferior do rosto."""
        h, w = face_gray.shape

        # Região da barba: metade inferior do rosto
        beard_region = face_gray[int(h*0.55):, :]
        beard_color = face_color[int(h*0.55):, :]

        if beard_region.size == 0:
            return BeardMetrics(0, 0, "none", 0, 0, 0)

        # Detectar cobertura (diferença de textura entre pele e barba)
        # Barba tem textura mais irregular
        beard_laplacian = cv2.Laplacian(beard_region, cv2.CV_64F)
        beard_texture = beard_laplacian.var()
        upper_face = face_gray[:int(h*0.55), :]
        upper_laplacian = cv2.Laplacian(upper_face, cv2.CV_64F)
        upper_texture = upper_laplacian.var()

        # Se textura da região inferior for muito maior, provavelmente tem barba
        texture_ratio = beard_texture / (upper_texture + 1)
        coverage = min(1.0, max(0, (texture_ratio - 0.5) * 0.8))

        # Uniformidade da barba
        beard_std = np.std(beard_region)
        uniformity = max(0, 1.0 - beard_std / 60)

        # Estimativa de comprimento baseada na textura
        if coverage < 0.2:
            length = "none"
        elif texture_ratio < 1.5:
            length = "stubble"
        elif texture_ratio < 2.5:
            length = "short"
        elif texture_ratio < 4.0:
            length = "medium"
        else:
            length = "long"

        # Definição de bordas (gradientes na transição barba/pele)
        grad_y = cv2.Sobel(beard_region, cv2.CV_64F, 0, 1, ksize=3)
        edge_strength = np.mean(np.abs(grad_y))
        edge_definition = min(1.0, edge_strength / 30)

        # Aparência geral (neatness)
        neatness = uniformity * 0.6 + edge_definition * 0.4

        overall = coverage * 0.3 + uniformity * 0.25 + neatness * 0.25 + edge_definition * 0.2

        return BeardMetrics(
            coverage_score=round(coverage, 3),
            uniformity_score=round(uniformity, 3),
            length_estimate=length,
            neatness_score=round(neatness, 3),
            edge_definition=round(edge_definition, 3),
            overall_score=round(overall, 3),
        )

    # ========== EYEBROW ANALYSIS ==========

    def _analyze_eyebrows(
        self, face_color: np.ndarray, face_gray: np.ndarray,
        face_x: int, face_y: int, face_w: int, face_h: int
    ) -> EyebrowMetrics:
        """Analisa sobrancelhas na região superior do rosto."""
        h, w = face_gray.shape

        # Região das sobrancelhas: 20-45% da altura do rosto
        eyebrow_region = face_gray[int(h*0.20):int(h*0.45), :]

        if eyebrow_region.size == 0:
            return EyebrowMetrics(0.5, 0.5, 0.5, 0.5, 0.5)

        # Simetria: comparar metades esquerda e direita
        mid = w // 2
        left_half = eyebrow_region[:, :mid]
        right_half = eyebrow_region[:, mid:]

        left_mean = np.mean(left_half)
        right_mean = np.mean(right_half)
        symmetry = max(0, 1.0 - abs(left_mean - right_mean) / 100)

        # Espessura: densidade de pixels escuros na região
        darkness = 1.0 - np.mean(eyebrow_region) / 255.0
        thickness = min(1.0, darkness * 2)

        # Arco: análise de curvatura usando gradientes
        grad_x = cv2.Sobel(eyebrow_region, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(eyebrow_region, cv2.CV_64F, 0, 1, ksize=3)

        # Arco elevado tem gradiente Y significativo
        arch_strength = min(1.0, np.mean(np.abs(grad_y)) / 20)

        # Definição: contraste entre sobrancelha e pele
        _, thresh = cv2.threshold(eyebrow_region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        definition = np.sum(thresh > 0) / thresh.size

        overall = symmetry * 0.3 + thickness * 0.2 + arch_strength * 0.2 + definition * 0.3

        return EyebrowMetrics(
            symmetry_score=round(symmetry, 3),
            thickness_score=round(thickness, 3),
            arch_score=round(arch_strength, 3),
            definition_score=round(definition, 3),
            overall_score=round(overall, 3),
        )

    # ========== HAIR ANALYSIS ==========

    def _analyze_hair(
        self, img: np.ndarray, gray: np.ndarray,
        face_x: int, face_y: int, face_w: int, face_h: int
    ) -> HairMetrics:
        """Analisa cabelo na região acima do rosto."""
        img_h, img_w = img.shape[:2]

        # Região do cabelo: acima do rosto detectado
        hair_y_start = max(0, face_y - int(face_h * 0.8))
        hair_y_end = face_y + int(face_h * 0.3)
        hair_x_start = max(0, face_x - int(face_w * 0.2))
        hair_x_end = min(img_w, face_x + face_w + int(face_w * 0.2))

        hair_region = gray[hair_y_start:hair_y_end, hair_x_start:hair_x_end]
        hair_color = img[hair_y_start:hair_y_end, hair_x_start:hair_x_end]

        if hair_region.size == 0:
            return HairMetrics(0, 0, 0, 0, 0, 0)

        # Cobertura: quantidade de cabelo visível
        darkness = 1.0 - np.mean(hair_region) / 255.0
        coverage = min(1.0, darkness * 1.5)

        # Volume: variação de altura do cabelo
        hair_edges = cv2.Canny(hair_region, 50, 150)
        edge_density = np.sum(hair_edges > 0) / hair_edges.size
        volume = min(1.0, edge_density * 5)

        # Textura: irregularidade do cabelo
        hair_laplacian = cv2.Laplacian(hair_region, cv2.CV_64F)
        texture = min(1.0, hair_laplacian.var() / 500)

        # Brilho: análise de highlights no cabelo
        if hair_color.size > 0:
            hsv = cv2.cvtColor(hair_color, cv2.COLOR_BGR2HSV)
            v_channel = hsv[:, :, 2]
            shine = min(1.0, np.std(v_channel) / 80)
        else:
            shine = 0.5

        # Aparência geral
        neatness = coverage * 0.3 + volume * 0.2 + texture * 0.2 + shine * 0.3

        overall = coverage * 0.25 + volume * 0.20 + texture * 0.20 + shine * 0.20 + neatness * 0.15

        return HairMetrics(
            coverage_score=round(coverage, 3),
            volume_score=round(volume, 3),
            texture_score=round(texture, 3),
            shine_score=round(shine, 3),
            neatness_score=round(neatness, 3),
            overall_score=round(overall, 3),
        )

    # ========== HYGIENE OVERALL ==========

    def _analyze_hygiene_overall(
        self, skin: SkinMetrics, beard: BeardMetrics,
        eyebrows: EyebrowMetrics, hair: HairMetrics
    ) -> Dict[str, Any]:
        """Avalia higiene geral combinando todas as métricas."""
        scores = [
            skin.overall_score,
            beard.overall_score if beard.coverage_score > 0.1 else 0.8,
            eyebrows.overall_score,
            hair.overall_score,
        ]

        overall = np.mean(scores)

        concerns = []
        if skin.redness_score < 0.5:
            concerns.append("Vermelhidão na pele detectada")
        if skin.pore_visibility > 0.7:
            concerns.append("Poros dilatados visíveis")
        if beard.neatness_score < 0.4 and beard.coverage_score > 0.2:
            concerns.append("Barba desalinhada")
        if eyebrows.symmetry_score < 0.5:
            concerns.append("Sobrancelhas assimétricas")
        if hair.neatness_score < 0.4:
            concerns.append("Cabelo desalinhado")

        return {
            "overall_score": round(overall, 3),
            "level": "high" if overall > 0.75 else "medium" if overall > 0.5 else "low",
            "concerns": concerns if concerns else ["Higiene geral adequada"],
            "positive_aspects": self._positive_aspects(skin, beard, eyebrows, hair),
        }

    def _positive_aspects(
        self, skin: SkinMetrics, beard: BeardMetrics,
        eyebrows: EyebrowMetrics, hair: HairMetrics
    ) -> List[str]:
        """Lista aspectos positivos do grooming."""
        positives = []

        if skin.uniformity_score > 0.7:
            positives.append("Pele uniforme e bem cuidada")
        if skin.brightness_score > 0.7:
            positives.append("Brilho natural saudável")
        if beard.neatness_score > 0.7 and beard.coverage_score > 0.2:
            positives.append("Barba bem aparada")
        if eyebrows.definition_score > 0.7:
            positives.append("Sobrancelhas bem definidas")
        if hair.shine_score > 0.6:
            positives.append("Cabelo com brilho saudável")
        if hair.volume_score > 0.6:
            positives.append("Bom volume capilar")

        return positives if positives else ["Aparência geral adequada"]

    # ========== SCORING & LEVELS ==========

    def _calculate_overall_score(
        self, skin: SkinMetrics, beard: BeardMetrics,
        eyebrows: EyebrowMetrics, hair: HairMetrics
    ) -> float:
        """Calcula score geral de grooming."""
        weights = {
            "skin": 0.35,
            "beard": 0.20,
            "eyebrows": 0.20,
            "hair": 0.25,
        }

        # Se não tiver barba, redistribuir peso
        if beard.coverage_score < 0.1:
            weights["beard"] = 0
            weights["skin"] = 0.45
            weights["eyebrows"] = 0.25
            weights["hair"] = 0.30

        score = (
            skin.overall_score * weights["skin"] +
            beard.overall_score * weights["beard"] +
            eyebrows.overall_score * weights["eyebrows"] +
            hair.overall_score * weights["hair"]
        )

        return min(1.0, max(0.0, score))

    def _calculate_confidence(
        self, skin: SkinMetrics, beard: BeardMetrics,
        eyebrows: EyebrowMetrics, hair: HairMetrics
    ) -> str:
        """Calcula confiança da análise."""
        scores = [skin.overall_score, beard.overall_score, eyebrows.overall_score, hair.overall_score]
        avg = np.mean(scores)

        if avg > 0.6:
            return "high"
        elif avg > 0.35:
            return "medium"
        return "low"

    def _level_from_score(self, score: float) -> str:
        """Converte score em nível descritivo."""
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

    # ========== RECOMMENDATIONS ==========

    def _generate_recommendations(
        self, skin: SkinMetrics, beard: BeardMetrics,
        eyebrows: EyebrowMetrics, hair: HairMetrics, hygiene: Dict
    ) -> List[Dict[str, Any]]:
        """Gera recomendações de grooming."""
        recs = []

        # Skin recommendations
        if skin.uniformity_score < 0.5:
            recs.append({
                "category": "skin",
                "message": "Considerar uso de base ou corretivo para uniformizar o tom da pele",
                "priority": "high",
                "products": ["Base leve", "Corretivo", "Pó translúcido"],
            })

        if skin.brightness_score < 0.4:
            recs.append({
                "category": "skin",
                "message": "Pele opaca. Hidratação e iluminador podem ajudar",
                "priority": "medium",
                "products": ["Hidratante facial", "Iluminador líquido", "Vitamina C"],
            })

        if skin.redness_score < 0.4:
            recs.append({
                "category": "skin",
                "message": "Vermelhidão detectada. Usar produtos calmantes",
                "priority": "medium",
                "products": ["Creme com niacinamida", "Protetor solar", "Água termal"],
            })

        # Beard recommendations
        if beard.coverage_score > 0.2 and beard.neatness_score < 0.5:
            recs.append({
                "category": "beard",
                "message": f"Barba {beard.length_estimate} precisa de aparo. Definir linhas de bochecha e pescoço",
                "priority": "high",
                "products": ["Aparador de barba", "Tesoura de precisão", "Óleo de barba"],
                "frequency": "A cada 2-3 dias",
            })
        elif beard.coverage_score > 0.2 and beard.neatness_score > 0.7:
            recs.append({
                "category": "beard",
                "message": f"Barba {beard.length_estimate} bem cuidada. Manter rotina atual",
                "priority": "low",
                "products": ["Bálsamo de barba", "Óleo de barba"],
                "frequency": "Diária",
            })

        # Eyebrow recommendations
        if eyebrows.symmetry_score < 0.5:
            recs.append({
                "category": "eyebrows",
                "message": "Sobrancelhas assimétricas. Considerar design profissional",
                "priority": "medium",
                "products": ["Lápis de sobrancelha", "Gel fixador", "Pinça"],
                "frequency": "A cada 15-20 dias",
            })

        if eyebrows.definition_score < 0.4:
            recs.append({
                "category": "eyebrows",
                "message": "Sobrancelhas pouco definidas. Preenchimento sutil recomendado",
                "priority": "low",
                "products": ["Sombra para sobrancelhas", "Lápis marrom", "Máscara de sobrancelhas"],
            })

        # Hair recommendations
        if hair.neatness_score < 0.4:
            recs.append({
                "category": "hair",
                "message": "Cabelo precisa de corte ou finalização. Verificar pontas duplas",
                "priority": "high",
                "products": ["Creme de pentear", "Óleo capilar", "Protetor térmico"],
                "frequency": "Corte a cada 4-6 semanas",
            })

        if hair.shine_score < 0.3:
            recs.append({
                "category": "hair",
                "message": "Cabelo sem brilho. Tratamento de hidratação recomendado",
                "priority": "medium",
                "products": ["Máscara de hidratação", "Óleo de argan", "Leave-in"],
            })

        if not recs:
            recs.append({
                "category": "general",
                "message": "Grooming excelente! Manter rotina atual de cuidados",
                "priority": "low",
            })

        return recs

    def _generate_grooming_plan(
        self, skin: SkinMetrics, beard: BeardMetrics,
        eyebrows: EyebrowMetrics, hair: HairMetrics
    ) -> List[str]:
        """Gera plano de grooming diário/semanal."""
        plan = []

        # Rotina diária
        plan.append("Limpeza facial diária (manhã e noite)")
        plan.append("Hidratação facial após limpeza")

        if beard.coverage_score > 0.2:
            plan.append("Aplicação de óleo/bálsamo de barba")

        plan.append("Protetor solar facial (manhã)")

        # Rotina semanal
        plan.append("Exfoliação facial 1-2x por semana")

        if hair.neatness_score < 0.6:
            plan.append("Hidratação capilar semanal")

        # Rotina mensal
        plan.append("Design de sobrancelhas a cada 15-20 dias")

        if beard.coverage_score > 0.2:
            plan.append("Aparo de barba a cada 3-5 dias")

        if hair.neatness_score < 0.6:
            plan.append("Corte de cabelo a cada 4-6 semanas")

        return plan

    # ========== SERIALIZERS ==========

    def _skin_to_dict(self, skin: SkinMetrics) -> Dict:
        return {
            "overall_score": skin.overall_score,
            "uniformity": skin.uniformity_score,
            "brightness": skin.brightness_score,
            "texture": skin.texture_score,
            "redness": skin.redness_score,
            "pore_visibility": skin.pore_visibility,
            "level": "high" if skin.overall_score > 0.7 else "medium" if skin.overall_score > 0.45 else "low",
        }

    def _beard_to_dict(self, beard: BeardMetrics) -> Dict:
        return {
            "overall_score": beard.overall_score,
            "coverage": beard.coverage_score,
            "uniformity": beard.uniformity_score,
            "length_estimate": beard.length_estimate,
            "neatness": beard.neatness_score,
            "edge_definition": beard.edge_definition,
            "level": "high" if beard.overall_score > 0.7 else "medium" if beard.overall_score > 0.45 else "low",
        }

    def _eyebrow_to_dict(self, eyebrows: EyebrowMetrics) -> Dict:
        return {
            "overall_score": eyebrows.overall_score,
            "symmetry": eyebrows.symmetry_score,
            "thickness": eyebrows.thickness_score,
            "arch": eyebrows.arch_score,
            "definition": eyebrows.definition_score,
            "level": "high" if eyebrows.overall_score > 0.7 else "medium" if eyebrows.overall_score > 0.45 else "low",
        }

    def _hair_to_dict(self, hair: HairMetrics) -> Dict:
        return {
            "overall_score": hair.overall_score,
            "coverage": hair.coverage_score,
            "volume": hair.volume_score,
            "texture": hair.texture_score,
            "shine": hair.shine_score,
            "neatness": hair.neatness_score,
            "level": "high" if hair.overall_score > 0.7 else "medium" if hair.overall_score > 0.45 else "low",
        }

    # ========== ERROR HANDLING ==========

    def _error_result(self, message: str) -> Dict:
        return {
            "overall_score": 0.0,
            "score_out_of_10": 0.0,
            "grooming_level": "unknown",
            "confidence": "low",
            "dimensions": {},
            "face_detected": False,
            "error": message,
            "recommendations": [{
                "category": "technical",
                "message": message,
                "priority": "high",
            }],
            "grooming_plan": [],
        }
