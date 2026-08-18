"""
backend/app/ai/visagism/measurement_engine.py

Motor de medicoes faciais deterministico do VisagismAgent.

Extrai 468 landmarks via MediaPipe FaceMesh e computa:
- 12+ medicoes faciais normalizadas
- 7+ proporcoes com classificacao
- Formato facial por regras geometricas
- Simetria por pares de landmarks
- Avaliacao por regiao facial

Nao faz inferencias — apenas mede e reporta.
"""

import math
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID

import numpy as np
from PIL import Image

from app.ai.mediapipe.analyzer import MediaPipeService
from app.ai.visagism.schemas import (
    FacialMeasurement, FacialProportion, FaceShape,
    EvidenceSource, PhotoAngle
)
from app.ai.visagism.evidence_tracker import EvidenceTracker


class VisagismMeasurementEngine:
    """
    Motor de medicoes faciais para visagismo.
    
    Usa MediaPipe FaceMesh para extrair landmarks e computar
    proporcoes geometricas deterministicas.
    """
    
    # Landmarks chave do MediaPipe FaceMesh (indices)
    LANDMARKS = {
        'forehead_top': 10,
        'chin_bottom': 152,
        'left_face': 234,
        'right_face': 454,
        'hairline_center': 10,
        'brow_left_outer': 105,
        'brow_right_outer': 334,
        'brow_left_inner': 103,
        'brow_right_inner': 332,
        'eye_left_outer': 33,
        'eye_left_inner': 133,
        'eye_right_outer': 362,
        'eye_right_inner': 263,
        'eye_left_top': 159,
        'eye_left_bottom': 145,
        'eye_right_top': 386,
        'eye_right_bottom': 374,
        'nose_tip': 1,
        'nose_bridge': 6,
        'nose_left': 129,
        'nose_right': 358,
        'nose_base_left': 98,
        'nose_base_right': 327,
        'cheek_left': 123,
        'cheek_right': 352,
        'zygoma_left': 116,
        'zygoma_right': 345,
        'mouth_left': 61,
        'mouth_right': 291,
        'mouth_top': 13,
        'mouth_bottom': 14,
        'jaw_left': 58,
        'jaw_right': 288,
        'jaw_angle_left': 172,
        'jaw_angle_right': 397,
        'chin_center': 152,
        'chin_left': 148,
        'chin_right': 377,
    }
    
    # Pares para simetria
    SYMMETRY_PAIRS = [
        (33, 263), (133, 362), (159, 386), (145, 374),
        (61, 291), (234, 454), (58, 288), (123, 352),
        (116, 345), (105, 334), (103, 332),
    ]
    
    # Limites para classificacao
    RATIO_OBLONG = 1.50
    RATIO_ROUND_MAX = 1.20
    RATIO_OVAL_MIN = 1.20
    RATIO_OVAL_MAX = 1.40
    JAW_SQUARE = 0.88
    JAW_HEART = 0.75
    JAW_DIAMOND = 0.70
    
    def __init__(self):
        self.mediapipe = MediaPipeService()
        self.tracker: Optional[EvidenceTracker] = None
    
    async def measure_photo(
        self,
        photo_id: UUID,
        image: Image.Image,
        angle: PhotoAngle,
        tracker: EvidenceTracker,
    ) -> Dict[str, Any]:
        """Executa todas as medicoes em uma foto."""
        self.tracker = tracker
        
        mesh_result = await self.mediapipe.analyze_face_mesh(image)
        
        if mesh_result.get("error") or mesh_result.get("landmarks_count", 0) < 468:
            return {
                "success": False,
                "error": mesh_result.get("error", "Landmarks insuficientes"),
                "landmarks_count": mesh_result.get("landmarks_count", 0),
            }
        
        landmarks = mesh_result["landmarks"]
        
        measurements = self._extract_measurements(photo_id, landmarks)
        proportions = self._compute_proportions(photo_id, measurements)
        face_shape = self._classify_face_shape(proportions)
        symmetry_score = self._compute_symmetry(landmarks)
        regions = self._assess_regions(photo_id, landmarks, measurements)
        viz_landmarks = self._prepare_visualization_landmarks(landmarks)
        
        return {
            "success": True,
            "photo_id": str(photo_id),
            "angle": angle.value,
            "measurements": measurements,
            "proportions": proportions,
            "face_shape": face_shape,
            "symmetry_score": symmetry_score,
            "regions": regions,
            "visualization_landmarks": viz_landmarks,
            "landmarks_count": len(landmarks),
        }
    
    def _extract_measurements(self, photo_id: UUID, landmarks: List[Dict]) -> List[FacialMeasurement]:
        """Extrai medicoes basicas dos landmarks."""
        m = self.LANDMARKS
        measurements = []
        
        defs = [
            ("face_width", [m['left_face'], m['right_face']], "largura total do rosto"),
            ("face_height", [m['forehead_top'], m['chin_bottom']], "altura total do rosto"),
            ("jaw_width", [m['jaw_left'], m['jaw_right']], "largura da mandibula"),
            ("brow_width", [m['brow_left_outer'], m['brow_right_outer']], "largura da testa"),
            ("interocular_distance", [m['eye_left_inner'], m['eye_right_inner']], "distancia entre olhos"),
            ("forehead_height", [m['hairline_center'], m['brow_left_outer']], "altura da testa"),
            ("nose_height", [m['nose_bridge'], m['nose_tip']], "altura do nariz"),
            ("nose_width", [m['nose_base_left'], m['nose_base_right']], "largura do nariz"),
            ("mouth_height", [m['mouth_top'], m['mouth_bottom']], "altura da boca"),
            ("mouth_width", [m['mouth_left'], m['mouth_right']], "largura da boca"),
            ("chin_height", [m['mouth_bottom'], m['chin_center']], "altura do queixo"),
            ("chin_width", [m['chin_left'], m['chin_right']], "largura do queixo"),
        ]
        
        for name, idxs, desc in defs:
            if all(i < len(landmarks) for i in idxs):
                val = self._distance(landmarks[idxs[0]], landmarks[idxs[1]])
                measurements.append(self._create_measurement(photo_id, name, val, idxs, desc))
        
        return measurements
    
    def _compute_proportions(self, photo_id: UUID, measurements: List[FacialMeasurement]) -> List[FacialProportion]:
        """Computa proporcoes a partir das medicoes."""
        m = {meas.name: meas for meas in measurements}
        proportions = []
        
        defs = [
            ("height_to_width_ratio", "face_height", "face_width", (1.3, 1.5)),
            ("jaw_to_face_ratio", "jaw_width", "face_width", (0.70, 0.88)),
            ("forehead_to_face_ratio", "brow_width", "face_width", (0.75, 0.90)),
            ("interocular_to_face_ratio", "interocular_distance", "face_width", (0.40, 0.50)),
            ("nose_to_mouth_ratio", "nose_width", "mouth_width", (0.60, 0.75)),
            ("chin_to_jaw_ratio", "chin_width", "jaw_width", (0.55, 0.70)),
        ]
        
        for name, num, den, ideal in defs:
            if num in m and den in m and m[den].value > 0:
                val = m[num].value / m[den].value
                proportions.append(self._create_proportion(photo_id, name, val, [m[num].evidence_id, m[den].evidence_id], ideal, name.replace("_", " ")))
        
        # Tercos faciais
        if all(k in m for k in ['forehead_height', 'nose_height', 'chin_height']):
            total = m['forehead_height'].value + m['nose_height'].value + m['chin_height'].value
            if total > 0:
                for key, label, ideal in [
                    ("upper_third", "terco superior", (0.30, 0.36)),
                    ("middle_third", "terco medio", (0.32, 0.36)),
                    ("lower_third", "terco inferior", (0.32, 0.38)),
                ]:
                    val = m[key.replace('_third', '_height').replace('upper', 'forehead').replace('middle', 'nose').replace('lower', 'chin')].value / total
                    proportions.append(self._create_proportion(photo_id, key, val, [m[key.replace('_third', '_height').replace('upper', 'forehead').replace('middle', 'nose').replace('lower', 'chin')].evidence_id], ideal, label))
        
        return proportions
    
    def _classify_face_shape(self, proportions: List[FacialProportion]) -> FaceShape:
        """Classifica formato facial por regras geometricas."""
        p = {prop.name: prop for prop in proportions}
        
        hw = p.get('height_to_width_ratio')
        jaw = p.get('jaw_to_face_ratio')
        chin = p.get('chin_to_jaw_ratio')
        forehead = p.get('forehead_to_face_ratio')
        
        if not hw:
            return FaceShape.UNKNOWN
        
        h_w, j_f, c_j, f_f = hw.value, (jaw.value if jaw else 0.80), (chin.value if chin else 0.65), (forehead.value if forehead else 0.82)
        
        if h_w >= self.RATIO_OBLONG: return FaceShape.OBLONG
        if h_w <= self.RATIO_ROUND_MAX and j_f >= self.JAW_SQUARE - 0.05: return FaceShape.ROUND
        if f_f >= 0.85 and c_j <= 0.60: return FaceShape.HEART
        if j_f <= self.JAW_DIAMOND and f_f <= 0.78: return FaceShape.DIAMOND
        if j_f >= self.JAW_SQUARE and abs(h_w - 1.0) < 0.15: return FaceShape.SQUARE
        if j_f > f_f + 0.05: return FaceShape.TRIANGULAR
        if self.RATIO_OVAL_MIN <= h_w <= self.RATIO_OVAL_MAX and 0.70 <= j_f <= 0.85: return FaceShape.OVAL
        
        return FaceShape.MIXED
    
    def _compute_symmetry(self, landmarks: List[Dict]) -> float:
        """Computa score de simetria."""
        if len(landmarks) < 468:
            return 0.5
        
        center_x = landmarks[1].get('x', 0.5)
        scores = []
        
        for left_idx, right_idx in self.SYMMETRY_PAIRS:
            if left_idx < len(landmarks) and right_idx < len(landmarks):
                left_dist = abs(landmarks[left_idx]['x'] - center_x)
                right_dist = abs(landmarks[right_idx]['x'] - center_x)
                if left_dist + right_dist > 0:
                    scores.append(1 - abs(left_dist - right_dist) / (left_dist + right_dist))
        
        return round(sum(scores) / len(scores), 3) if scores else 0.5
    
    def _assess_regions(self, photo_id: UUID, landmarks: List[Dict], measurements: List[FacialMeasurement]) -> Dict[str, Any]:
        """Avalia regioes faciais especificas."""
        m = self.LANDMARKS
        regions = {}
        
        regions['forehead'] = {
            'height_relative': self._safe_ratio(measurements, 'forehead_height', 'face_height'),
            'width_relative': self._safe_ratio(measurements, 'brow_width', 'face_width'),
        }
        
        # NOTA: arch_height e calculado em coordenadas normalizadas brutas.
        # Para comparacao entre individuos, requer normalizacao pelo tamanho da face.
        # O valor bruto e mantido para auditoria; o normalizado e placeholder.
        arch_raw = abs(landmarks[105]['y'] - landmarks[52]['y']) if len(landmarks) > 105 else 0
        face_h = self._safe_ratio(measurements, 'face_height', None) or 1.0
        arch_normalized = arch_raw / face_h if face_h > 0 else 0
        
        regions['eyebrows'] = {
            'arch_height_raw': arch_raw,
            'arch_height_normalized': round(arch_normalized, 4),
            'arch_height_status': 'PLACEHOLDER: requer validacao com dataset de referencia',
            'separation': self._distance(landmarks[m['brow_left_inner']], landmarks[m['brow_right_inner']]),
        }
        
        regions['eyes'] = {
            'size_relative': self._safe_ratio(measurements, 'interocular_distance', 'face_width'),
            'shape': self._assess_eye_shape(landmarks),
        }
        
        regions['nose'] = {
            'length_relative': self._safe_ratio(measurements, 'nose_height', 'face_height'),
            'width_relative': self._safe_ratio(measurements, 'nose_width', 'face_width'),
        }
        
        # NOTA: prominencia do zigoma requer analise de profundidade 3D
        # que nao esta disponivel em landmarks 2D. Marcado como PLACEHOLDER.
        regions['cheekbones'] = {
            'prominence': 'PLACEHOLDER: requer analise 3D ou perfil lateral',
        }
        
        regions['mouth'] = {
            'width_relative': self._safe_ratio(measurements, 'mouth_width', 'face_width'),
            'fullness': self._assess_lip_fullness(landmarks),
        }
        
        regions['jaw'] = {
            'width_relative': self._safe_ratio(measurements, 'jaw_width', 'face_width'),
        }
        
        # NOTA: projecao e formato do queixo requerem analise de perfil
        # para determinar proeminencia. Marcado como PLACEHOLDER.
        regions['chin'] = {
            'projection': 'PLACEHOLDER: requer foto de perfil para medicao de proeminencia',
            'shape': 'PLACEHOLDER: requer analise de curvatura do landmark 152',
        }
        
        return regions
    
    def _distance(self, p1: Dict, p2: Dict) -> float:
        return math.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2)
    
    def _create_measurement(self, photo_id: UUID, name: str, value: float, landmarks_used: List[int], description: str) -> FacialMeasurement:
        evidence_id = self.tracker.register(
            category="measurement", description=description, value=round(value, 4),
            source="mediapipe_landmark", confidence=0.90,
            photo_id=str(photo_id), raw_data={"landmarks_used": landmarks_used, "value": value},
        )
        return FacialMeasurement(
            evidence_id=evidence_id, name=name, value=round(value, 4),
            source=EvidenceSource.MEDIAPIPE_LANDMARK, confidence=0.90,
            landmarks_used=landmarks_used, photo_id=photo_id,
        )
    
    def _create_proportion(self, photo_id: UUID, name: str, value: float, evidence_ids: List[str], ideal: Tuple[float, float], description: str) -> FacialProportion:
        classification = "within_ideal" if ideal[0] <= value <= ideal[1] else "below_ideal" if value < ideal[0] else "above_ideal"
        evidence_id = self.tracker.register(
            category="proportion", description=f"{description}: {value:.3f}", value=round(value, 4),
            source="computed_ratio", confidence=0.85, photo_id=str(photo_id),
            raw_data={"ideal_range": ideal, "classification": classification}, derived_from=evidence_ids,
        )
        return FacialProportion(
            evidence_id=evidence_id, name=name, value=round(value, 4),
            ideal_range=ideal, classification=classification,
            source=EvidenceSource.COMPUTED_RATIO, confidence=0.85, evidence=evidence_ids,
        )
    
    def _safe_ratio(self, measurements: List[FacialMeasurement], num_name: Optional[str], den_name: str) -> Optional[float]:
        m = {meas.name: meas for meas in measurements}
        if num_name and num_name in m and den_name in m and m[den_name].value > 0:
            return round(m[num_name].value / m[den_name].value, 3)
        return None
    
    def _assess_eye_shape(self, landmarks: List[Dict]) -> str:
        if len(landmarks) > 374:
            A = abs(landmarks[159]['y'] - landmarks[145]['y'])
            B = abs(landmarks[158]['y'] - landmarks[153]['y'])
            C = abs(landmarks[33]['x'] - landmarks[133]['x'])
            ear = (A + B) / (2.0 * C) if C > 0 else 0
            return "open" if ear > 0.30 else "average" if ear > 0.25 else "narrow"
        return "unknown"
    
    def _assess_lip_fullness(self, landmarks: List[Dict]) -> str:
        if len(landmarks) > 17:
            upper = abs(landmarks[0]['y'] - landmarks[13]['y'])
            lower = abs(landmarks[14]['y'] - landmarks[17]['y'])
            ratio = upper / lower if lower > 0 else 1
            return "full_upper" if ratio > 1.2 else "full_lower" if ratio < 0.8 else "balanced"
        return "unknown"
    
    def _prepare_visualization_landmarks(self, landmarks: List[Dict]) -> List[Dict]:
        return [{"index": i, "x": lm["x"], "y": lm["y"], "z": lm.get("z", 0)} for i, lm in enumerate(landmarks[:468])]
