"""
backend/app/ai/visagism/schemas.py

Schemas Pydantic do VisagismAgent Real (v1.0.0).

Este modulo define os contratos de entrada e saida do motor de analise
de visagismo. O JSON estruturado e a fonte canonica; o relatorio humano
e os dados de visualizacao sao derivados deste JSON.

Principio fundamental: cada conclusao deve ser rastreavel ate evidencias.
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from uuid import UUID
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class PhotoAngle(str, Enum):
    """Angulos do protocolo multifoto de visagismo."""
    FRONT_NEUTRAL = "front_neutral"
    THREE_QUARTER_RIGHT = "three_quarter_right"
    THREE_QUARTER_LEFT = "three_quarter_left"
    PROFILE_RIGHT = "profile_right"
    PROFILE_LEFT = "profile_left"
    FRONT_SMILING = "front_smiling"
    HAIRLINE = "hairline"
    POSTERIOR = "posterior"
    HALF_BODY = "half_body"
    VIDEO_SHORT = "video_short"


class EvidenceSource(str, Enum):
    """Fonte de uma evidencia observada."""
    MEDIAPIPE_LANDMARK = "mediapipe_landmark"
    MEDIAPIPE_MESH = "mediapipe_mesh"
    DEEPFACE_ANALYSIS = "deepface_analysis"
    REKOGNITION = "rekognition"
    LLM_VISION = "llm_vision"
    COMPUTED_RATIO = "computed_ratio"
    HUMAN_VERIFIED = "human_verified"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    """Nivel de confianca qualitativo."""
    CERTAIN = "certain"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNCERTAIN = "uncertain"
    INSUFFICIENT_DATA = "insufficient_data"


class FaceShape(str, Enum):
    """Formatos faciais classificados pelo motor de regras."""
    OVAL = "oval"
    ROUND = "round"
    SQUARE = "square"
    HEART = "heart"
    DIAMOND = "diamond"
    OBLONG = "oblong"
    TRIANGULAR = "triangular"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ChangeLevel(str, Enum):
    """Nivel de mudanca em relacao ao visual atual."""
    SUBTLE = "subtle"
    MODERATE = "moderate"
    DRAMATIC = "dramatic"


class MaintenanceDifficulty(str, Enum):
    """Dificuldade de manutencao de um corte."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class HairTexture(str, Enum):
    """Textura do cabelo observada."""
    STRAIGHT = "straight"
    WAVY = "wavy"
    CURLY = "curly"
    COILY = "coily"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class HairThickness(str, Enum):
    """Espessura do fio de cabelo."""
    FINE = "fine"
    MEDIUM = "medium"
    COARSE = "coarse"
    UNKNOWN = "unknown"


class VolumeLevel(str, Enum):
    """Nivel de volume."""
    FLAT = "flat"
    MODERATE = "moderate"
    VOLUMINOUS = "voluminous"
    UNKNOWN = "unknown"


class NeckLength(str, Enum):
    """Comprimento do pescoco."""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    UNKNOWN = "unknown"


class ShoulderWidth(str, Enum):
    """Largura dos ombros relativa."""
    NARROW = "narrow"
    MEDIUM = "medium"
    BROAD = "broad"
    UNKNOWN = "unknown"


class SideTreatment(str, Enum):
    """Tratamento das laterais do cabelo."""
    TAPERED = "tapered"
    FADED = "faded"
    LAYERED = "layered"
    BULK_REMOVED = "bulk_removed"
    KEPT_LENGTH = "kept_length"


class ForeheadExposure(str, Enum):
    """Recomendacao de exposicao da testa."""
    FULL = "full"
    PARTIAL = "partial"
    MINIMAL = "minimal"


# =============================================================================
# SCHEMAS DE ENTRADA
# =============================================================================

class PhotoInput(BaseModel):
    """Foto individual do protocolo multifoto."""
    model_config = ConfigDict(use_enum_values=True)
    
    photo_id: UUID
    url: str
    angle: PhotoAngle
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    is_usable: bool = True
    unusable_reason: Optional[str] = None


