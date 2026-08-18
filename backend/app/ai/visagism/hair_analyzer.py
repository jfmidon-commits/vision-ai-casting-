"""
backend/app/ai/visagism/hair_analyzer.py

Analisador de cabelo para visagismo.

Combina analise de landmarks (implantacao capilar) com
interpretacao para textura, densidade e volume.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID

from PIL import Image

from app.ai.visagism.schemas import (
    HairAssessment, HairTexture, HairThickness, VolumeLevel,
    ConfidenceLevel, EvidenceSource, PhotoAngle
)
from app.ai.visagism.evidence_tracker import EvidenceTracker


class HairAnalyzer:
    """Analisador de cabelo para visagismo capilar."""
    
    HAIRLINE_LANDMARKS = [10, 8, 6, 5, 4, 1, 0, 17, 18, 19, 20, 21, 22]
    
    async def analyze(
        self,
        photo_id: UUID,
        image: Image.Image,
        angle: PhotoAngle,
        landmarks: List[Dict[str, Any]],
        tracker: EvidenceTracker,
    ) -> HairAssessment:
        """Analisa o cabelo em uma foto."""
        
        hairline = self._analyze_hairline(landmarks, angle)
        texture = self._estimate_texture(image, landmarks)
        volume = self._estimate_volume(landmarks, angle)
        density = self._estimate_density(image, landmarks)
        
        evidence_ids = []
        
        if hairline.get('shape'):
            eid = tracker.register(
                category="observation",
                description=f"Implantacao capilar: {hairline['shape']}",
                value=hairline,
                source="mediapipe_landmark",
                confidence=0.75,
                photo_id=str(photo_id),
            )
            evidence_ids.append(eid)
        
        if texture and texture != HairTexture.UNKNOWN:
            eid = tracker.register(
                category="observation",
                description=f"Textura do cabelo: {texture.value}",
                value=texture.value,
                source="inferred",
                confidence=0.50,
                photo_id=str(photo_id),
            )
            evidence_ids.append(eid)
        
        return HairAssessment(
            hairline_shape=hairline.get('shape'),
            hairline_height=hairline.get('height'),
            forehead_exposure=hairline.get('forehead_exposure'),
            apparent_density=density,
            texture=texture,
            # PLACEHOLDER: espessura do fio requer analise de textura de imagem
            # (modelo de classificacao de frequencia ou CNN treinada).
            # Atualmente nao implementado — retorna UNKNOWN com confidence 0.
            thickness=HairThickness.UNKNOWN,
            volume=volume.get('overall', VolumeLevel.UNKNOWN),
            crown_volume=volume.get('crown'),
            side_volume=volume.get('sides'),
            nape_volume=volume.get('nape'),
            occipital_volume=volume.get('occipital'),
            posterior_assessment=volume.get('posterior') if angle == PhotoAngle.POSTERIOR else None,
            overall_distribution=volume.get('description'),
            source=EvidenceSource.MEDIAPIPE_LANDMARK if hairline else EvidenceSource.INFERRED,
            confidence=0.70 if hairline else 0.40,
            evidence_ids=evidence_ids,
        )
    
    def _analyze_hairline(self, landmarks: List[Dict], angle: PhotoAngle) -> Dict[str, Any]:
        """Analisa a linha do cabelo/implantacao capilar."""
        if angle not in [PhotoAngle.FRONT_NEUTRAL, PhotoAngle.FRONT_SMILING, PhotoAngle.HAIRLINE]:
            return {}
        
        if len(landmarks) < 200:
            return {}
        
        top_points = [landmarks[i] for i in self.HAIRLINE_LANDMARKS if i < len(landmarks)]
        if not top_points:
            return {}
        
        xs = [p['x'] for p in top_points]
        ys = [p['y'] for p in top_points]
        center_y = ys[len(ys)//2]
        side_y = (ys[0] + ys[-1]) / 2
        
        shape = "straight"
        if center_y < side_y - 0.03:
            shape = "m_shaped"
        elif center_y > side_y + 0.03:
            shape = "rounded"
        
        face_height = abs(landmarks[10]['y'] - landmarks[152]['y']) if len(landmarks) > 152 else 1
        hairline_height = center_y - landmarks[10]['y'] if len(landmarks) > 10 else 0
        relative_height = hairline_height / face_height if face_height > 0 else 0.5
        
        height = "medium"
        if relative_height < 0.15:
            height = "low"
        elif relative_height > 0.25:
            height = "high"
        
        return {
            'shape': shape,
            'height': height,
            'forehead_exposure': round(min(1.0, relative_height * 3), 2),
            'relative_position': round(relative_height, 3),
        }
    
    def _estimate_texture(self, image: Image.Image, landmarks: List[Dict]) -> Optional[HairTexture]:
        """Estima textura do cabelo. Placeholder para modelo futuro."""
        return HairTexture.UNKNOWN
    
    def _estimate_volume(self, landmarks: List[Dict], angle: PhotoAngle) -> Dict[str, Any]:
        """Estima distribuicao de volume do cabelo."""
        volume = {
            'overall': VolumeLevel.UNKNOWN,
            'crown': VolumeLevel.UNKNOWN,
            'sides': VolumeLevel.UNKNOWN,
            'nape': VolumeLevel.UNKNOWN,
            'occipital': VolumeLevel.UNKNOWN,
            'description': "Volume nao avaliavel neste angulo",
        }
        
        if angle == PhotoAngle.POSTERIOR:
            # PLACEHOLDER: volume occipital nao pode ser medido sem modelo 3D
            # ou analise de densidade de pixels. Valor estimado heuristicamente.
            volume['occipital'] = VolumeLevel.MODERATE  # PLACEHOLDER: estimativa heuristica
            volume['posterior'] = "Volume occipital: estimativa heuristica (PLACEHOLDER)"
            volume['description'] = "Volume posterior: estimativa heuristica (PLACEHOLDER)"
        elif angle in [PhotoAngle.FRONT_NEUTRAL, PhotoAngle.FRONT_SMILING]:
            # PLACEHOLDER: volume frontal estimado pela altura do landmark 10
            # em relacao ao cranio. Nao e medicao direta.
            volume['crown'] = VolumeLevel.MODERATE  # PLACEHOLDER: estimativa heuristica
            volume['sides'] = VolumeLevel.MODERATE  # PLACEHOLDER: estimativa heuristica
            volume['description'] = "Volume frontal: estimativa heuristica (PLACEHOLDER)"
        
        return volume
    
    def _estimate_density(self, image: Image.Image, landmarks: List[Dict]) -> ConfidenceLevel:
        """Estima densidade aparente do cabelo. Placeholder."""
        return ConfidenceLevel.INSUFFICIENT_DATA
