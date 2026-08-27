"""
GroomingAnalyzer - Analise real de grooming usando MediaPipe FaceMesh + OpenCV.
Avalia: pele, barba, sobrancelhas, cabelo, higiene geral com landmarks precisos.

Usa MediaPipe FaceMesh (468 landmarks) para definir regioes exatas do rosto,
permitindo analise precisa de cada area de grooming.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SkinMetrics:
    """Metricas de analise da pele."""

    uniformity_score: float
    brightness_score: float
    texture_score: float
    redness_score: float
    pore_visibility: float
    overall_score: float


@dataclass
class BeardMetrics:
    """Metricas de analise de barba."""

    coverage_score: float
    uniformity_score: float
    length_estimate: str
    neatness_score: float
    edge_definition: float
    overall_score: float


@dataclass
class EyebrowMetrics:
    """Metricas de analise de sobrancelhas."""

    symmetry_score: float
    thickness_score: float
    arch_score: float
    definition_score: float
    overall_score: float


@dataclass
class HairMetrics:
    """Metricas de analise de cabelo."""

    coverage_score: float
    volume_score: float
    texture_score: float
    shine_score: float
    neatness_score: float
    overall_score: float


class GroomingAnalyzer:
    """
    Analisa grooming facial usando MediaPipe FaceMesh + OpenCV.
    Usa 468 landmarks para definir regioes precisas do rosto.
    """

    # MediaPipe FaceMesh landmark indices
    FACE_OVAL = [
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
    ]

    LEFT_EYEBROW = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
    RIGHT_EYEBROW = [336, 296, 334, 293, 300, 276, 283, 282, 295, 285]

    LEFT_EYE = [
        33,
        246,
        161,
        160,
        159,
        158,
        157,
        173,
        133,
        155,
        154,
        153,
        145,
        144,
        163,
        7,
    ]
    RIGHT_EYE = [
        362,
        398,
        384,
        385,
        386,
        387,
        388,
        466,
        263,
        249,
        390,
        373,
        374,
        380,
        381,
        382,
    ]

    NOSE = [1, 2, 98, 327, 168, 195, 5, 4, 275, 440, 305]
    MOUTH_OUTER = [
        61,
        185,
        40,
        39,
        37,
        0,
        267,
        269,
        270,
        409,
        291,
        375,
        321,
        405,
        314,
        17,
        84,
        181,
        91,
        146,
    ]
    MOUTH_INNER = [
        78,
        191,
        80,
        81,
        82,
        13,
        312,
        311,
        310,
        415,
        308,
        324,
        318,
        402,
        317,
        14,
        87,
        178,
        88,
        95,
    ]

    def __init__(self):
        self._face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"
        )

        # MediaPipe FaceMesh
        self._mp_face_mesh = None
        self._face_mesh = None
        self._init_mediapipe()

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
            logger.info("MediaPipe FaceMesh inicializado no GroomingAnalyzer")
        except ImportError:
            logger.warning("MediaPipe nao disponivel. Usando fallback OpenCV.")
            self._face_mesh = None

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analisa grooming em uma imagem facial.

        Args:
            image_bytes: Bytes da imagem

        Returns:
            Dict com analise completa de grooming
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return self._error_result("Nao foi possivel carregar a imagem")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detectar faces
        faces = self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100)
        )

        if len(faces) == 0:
            return self._error_result("Nenhum rosto detectado")

        largest_face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = largest_face

        face_roi = gray[y : y + h, x : x + w]
        face_roi_color = img[y : y + h, x : x + w]

        # Tentar MediaPipe FaceMesh
        landmarks = self._get_mediapipe_landmarks(img)

        # Analises individuais com landmarks precisos
        skin = self._analyze_skin(face_roi_color, face_roi, landmarks, x, y, w, h)
        beard = self._analyze_beard(face_roi_color, face_roi, landmarks, x, y, w, h)
        eyebrows = self._analyze_eyebrows(
            face_roi_color, face_roi, landmarks, x, y, w, h
        )
        hair = self._analyze_hair(img, gray, landmarks, x, y, w, h)
        hygiene = self._analyze_hygiene_overall(skin, beard, eyebrows, hair)

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
            "landmarks_detected": landmarks is not None,
            "landmark_count": len(landmarks) if landmarks else 0,
            "face_position": {
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
            },
            "recommendations": self._generate_recommendations(
                skin, beard, eyebrows, hair, hygiene
            ),
            "grooming_plan": self._generate_grooming_plan(skin, beard, eyebrows, hair),
        }

    # ========== MEDIAPIPE LANDMARKS ==========

    def _get_mediapipe_landmarks(self, img: np.ndarray) -> Optional[list]:
        """Extrai landmarks do MediaPipe FaceMesh (468 pontos)."""
        if self._face_mesh is None:
            return None

        try:
            import mediapipe as mp

            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = self._face_mesh.process(img_rgb)

            if not results.multi_face_landmarks:
                return None

            face_landmarks = results.multi_face_landmarks[0]
            h, w = img.shape[:2]

            landmarks = []
            for lm in face_landmarks.landmark:
                landmarks.append(
                    {
                        "x": lm.x,
                        "y": lm.y,
                        "z": lm.z,
                        "px_x": int(lm.x * w),
                        "px_y": int(lm.y * h),
                    }
                )

            return landmarks

        except Exception as e:
            logger.warning(f"Erro no MediaPipe FaceMesh: {e}")
            return None

    def _get_landmark_region_pixels(
        self, landmarks: list, indices: list, img_shape: tuple
    ) -> list:
        """Extrai coordenadas em pixels de uma regiao de landmarks."""
        h, w = img_shape[:2]
        points = []
        for idx in indices:
            if idx < len(landmarks):
                points.append((landmarks[idx]["px_x"], landmarks[idx]["px_y"]))
        return points

    def _get_region_mask(
        self, img: np.ndarray, landmarks: list, indices: list
    ) -> np.ndarray:
        """Cria mascara binaria para uma regiao de landmarks."""
        h, w = img.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        points = self._get_landmark_region_pixels(landmarks, indices, img.shape)
        if len(points) >= 3:
            pts = np.array(points, dtype=np.int32)
            cv2.fillPoly(mask, [pts], 255)

        return mask

    def _get_region_pixels(self, img: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Extrai pixels da imagem onde a mascara e ativa."""
        return img[mask > 0]

    # ========== SKIN ANALYSIS ==========

    def _analyze_skin(
        self,
        face_color: np.ndarray,
        face_gray: np.ndarray,
        landmarks: Optional[list],
        face_x: int,
        face_y: int,
        face_w: int,
        face_h: int,
    ) -> SkinMetrics:
        """Analisa qualidade da pele usando landmarks para regioes precisas."""
        h, w = face_gray.shape

        # Regioes de pele pura (evitar olhos, sobrancelhas, boca)
        if landmarks:
            # Usar landmarks para definir regioes precisas
            # Testa: entre sobrancelhas e acima dos olhos
            forehead_indices = [
                10,
                8,
                6,
                5,
                4,
                1,
                0,
                37,
                39,
                40,
                185,
                61,
                67,
                103,
                54,
                21,
            ]
            forehead_mask = self._get_region_mask(
                face_color, landmarks, forehead_indices
            )
            forehead_pixels = self._get_region_pixels(face_color, forehead_mask)

            # Bochechas: laterais do nariz
            left_cheek_indices = [
                117,
                118,
                119,
                120,
                121,
                128,
                114,
                47,
                126,
                217,
                174,
                196,
                3,
                51,
                45,
                44,
            ]
            right_cheek_indices = [
                346,
                347,
                348,
                349,
                350,
                357,
                343,
                277,
                356,
                437,
                399,
                419,
                248,
                261,
                265,
                264,
            ]

            left_mask = self._get_region_mask(face_color, landmarks, left_cheek_indices)
            right_mask = self._get_region_mask(
                face_color, landmarks, right_cheek_indices
            )

            left_pixels = self._get_region_pixels(face_color, left_mask)
            right_pixels = self._get_region_pixels(face_color, right_mask)

            # Combinar todas as regioes de pele
            all_skin_pixels = (
                np.vstack(
                    [
                        p
                        for p in [forehead_pixels, left_pixels, right_pixels]
                        if len(p) > 0
                    ]
                )
                if any(len(p) > 0 for p in [forehead_pixels, left_pixels, right_pixels])
                else None
            )
        else:
            all_skin_pixels = None

        # Se nao conseguiu landmarks, usar regioes aproximadas
        if all_skin_pixels is None or len(all_skin_pixels) < 100:
            # Regiao da testa (superior 30%)
            forehead_gray = face_gray[: int(h * 0.3), int(w * 0.2) : int(w * 0.8)]
            # Bochechas (meio lateral)
            left_cheek_gray = face_gray[int(h * 0.3) : int(h * 0.7), : int(w * 0.4)]
            right_cheek_gray = face_gray[int(h * 0.3) : int(h * 0.7), int(w * 0.6) :]

            face_gray_for_analysis = np.concatenate(
                [
                    forehead_gray.flatten(),
                    left_cheek_gray.flatten(),
                    right_cheek_gray.flatten(),
                ]
            )
        else:
            # Converter pixels para grayscale para analise
            face_gray_for_analysis = cv2.cvtColor(
                all_skin_pixels.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_RGB2GRAY
            ).flatten()

            # Usar pixels coloridos para analise de vermelhidao
            face_color_for_analysis = all_skin_pixels

        # Uniformidade
        std_val = np.std(face_gray_for_analysis)
        uniformity = max(0, 1.0 - std_val / 80)

        # Brilho
        mean_val = np.mean(face_gray_for_analysis)
        brightness = mean_val / 255.0
        if 0.4 <= brightness <= 0.7:
            brightness_score = 1.0
        else:
            brightness_score = max(0, 1.0 - abs(brightness - 0.55) * 2)

        # Textura
        if len(face_gray_for_analysis) > 100:
            sample = face_gray_for_analysis[: min(10000, len(face_gray_for_analysis))]
            # Correção defensiva: int(sqrt(len(sample))) só produz um
            # reshape válido quando len(sample) é divisível por esse
            # valor -- praticamente nunca garantido, já que len(sample)
            # depende do tamanho da região de pele detectada por foto.
            # Bug real em produção: len(sample)=1869, sqrt truncada=43,
            # 1869 não é divisível por 43 -> ValueError: cannot reshape
            # array of size 1869 into shape (43,newaxis).
            # Fix: usar exatamente side*side elementos (<= len(sample)
            # por construção, já que side = floor(sqrt(len(sample)))),
            # garantindo que o reshape sempre seja válido. No máximo
            # descarta (side*2)-1 pixels de uma amostra de até 10000 --
            # irrelevante para a variância de textura calculada a seguir.
            side = int(np.sqrt(len(sample)))
            sample_2d = sample[: side * side].reshape(side, side)
            laplacian = cv2.Laplacian(sample_2d.astype(np.uint8), cv2.CV_64F)
            texture_var = laplacian.var()
        else:
            laplacian = cv2.Laplacian(face_gray, cv2.CV_64F)
            texture_var = laplacian.var()

        if 50 <= texture_var <= 300:
            texture_score = 1.0
        else:
            texture_score = max(0, 1.0 - abs(texture_var - 175) / 300)

        # Vermelhidao
        if all_skin_pixels is not None and len(all_skin_pixels) > 0:
            r_mean = np.mean(all_skin_pixels[:, 0])
            g_mean = np.mean(all_skin_pixels[:, 1])
            redness_ratio = r_mean / (g_mean + 0.01)
        else:
            b, g, r = cv2.split(face_color)
            redness = np.mean(r) / 255.0
            greenness = np.mean(g) / 255.0
            redness_ratio = redness / (greenness + 0.01)

        redness_score = max(0, 1.0 - abs(redness_ratio - 1.0) * 2)

        # Poros
        local_var = np.array(
            [
                np.std(face_gray_for_analysis[i : i + 100])
                for i in range(0, max(1, len(face_gray_for_analysis) - 100), 100)
            ]
        )
        pore_visibility = (
            min(1.0, np.mean(local_var) / 30) if len(local_var) > 0 else 0.5
        )
        pore_score = max(0, 1.0 - pore_visibility)

        overall = (
            uniformity * 0.25
            + brightness_score * 0.25
            + texture_score * 0.20
            + redness_score * 0.15
            + pore_score * 0.15
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
        self,
        face_color: np.ndarray,
        face_gray: np.ndarray,
        landmarks: Optional[list],
        face_x: int,
        face_y: int,
        face_w: int,
        face_h: int,
    ) -> BeardMetrics:
        """Analisa barba na regiao inferior do rosto."""
        h, w = face_gray.shape

        if landmarks:
            # Usar landmarks para definir regiao exata da barba
            # Mandibula inferior + queixo
            beard_indices = [
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
            ]
            beard_mask = self._get_region_mask(face_color, landmarks, beard_indices)

            # Limitar a metade inferior
            beard_mask[: h // 2, :] = 0

            beard_pixels_gray = self._get_region_pixels(face_gray, beard_mask)
            beard_pixels_color = self._get_region_pixels(face_color, beard_mask)

            if len(beard_pixels_gray) > 0:
                # Mesma correção defensiva do bloco de textura acima:
                # int(sqrt(n)) nem sempre divide n, o que já quebrou em
                # produção. Usa exatamente side*side pixels.
                beard_side = int(np.sqrt(len(beard_pixels_gray)))
                beard_region = beard_pixels_gray[: beard_side * beard_side].reshape(
                    beard_side, beard_side
                )
                beard_color_region = beard_pixels_color
            else:
                beard_region = face_gray[int(h * 0.55) :, :]
                beard_color_region = face_color[int(h * 0.55) :, :]
        else:
            beard_region = face_gray[int(h * 0.55) :, :]
            beard_color_region = face_color[int(h * 0.55) :, :]

        if beard_region.size == 0:
            return BeardMetrics(0, 0, "none", 0, 0, 0)

        # Detectar cobertura
        # Mesma correção defensiva (ver bloco de textura acima). Este
        # branch (ndim==1) provavelmente não é mais alcançado depois da
        # correção de beard_region acima -- que agora sempre produz um
        # array 2D -- mas mantido correto por segurança/consistência.
        if beard_region.ndim == 1:
            laplacian_side = int(np.sqrt(max(1, beard_region.size)))
            beard_laplacian_input = beard_region[: laplacian_side * laplacian_side].reshape(
                laplacian_side, laplacian_side
            )
            beard_laplacian = cv2.Laplacian(beard_laplacian_input.astype(np.uint8), cv2.CV_64F)
        else:
            beard_laplacian = cv2.Laplacian(beard_region, cv2.CV_64F)

        beard_texture = beard_laplacian.var() if beard_laplacian.size > 0 else 0
        upper_face = face_gray[: int(h * 0.55), :]
        upper_laplacian = cv2.Laplacian(upper_face, cv2.CV_64F)
        upper_texture = upper_laplacian.var()

        texture_ratio = beard_texture / (upper_texture + 1)
        coverage = min(1.0, max(0, (texture_ratio - 0.5) * 0.8))

        # Uniformidade
        beard_std = (
            np.std(beard_region) if beard_region.ndim > 1 else np.std(beard_region)
        )
        uniformity = max(0, 1.0 - beard_std / 60)

        # Comprimento
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

        # Definicao de bordas
        if beard_region.ndim > 1:
            grad_y = cv2.Sobel(beard_region, cv2.CV_64F, 0, 1, ksize=3)
            edge_strength = np.mean(np.abs(grad_y))
        else:
            edge_strength = 0
        edge_definition = min(1.0, edge_strength / 30)

        # Aparência
        neatness = uniformity * 0.6 + edge_definition * 0.4
        overall = (
            coverage * 0.3 + uniformity * 0.25 + neatness * 0.25 + edge_definition * 0.2
        )

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
        self,
        face_color: np.ndarray,
        face_gray: np.ndarray,
        landmarks: Optional[list],
        face_x: int,
        face_y: int,
        face_w: int,
        face_h: int,
    ) -> EyebrowMetrics:
        """Analisa sobrancelhas usando landmarks MediaPipe."""
        h, w = face_gray.shape

        if landmarks:
            # Extrair regioes exatas das sobrancelhas
            left_brow_pts = self._get_landmark_region_pixels(
                landmarks, self.LEFT_EYEBROW, face_color.shape
            )
            right_brow_pts = self._get_landmark_region_pixels(
                landmarks, self.RIGHT_EYEBROW, face_color.shape
            )

            if left_brow_pts and right_brow_pts:
                # Criar mascaras para sobrancelhas
                left_mask = np.zeros(face_gray.shape, dtype=np.uint8)
                right_mask = np.zeros(face_gray.shape, dtype=np.uint8)

                if len(left_brow_pts) >= 3:
                    cv2.fillPoly(
                        left_mask, [np.array(left_brow_pts, dtype=np.int32)], 255
                    )
                if len(right_brow_pts) >= 3:
                    cv2.fillPoly(
                        right_mask, [np.array(right_brow_pts, dtype=np.int32)], 255
                    )

                left_pixels = face_gray[left_mask > 0]
                right_pixels = face_gray[right_mask > 0]

                # Simetria: comparar altura e espessura
                left_y_coords = [p[1] for p in left_brow_pts]
                right_y_coords = [p[1] for p in right_brow_pts]

                left_height = (
                    max(left_y_coords) - min(left_y_coords) if left_y_coords else 0
                )
                right_height = (
                    max(right_y_coords) - min(right_y_coords) if right_y_coords else 0
                )
                symmetry = 1.0 - abs(left_height - right_height) / max(
                    left_height + right_height, 1
                )

                # Espessura: densidade de pixels escuros
                left_darkness = (
                    1.0 - np.mean(left_pixels) / 255.0 if len(left_pixels) > 0 else 0
                )
                right_darkness = (
                    1.0 - np.mean(right_pixels) / 255.0 if len(right_pixels) > 0 else 0
                )
                thickness = min(1.0, (left_darkness + right_darkness) / 2 * 2)

                # Arco: analise de curvatura
                left_x = [p[0] for p in left_brow_pts]
                left_y = [p[1] for p in left_brow_pts]
                right_x = [p[0] for p in right_brow_pts]
                right_y = [p[1] for p in right_brow_pts]

                # Calcular curvatura (segunda derivada aproximada)
                left_curve = self._calculate_curvature(left_x, left_y)
                right_curve = self._calculate_curvature(right_x, right_y)
                arch_strength = min(1.0, (abs(left_curve) + abs(right_curve)) / 2)

                # Definicao: contraste entre sobrancelha e pele ao redor
                left_mean = np.mean(left_pixels) if len(left_pixels) > 0 else 128
                surrounding_left = (
                    face_gray[
                        max(0, min(left_y_coords) - 5) : min(h, max(left_y_coords) + 5),
                        max(0, min(left_x) - 10) : min(w, max(left_x) + 10),
                    ]
                    if left_y_coords and left_x
                    else face_gray
                )
                if surrounding_left.size > 0:
                    surround_mean = np.mean(surrounding_left)
                    definition = min(1.0, abs(left_mean - surround_mean) / 128)
                else:
                    definition = 0.5

                overall = (
                    symmetry * 0.3
                    + thickness * 0.2
                    + arch_strength * 0.2
                    + definition * 0.3
                )

                return EyebrowMetrics(
                    symmetry_score=round(symmetry, 3),
                    thickness_score=round(thickness, 3),
                    arch_score=round(arch_strength, 3),
                    definition_score=round(definition, 3),
                    overall_score=round(overall, 3),
                )

        # Fallback: regiao aproximada
        eyebrow_region = face_gray[int(h * 0.20) : int(h * 0.45), :]
        if eyebrow_region.size == 0:
            return EyebrowMetrics(0.5, 0.5, 0.5, 0.5, 0.5)

        mid = w // 2
        left_half = eyebrow_region[:, :mid]
        right_half = eyebrow_region[:, mid:]

        left_mean = np.mean(left_half)
        right_mean = np.mean(right_half)
        symmetry = max(0, 1.0 - abs(left_mean - right_mean) / 100)

        darkness = 1.0 - np.mean(eyebrow_region) / 255.0
        thickness = min(1.0, darkness * 2)

        grad_y = cv2.Sobel(eyebrow_region, cv2.CV_64F, 0, 1, ksize=3)
        arch_strength = min(1.0, np.mean(np.abs(grad_y)) / 20)

        _, thresh = cv2.threshold(
            eyebrow_region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        definition = np.sum(thresh > 0) / thresh.size

        overall = (
            symmetry * 0.3 + thickness * 0.2 + arch_strength * 0.2 + definition * 0.3
        )

        return EyebrowMetrics(
            symmetry_score=round(symmetry, 3),
            thickness_score=round(thickness, 3),
            arch_score=round(arch_strength, 3),
            definition_score=round(definition, 3),
            overall_score=round(overall, 3),
        )

    def _calculate_curvature(self, x: list, y: list) -> float:
        """Calcula curvatura media de uma serie de pontos."""
        if len(x) < 3 or len(y) < 3:
            return 0.0

        # Normalizar
        x_norm = np.array(x) / max(max(x), 1)
        y_norm = np.array(y) / max(max(y), 1)

        # Segunda derivada aproximada
        curvature = 0
        for i in range(1, len(x_norm) - 1):
            dx1 = x_norm[i] - x_norm[i - 1]
            dx2 = x_norm[i + 1] - x_norm[i]
            dy1 = y_norm[i] - y_norm[i - 1]
            dy2 = y_norm[i + 1] - y_norm[i]

            d2y = dy2 - dy1
            curvature += abs(d2y)

        return curvature / max(len(x_norm) - 2, 1)

    # ========== HAIR ANALYSIS ==========

    def _analyze_hair(
        self,
        img: np.ndarray,
        gray: np.ndarray,
        landmarks: Optional[list],
        face_x: int,
        face_y: int,
        face_w: int,
        face_h: int,
    ) -> HairMetrics:
        """Analisa cabelo na regiao acima do rosto."""
        img_h, img_w = img.shape[:2]

        if landmarks:
            # Usar landmarks para definir regiao do cabelo
            # Topo da cabeca (landmarks superiores)
            hair_top_indices = [
                10,
                8,
                6,
                5,
                4,
                1,
                0,
                37,
                39,
                40,
                185,
                61,
                67,
                103,
                54,
                21,
            ]
            hair_top_pts = self._get_landmark_region_pixels(
                landmarks, hair_top_indices, img.shape
            )

            if hair_top_pts:
                min_y = min(p[1] for p in hair_top_pts)
                max_y = max(p[1] for p in hair_top_pts)
                min_x = min(p[0] for p in hair_top_pts)
                max_x = max(p[0] for p in hair_top_pts)

                # Expandir para regiao do cabelo
                hair_y_start = max(0, min_y - int(face_h * 0.8))
                hair_y_end = min(img_h, max_y + int(face_h * 0.2))
                hair_x_start = max(0, min_x - int(face_w * 0.3))
                hair_x_end = min(img_w, max_x + int(face_w * 0.3))
            else:
                hair_y_start = max(0, face_y - int(face_h * 0.8))
                hair_y_end = face_y + int(face_h * 0.3)
                hair_x_start = max(0, face_x - int(face_w * 0.2))
                hair_x_end = min(img_w, face_x + face_w + int(face_w * 0.2))
        else:
            hair_y_start = max(0, face_y - int(face_h * 0.8))
            hair_y_end = face_y + int(face_h * 0.3)
            hair_x_start = max(0, face_x - int(face_w * 0.2))
            hair_x_end = min(img_w, face_x + face_w + int(face_w * 0.2))

        hair_region = gray[hair_y_start:hair_y_end, hair_x_start:hair_x_end]
        hair_color = img[hair_y_start:hair_y_end, hair_x_start:hair_x_end]

        if hair_region.size == 0:
            return HairMetrics(0, 0, 0, 0, 0, 0)

        darkness = 1.0 - np.mean(hair_region) / 255.0
        coverage = min(1.0, darkness * 1.5)

        hair_edges = cv2.Canny(hair_region, 50, 150)
        edge_density = np.sum(hair_edges > 0) / hair_edges.size
        volume = min(1.0, edge_density * 5)

        hair_laplacian = cv2.Laplacian(hair_region, cv2.CV_64F)
        texture = min(1.0, hair_laplacian.var() / 500)

        if hair_color.size > 0:
            hsv = cv2.cvtColor(hair_color, cv2.COLOR_BGR2HSV)
            v_channel = hsv[:, :, 2]
            shine = min(1.0, np.std(v_channel) / 80)
        else:
            shine = 0.5

        neatness = coverage * 0.3 + volume * 0.2 + texture * 0.2 + shine * 0.3
        overall = (
            coverage * 0.25
            + volume * 0.20
            + texture * 0.20
            + shine * 0.20
            + neatness * 0.15
        )

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
        self,
        skin: SkinMetrics,
        beard: BeardMetrics,
        eyebrows: EyebrowMetrics,
        hair: HairMetrics,
    ) -> Dict[str, Any]:
        scores = [
            skin.overall_score,
            beard.overall_score if beard.coverage_score > 0.1 else 0.8,
            eyebrows.overall_score,
            hair.overall_score,
        ]
        overall = np.mean(scores)

        concerns = []
        if skin.redness_score < 0.5:
            concerns.append("Vermelhidao na pele detectada")
        if skin.pore_visibility > 0.7:
            concerns.append("Poros dilatados visiveis")
        if beard.neatness_score < 0.4 and beard.coverage_score > 0.2:
            concerns.append("Barba desalinhada")
        if eyebrows.symmetry_score < 0.5:
            concerns.append("Sobrancelhas assimetricas")
        if hair.neatness_score < 0.4:
            concerns.append("Cabelo desalinhado")

        return {
            "overall_score": round(overall, 3),
            "level": "high" if overall > 0.75 else "medium" if overall > 0.5 else "low",
            "concerns": concerns if concerns else ["Higiene geral adequada"],
            "positive_aspects": self._positive_aspects(skin, beard, eyebrows, hair),
        }

    def _positive_aspects(
        self,
        skin: SkinMetrics,
        beard: BeardMetrics,
        eyebrows: EyebrowMetrics,
        hair: HairMetrics,
    ) -> List[str]:
        positives = []
        if skin.uniformity_score > 0.7:
            positives.append("Pele uniforme e bem cuidada")
        if skin.brightness_score > 0.7:
            positives.append("Brilho natural saudavel")
        if beard.neatness_score > 0.7 and beard.coverage_score > 0.2:
            positives.append("Barba bem aparada")
        if eyebrows.definition_score > 0.7:
            positives.append("Sobrancelhas bem definidas")
        if hair.shine_score > 0.6:
            positives.append("Cabelo com brilho saudavel")
        if hair.volume_score > 0.6:
            positives.append("Bom volume capilar")
        return positives if positives else ["Aparência geral adequada"]

    # ========== SCORING & LEVELS ==========

    def _calculate_overall_score(
        self,
        skin: SkinMetrics,
        beard: BeardMetrics,
        eyebrows: EyebrowMetrics,
        hair: HairMetrics,
    ) -> float:
        weights = {"skin": 0.35, "beard": 0.20, "eyebrows": 0.20, "hair": 0.25}

        if beard.coverage_score < 0.1:
            weights["beard"] = 0
            weights["skin"] = 0.45
            weights["eyebrows"] = 0.25
            weights["hair"] = 0.30

        score = (
            skin.overall_score * weights["skin"]
            + beard.overall_score * weights["beard"]
            + eyebrows.overall_score * weights["eyebrows"]
            + hair.overall_score * weights["hair"]
        )
        return min(1.0, max(0.0, score))

    def _calculate_confidence(
        self,
        skin: SkinMetrics,
        beard: BeardMetrics,
        eyebrows: EyebrowMetrics,
        hair: HairMetrics,
    ) -> str:
        scores = [
            skin.overall_score,
            beard.overall_score,
            eyebrows.overall_score,
            hair.overall_score,
        ]
        avg = np.mean(scores)
        if avg > 0.6:
            return "high"
        elif avg > 0.35:
            return "medium"
        return "low"

    def _level_from_score(self, score: float) -> str:
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
        self,
        skin: SkinMetrics,
        beard: BeardMetrics,
        eyebrows: EyebrowMetrics,
        hair: HairMetrics,
        hygiene: Dict,
    ) -> List[Dict[str, Any]]:
        recs = []

        if skin.uniformity_score < 0.5:
            recs.append(
                {
                    "category": "skin",
                    "message": "Considerar uso de base ou corretivo para uniformizar o tom da pele",
                    "priority": "high",
                    "products": ["Base leve", "Corretivo", "Po translucido"],
                }
            )

        if skin.brightness_score < 0.4:
            recs.append(
                {
                    "category": "skin",
                    "message": "Pele opaca. Hidratacao e iluminador podem ajudar",
                    "priority": "medium",
                    "products": [
                        "Hidratante facial",
                        "Iluminador liquido",
                        "Vitamina C",
                    ],
                }
            )

        if skin.redness_score < 0.4:
            recs.append(
                {
                    "category": "skin",
                    "message": "Vermelhidao detectada. Usar produtos calmantes",
                    "priority": "medium",
                    "products": [
                        "Creme com niacinamida",
                        "Protetor solar",
                        "Agua termal",
                    ],
                }
            )

        if beard.coverage_score > 0.2 and beard.neatness_score < 0.5:
            recs.append(
                {
                    "category": "beard",
                    "message": f"Barba {beard.length_estimate} precisa de aparo. Definir linhas de bochecha e pescoço",
                    "priority": "high",
                    "products": [
                        "Aparador de barba",
                        "Tesoura de precisao",
                        "Oleo de barba",
                    ],
                    "frequency": "A cada 2-3 dias",
                }
            )
        elif beard.coverage_score > 0.2 and beard.neatness_score > 0.7:
            recs.append(
                {
                    "category": "beard",
                    "message": f"Barba {beard.length_estimate} bem cuidada. Manter rotina atual",
                    "priority": "low",
                    "products": ["Balsamo de barba", "Oleo de barba"],
                    "frequency": "Diaria",
                }
            )

        if eyebrows.symmetry_score < 0.5:
            recs.append(
                {
                    "category": "eyebrows",
                    "message": "Sobrancelhas assimetricas. Considerar design profissional",
                    "priority": "medium",
                    "products": ["Lapis de sobrancelha", "Gel fixador", "Pinca"],
                    "frequency": "A cada 15-20 dias",
                }
            )

        if eyebrows.definition_score < 0.4:
            recs.append(
                {
                    "category": "eyebrows",
                    "message": "Sobrancelhas pouco definidas. Preenchimento sutil recomendado",
                    "priority": "low",
                    "products": [
                        "Sombra para sobrancelhas",
                        "Lapis marrom",
                        "Mascara de sobrancelhas",
                    ],
                }
            )

        if hair.neatness_score < 0.4:
            recs.append(
                {
                    "category": "hair",
                    "message": "Cabelo precisa de corte ou finalizacao. Verificar pontas duplas",
                    "priority": "high",
                    "products": [
                        "Creme de pentear",
                        "Oleo capilar",
                        "Protetor termico",
                    ],
                    "frequency": "Corte a cada 4-6 semanas",
                }
            )

        if hair.shine_score < 0.3:
            recs.append(
                {
                    "category": "hair",
                    "message": "Cabelo sem brilho. Tratamento de hidratacao recomendado",
                    "priority": "medium",
                    "products": ["Mascara de hidratacao", "Oleo de argan", "Leave-in"],
                }
            )

        if not recs:
            recs.append(
                {
                    "category": "general",
                    "message": "Grooming excelente! Manter rotina atual de cuidados",
                    "priority": "low",
                }
            )

        return recs

    def _generate_grooming_plan(
        self,
        skin: SkinMetrics,
        beard: BeardMetrics,
        eyebrows: EyebrowMetrics,
        hair: HairMetrics,
    ) -> List[str]:
        plan = []
        plan.append("Limpeza facial diaria (manha e noite)")
        plan.append("Hidratacao facial apos limpeza")

        if beard.coverage_score > 0.2:
            plan.append("Aplicacao de oleo/balsamo de barba")

        plan.append("Protetor solar facial (manha)")
        plan.append("Exfoliacao facial 1-2x por semana")

        if hair.neatness_score < 0.6:
            plan.append("Hidratacao capilar semanal")

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
            "level": (
                "high"
                if skin.overall_score > 0.7
                else "medium" if skin.overall_score > 0.45 else "low"
            ),
        }

    def _beard_to_dict(self, beard: BeardMetrics) -> Dict:
        return {
            "overall_score": beard.overall_score,
            "coverage": beard.coverage_score,
            "uniformity": beard.uniformity_score,
            "length_estimate": beard.length_estimate,
            "neatness": beard.neatness_score,
            "edge_definition": beard.edge_definition,
            "level": (
                "high"
                if beard.overall_score > 0.7
                else "medium" if beard.overall_score > 0.45 else "low"
            ),
        }

    def _eyebrow_to_dict(self, eyebrows: EyebrowMetrics) -> Dict:
        return {
            "overall_score": eyebrows.overall_score,
            "symmetry": eyebrows.symmetry_score,
            "thickness": eyebrows.thickness_score,
            "arch": eyebrows.arch_score,
            "definition": eyebrows.definition_score,
            "level": (
                "high"
                if eyebrows.overall_score > 0.7
                else "medium" if eyebrows.overall_score > 0.45 else "low"
            ),
        }

    def _hair_to_dict(self, hair: HairMetrics) -> Dict:
        return {
            "overall_score": hair.overall_score,
            "coverage": hair.coverage_score,
            "volume": hair.volume_score,
            "texture": hair.texture_score,
            "shine": hair.shine_score,
            "neatness": hair.neatness_score,
            "level": (
                "high"
                if hair.overall_score > 0.7
                else "medium" if hair.overall_score > 0.45 else "low"
            ),
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
            "landmarks_detected": False,
            "landmark_count": 0,
            "error": message,
            "recommendations": [
                {
                    "category": "technical",
                    "message": message,
                    "priority": "high",
                }
            ],
            "grooming_plan": [],
        }