class ProfileContext(BaseModel):
    """Contexto do perfil para enriquecer a analise."""
    model_config = ConfigDict(use_enum_values=True)
    
    profile_id: UUID
    gender: Optional[str] = None
    age_estimate: Optional[int] = Field(None, ge=0, le=120)
    current_hair_length: Optional[str] = None
    current_hair_color: Optional[str] = None
    current_hair_texture: Optional[str] = None
    facial_hair: Optional[str] = None
    style_preferences: List[Dict[str, Any]] = []
    previous_visagism_analyses: List[Dict[str, Any]] = []
    approved_appearances: List[Dict[str, Any]] = []


class VisagismAnalysisInput(BaseModel):
    """Entrada completa para o VisagismAgent."""
    model_config = ConfigDict(use_enum_values=True)
    
    photos: List[PhotoInput] = Field(..., min_length=1)
    profile: ProfileContext
    analysis_types: List[str] = ["hair"]
    include_report: bool = True
    include_visualization_data: bool = True
    correlation_id: Optional[str] = None


# =============================================================================
# SCHEMAS DE EVIDENCIA (OBSERVADO / MEDIDO)
# =============================================================================

class PhotoQualityAssessment(BaseModel):
    """Avaliacao de qualidade de uma foto do protocolo."""
    model_config = ConfigDict(use_enum_values=True)
    
    photo_id: UUID
    angle: PhotoAngle
    is_usable: bool
    unusable_reason: Optional[str] = None
    face_detected: bool
    face_count: int = Field(0, ge=0)
    face_occluded: bool = False
    lighting_quality: ConfidenceLevel
    focus_quality: ConfidenceLevel
    angle_accuracy: ConfidenceLevel
    confidence: float = Field(..., ge=0, le=1)


class FacialMeasurement(BaseModel):
    """Medicao facial individual com rastreabilidade."""
    model_config = ConfigDict(use_enum_values=True)
    
    evidence_id: str = Field(..., description="ID unico desta evidencia")
    name: str
    value: float
    unit: str = "normalized"
    source: EvidenceSource
    confidence: float = Field(..., ge=0, le=1)
    landmarks_used: List[int] = Field(default_factory=list)
    photo_id: Optional[UUID] = None
    raw_landmark_data: Optional[Dict[str, Any]] = None


class FacialProportion(BaseModel):
    """Proporcao facial computada a partir de medicoes."""
    model_config = ConfigDict(use_enum_values=True)
    
    evidence_id: str
    name: str
    value: float
    ideal_range: Optional[Tuple[float, float]] = None
    classification: str
    source: EvidenceSource
    confidence: float = Field(..., ge=0, le=1)
    evidence: List[str] = Field(default_factory=list)


# =============================================================================
# SCHEMAS DE REGIAO FACIAL
# =============================================================================

class FacialRegionAssessment(BaseModel):
    """Avaliacao de uma regiao facial especifica."""
    model_config = ConfigDict(use_enum_values=True)
    
    region_name: str
    observations: List[str] = Field(default_factory=list)
    measurements: List[FacialMeasurement] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)
    source: EvidenceSource
    evidence_ids: List[str] = Field(default_factory=list)


# =============================================================================
# SCHEMAS DE CABELO
# =============================================================================

class HairAssessment(BaseModel):
    """Avaliacao completa do cabelo."""
    model_config = ConfigDict(use_enum_values=True)
    
    hairline_shape: Optional[str] = None
    hairline_height: Optional[str] = None
    forehead_exposure: Optional[float] = Field(None, ge=0, le=1)
    apparent_density: Optional[ConfidenceLevel] = None
    texture: Optional[HairTexture] = None
    thickness: Optional[HairThickness] = None
    volume: Optional[VolumeLevel] = None
    crown_volume: Optional[VolumeLevel] = None
    side_volume: Optional[VolumeLevel] = None
    nape_volume: Optional[VolumeLevel] = None
    occipital_volume: Optional[VolumeLevel] = None
    posterior_assessment: Optional[str] = None
    overall_distribution: Optional[str] = None
    source: EvidenceSource
    confidence: float = Field(..., ge=0, le=1)
    evidence_ids: List[str] = Field(default_factory=list)


