"""
backend/app/ai/visagism/__init__.py

Modulo de visagismo do Vision AI Casting.

Exporta o pipeline principal e schemas para uso externo.
"""

from app.ai.visagism.schemas import (
    VisagismAnalysisInput,
    VisagismAnalysisResult,
    PhotoInput,
    ProfileContext,
    PhotoQualityAssessment,
    FacialMeasurement,
    FacialProportion,
    FacialRegionAssessment,
    HairAssessment,
    HeadNeckShoulderRelation,
    AsymmetryAssessment,
    ExpressionComparison,
    HaircutRecommendation,
    DiscouragedCut,
    PhotoAngle,
    FaceShape,
    ConfidenceLevel,
    EvidenceSource,
    ChangeLevel,
    MaintenanceDifficulty,
    HairTexture,
    HairThickness,
    VolumeLevel,
    NeckLength,
    ShoulderWidth,
    SideTreatment,
    ForeheadExposure,
    LegacyVisagismAnalysis,
)

from app.ai.visagism.pipeline import VisagismPipeline
from app.ai.visagism.evidence_tracker import EvidenceTracker, Evidence
from app.ai.visagism.confidence_scorer import ConfidenceScorer, ConfidenceBreakdown
from app.ai.visagism.measurement_engine import VisagismMeasurementEngine
from app.ai.visagism.hair_analyzer import HairAnalyzer
from app.ai.visagism.multimodal_interpreter import VisagismMultimodalInterpreter
from app.ai.visagism.rule_engine import VisagismRuleEngine
from app.ai.visagism.report_generator import VisagismReportGenerator

__all__ = [
    "VisagismAnalysisInput",
    "VisagismAnalysisResult",
    "PhotoInput",
    "ProfileContext",
    "PhotoQualityAssessment",
    "FacialMeasurement",
    "FacialProportion",
    "FacialRegionAssessment",
    "HairAssessment",
    "HeadNeckShoulderRelation",
    "AsymmetryAssessment",
    "ExpressionComparison",
    "HaircutRecommendation",
    "DiscouragedCut",
    "PhotoAngle",
    "FaceShape",
    "ConfidenceLevel",
    "EvidenceSource",
    "ChangeLevel",
    "MaintenanceDifficulty",
    "HairTexture",
    "HairThickness",
    "VolumeLevel",
    "NeckLength",
    "ShoulderWidth",
    "SideTreatment",
    "ForeheadExposure",
    "LegacyVisagismAnalysis",
    "VisagismPipeline",
    "EvidenceTracker",
    "Evidence",
    "ConfidenceScorer",
    "ConfidenceBreakdown",
    "VisagismMeasurementEngine",
    "HairAnalyzer",
    "VisagismMultimodalInterpreter",
    "VisagismRuleEngine",
    "VisagismReportGenerator",
]
