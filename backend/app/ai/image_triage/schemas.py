"""
backend/app/ai/image_triage/schemas.py

Schemas Pydantic do modulo de triagem de imagens.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime


class FaceAngle(str, Enum):
    """Angulos faciais relevantes para o protocolo de visagismo."""
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
    NO_FACE = "no_face"


class QualityDimension(str, Enum):
    """Dimensões de qualidade avaliadas."""
    SHARPNESS = "sharpness"
    RESOLUTION = "resolution"
    ILLUMINATION = "illumination"
    OCCLUSION = "occlusion"
    FRAMING = "framing"
    CONTRAST = "contrast"
    NOISE = "noise"
    EYE_VISIBILITY = "eye_visibility"


class QualityScore(BaseModel):
    """Score de qualidade em uma dimensão específica."""
    dimension: QualityDimension
    score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    details: Optional[str] = None
    is_critical: bool = False


class ImageCandidate(BaseModel):
    """Uma imagem candidata após análise."""
    source_path: str
    filename: str
    face_angle: FaceAngle
    face_count: int = 0
    face_confidence: float = 0.0
    quality_scores: List[QualityScore] = Field(default_factory=list)
    overall_quality: float = Field(0.0, ge=0.0, le=1.0)
    width: int = 0
    height: int = 0
    is_usable: bool = False
    rejection_reasons: List[str] = Field(default_factory=list)
    rank_in_category: int = 0
    file_size_bytes: int = 0
    created_at: Optional[datetime] = None

    def get_score(self, dimension: QualityDimension) -> Optional[float]:
        """Retorna score de uma dimensão específica."""
        for qs in self.quality_scores:
            if qs.dimension == dimension:
                return qs.score
        return None


class TriageConfig(BaseModel):
    """Configuração da triagem."""
    min_width: int = 400
    min_height: int = 400
    min_face_confidence: float = 0.6
    min_overall_quality: float = 0.4
    max_per_angle: int = 2
    max_total: int = 15
    critical_dimensions: List[QualityDimension] = [
        QualityDimension.RESOLUTION,
        QualityDimension.FRAMING,
    ]
    quality_weights: Dict[str, float] = {
        "sharpness": 0.20,
        "resolution": 0.15,
        "illumination": 0.15,
        "occlusion": 0.15,
        "framing": 0.15,
        "contrast": 0.10,
        "noise": 0.05,
        "eye_visibility": 0.05,
    }
    output_dir: Optional[str] = None
    copy_selected: bool = True
    generate_report: bool = True
    max_workers: int = 4
    supported_formats: List[str] = [".jpg", ".jpeg", ".png", ".webp", ".bmp"]


class TriageInput(BaseModel):
    """Entrada para triagem."""
    source_dir: str
    config: TriageConfig = Field(default_factory=TriageConfig)
    profile_id: Optional[str] = None


class TriageResult(BaseModel):
    """Resultado da triagem."""
    total_images_found: int = 0
    total_images_analyzed: int = 0
    total_faces_detected: int = 0
    selected_count: int = 0
    rejected_count: int = 0
    selected: List[ImageCandidate] = Field(default_factory=list)
    rejected: List[ImageCandidate] = Field(default_factory=list)
    by_angle: Dict[str, List[ImageCandidate]] = Field(default_factory=dict)
    config: TriageConfig
    processing_time_seconds: float = 0.0
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    output_dir: Optional[str] = None
    report_path: Optional[str] = None

    def get_best_for_angle(self, angle: FaceAngle) -> Optional[ImageCandidate]:
        """Retorna a melhor imagem para um ângulo específico."""
        candidates = self.by_angle.get(angle.value, [])
        return candidates[0] if candidates else None

    def get_protocol_coverage(self) -> Dict[str, bool]:
        """Verifica quais ângulos do protocolo estão cobertos."""
        protocol_angles = [
            FaceAngle.FRONTAL,
            FaceAngle.THREE_QUARTER_LEFT,
            FaceAngle.THREE_QUARTER_RIGHT,
            FaceAngle.PROFILE_LEFT,
            FaceAngle.PROFILE_RIGHT,
            FaceAngle.SMILING,
            FaceAngle.HAIRLINE,
            FaceAngle.POSTERIOR,
            FaceAngle.HALF_BODY,
        ]
        return {
            angle.value: angle.value in self.by_angle and len(self.by_angle[angle.value]) > 0
            for angle in protocol_angles
        }

    def get_protocol_coverage_score(self) -> float:
        """Score de cobertura do protocolo (0-1)."""
        coverage = self.get_protocol_coverage()
        return sum(coverage.values()) / len(coverage)