# =============================================================================
# SCHEMAS DE RELACAO E ASSIMETRIA
# =============================================================================

class HeadNeckShoulderRelation(BaseModel):
    """Relacao cabeca/pescoco/ombros."""
    model_config = ConfigDict(use_enum_values=True)
    
    photo_id: Optional[UUID] = None
    neck_length: Optional[NeckLength] = None
    shoulder_width_relative: Optional[ShoulderWidth] = None
    head_to_body_ratio: Optional[float] = Field(None, ge=0, le=1)
    posture_observation: Optional[str] = None
    confidence: float = Field(..., ge=0, le=1)
    source: EvidenceSource
    evidence_ids: List[str] = Field(default_factory=list)


class AsymmetryAssessment(BaseModel):
    """Avaliacao de assimetrias faciais."""
    model_config = ConfigDict(use_enum_values=True)
    
    is_detectable: bool
    description: Optional[str] = None
    affected_regions: List[str] = Field(default_factory=list)
    severity: Optional[str] = None
    visual_impact: Optional[str] = None
    compensatory_design: Optional[str] = None
    confidence: float = Field(..., ge=0, le=1)
    source: EvidenceSource
    evidence_ids: List[str] = Field(default_factory=list)


class ExpressionComparison(BaseModel):
    """Comparacao entre expressao neutra e sorriso."""
    model_config = ConfigDict(use_enum_values=True)
    
    has_comparison: bool
    neutral_photo_id: Optional[UUID] = None
    smiling_photo_id: Optional[UUID] = None
    changes_observed: List[str] = Field(default_factory=list)
    recommendations_impact: Optional[str] = None
    confidence: float = Field(..., ge=0, le=1)
    evidence_ids: List[str] = Field(default_factory=list)


# =============================================================================
# SCHEMAS DE RECOMENDACAO
# =============================================================================

class HaircutRecommendation(BaseModel):
    """Recomendacao de corte de cabelo individual."""
    model_config = ConfigDict(use_enum_values=True)
    
    rank: int = Field(..., ge=1, le=5)
    name: str
    category: str
    justification: str
    recommended_length_top: Optional[str] = None
    recommended_length_sides: Optional[str] = None
    recommended_length_nape: Optional[str] = None
    recommended_length_occipital: Optional[str] = None
    volume_distribution: str
    texture_work: Optional[str] = None
    forehead_exposure_recommendation: ForeheadExposure
    side_treatment: SideTreatment
    nape_treatment: Optional[str] = None
    advantages: List[str] = Field(default_factory=list)
    disadvantages: List[str] = Field(default_factory=list)
    change_level: ChangeLevel
    maintenance_difficulty: MaintenanceDifficulty
    maintenance_frequency: Optional[str] = None
    technical_instructions: str
    styling_requirements: str
    styling_products: List[str] = Field(default_factory=list)
    styling_time_estimate: Optional[str] = None
    confidence: float = Field(..., ge=0, le=1)
    confidence_explanation: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)


class DiscouragedCut(BaseModel):
    """Corte ou desenho desaconselhado."""
    model_config = ConfigDict(use_enum_values=True)
    
    name: str
    reason: str
    alternative: Optional[str] = None
    confidence: float = Field(..., ge=0, le=1)
    evidence_ids: List[str] = Field(default_factory=list)


# =============================================================================
# SCHEMA DE SAIDA COMPLETO (JSON CANONICO)
# =============================================================================

