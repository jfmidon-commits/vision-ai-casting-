"""Schemas for the user-facing full visagism pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FullVisagismRequest(BaseModel):
    """Request a complete multi-photo visagism analysis for a photoshoot."""

    photoshoot_id: UUID
    cut_limit: int = Field(default=5, ge=5, le=7)
    generate_card: bool = True


class HaircutRecommendation(BaseModel):
    rank: int = Field(..., ge=1)
    key: str
    name: str
    compatibility_score: float = Field(..., ge=0.0, le=1.0)
    top_cm: List[float]
    sides_mm: List[int]
    fade: str
    connection: str
    direction: str
    finish: str
    maintenance: str
    avoid: str
    reasons: List[str] = []
    risks: List[str] = []
    evidence: Dict[str, Any] = {}


class FullVisagismAnalysis(BaseModel):
    """Stable response contract for the complete reproducible analysis."""

    schema_version: str = "1.0"
    analysis_id: Optional[UUID] = None
    photoshoot_id: UUID
    status: str
    processed_images: int = 0
    selected_views: Dict[str, Any] = {}
    face_shape: Optional[Dict[str, Any]] = None
    measurements: Dict[str, Any] = {}
    hair_analysis: Dict[str, Any] = {}
    recommendations: List[HaircutRecommendation] = []
    top_recommendation: Optional[HaircutRecommendation] = None
    card_url: Optional[str] = None
    manifest_url: Optional[str] = None
    simulation_url: Optional[str] = None
    analysis_sources: List[str] = []
    limitations: List[str] = []
    integrity: Dict[str, Any] = {}