class VisagismAnalysisResult(BaseModel):
    """
    Resultado completo da analise de visagismo — JSON canonico.
    """
    model_config = ConfigDict(use_enum_values=True)
    
    version: str = "1.0.0"
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    photos_analyzed: int = Field(0, ge=0)
    photos_usable: int = Field(0, ge=0)
    photos_rejected: int = Field(0, ge=0)
    
    photo_assessments: List[PhotoQualityAssessment] = Field(default_factory=list)
    facial_measurements: List[FacialMeasurement] = Field(default_factory=list)
    facial_proportions: List[FacialProportion] = Field(default_factory=list)
    
    face_shape_category: FaceShape = FaceShape.UNKNOWN
    face_shape_evidence: List[str] = Field(default_factory=list)
    face_shape_confidence: float = Field(0.0, ge=0, le=1)
    
    forehead: Optional[FacialRegionAssessment] = None
    eyebrows: Optional[FacialRegionAssessment] = None
    eyes: Optional[FacialRegionAssessment] = None
    nose: Optional[FacialRegionAssessment] = None
    cheekbones: Optional[FacialRegionAssessment] = None
    mouth: Optional[FacialRegionAssessment] = None
    jaw: Optional[FacialRegionAssessment] = None
    chin: Optional[FacialRegionAssessment] = None
    neck: Optional[FacialRegionAssessment] = None
    
    hair: Optional[HairAssessment] = None
    head_neck_shoulder: Optional[HeadNeckShoulderRelation] = None
    asymmetries: Optional[AsymmetryAssessment] = None
    expression_comparison: Optional[ExpressionComparison] = None
    
    visual_strengths: List[str] = Field(default_factory=list)
    modifiable_aspects: List[str] = Field(default_factory=list)
    preserve_aspects: List[str] = Field(default_factory=list)
    
    primary_recommendation: Optional[HaircutRecommendation] = None
    alternative_recommendations: List[HaircutRecommendation] = Field(default_factory=list)
    discouraged_cuts: List[DiscouragedCut] = Field(default_factory=list)
    
    general_maintenance_schedule: Optional[str] = None
    analysis_limitations: List[str] = Field(default_factory=list)
    
    overall_confidence: float = Field(0.0, ge=0, le=1)
    overall_confidence_explanation: str = ""
    
    evidence_map: Dict[str, List[str]] = Field(default_factory=dict)
    visualization_data: Optional[Dict[str, Any]] = None
    human_report: Optional[str] = None


# =============================================================================
# SCHEMAS INTERMEDIARIOS (USADOS INTERNAMENTE PELO PIPELINE)
# =============================================================================

class PipelineStageResult(BaseModel):
    """Resultado de uma fase do pipeline."""
    model_config = ConfigDict(use_enum_values=True)
    
    stage_name: str
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    processing_time_ms: int = 0


class PipelineContext(BaseModel):
    """Contexto compartilhado entre as fases do pipeline."""
    model_config = ConfigDict(use_enum_values=True)
    
    input_data: VisagismAnalysisInput
    stage_results: Dict[str, PipelineStageResult] = Field(default_factory=dict)
    evidence_tracker: Dict[str, Any] = Field(default_factory=dict)
    current_confidence: float = 1.0
    warnings: List[str] = Field(default_factory=list)


# =============================================================================
# SCHEMA LEGACY (COMPATIBILIDADE)
# =============================================================================

class LegacyVisagismAnalysis(BaseModel):
    """Schema legacy para compatibilidade com consumidores existentes."""
    model_config = ConfigDict(use_enum_values=True)
    
    face_shape_category: str = ""
    face_shape_description: str = ""
    recommended_hairstyles: List[str] = Field(default_factory=list)
    recommended_eyebrow_shapes: List[str] = Field(default_factory=list)
    recommended_makeup_styles: List[str] = Field(default_factory=list)
    contouring_tips: List[str] = Field(default_factory=list)
    highlighting_tips: List[str] = Field(default_factory=list)
    color_recommendations: Dict[str, Any] = Field(default_factory=dict)
    overall_recommendation: str = ""
    confidence: float = Field(0.5, ge=0, le=1)
