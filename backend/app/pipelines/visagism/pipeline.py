"""Reproducible visagism pipeline built from Vision's real analyzers."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from app.ai.image_triage.engine import (
    ImageTriageEngine,
    TriageCategory,
    TriageResult,
)
from app.pipelines.visagism.card_generator import BarberCardGenerator
from app.pipelines.visagism.cut_recommendations import CutRecommendationEngine
from app.pipelines.visagism.grooming_hair_adapter import GroomingHairEvidenceAdapter
from app.pipelines.visagism.hair_analysis import HairAnalysisEngine
from app.pipelines.visagism.measurements import FacialMeasurementEngine
from app.pipelines.visagism.simulation import (
    HairSimulationProvider,
    NullHairSimulationProvider,
)


class RealVisagismPipeline:
    """Orchestrate deterministic visagism stages using Vision's real engines."""

    ESSENTIAL_VIEWS = (
        TriageCategory.FRONTAL,
        TriageCategory.THREE_QUARTER_LEFT,
        TriageCategory.THREE_QUARTER_RIGHT,
        TriageCategory.PROFILE_LEFT,
        TriageCategory.PROFILE_RIGHT,
        TriageCategory.HAIRLINE,
        TriageCategory.POSTERIOR,
        TriageCategory.HALF_BODY,
        TriageCategory.SMILING,
    )

    FACIAL_EVIDENCE_ORDER = (
        TriageCategory.FRONTAL.value,
        TriageCategory.HAIRLINE.value,
        TriageCategory.THREE_QUARTER_RIGHT.value,
        TriageCategory.THREE_QUARTER_LEFT.value,
    )

    def __init__(
        self,
        triage_engine: Optional[ImageTriageEngine] = None,
        measurement_engine: Optional[FacialMeasurementEngine] = None,
        grooming_analyzer: Optional[Any] = None,
        hair_engine: Optional[HairAnalysisEngine] = None,
        cut_engine: Optional[CutRecommendationEngine] = None,
        card_generator: Optional[BarberCardGenerator] = None,
        simulation_provider: Optional[HairSimulationProvider] = None,
    ) -> None:
        self.triage_engine = triage_engine or ImageTriageEngine()
        self.measurement_engine = measurement_engine or FacialMeasurementEngine(
            self.triage_engine
        )
        # Keep the injection name for backwards compatibility with tests/callers,
        # but default to a hair-only adapter. Haircut recommendations must not
        # depend on unrelated beard/skin/eyebrow analysis succeeding.
        self.grooming_analyzer = grooming_analyzer or GroomingHairEvidenceAdapter()
        self.hair_engine = hair_engine or HairAnalysisEngine()
        self.cut_engine = cut_engine or CutRecommendationEngine()
        self.card_generator = card_generator or BarberCardGenerator()
        self.simulation_provider = simulation_provider or NullHairSimulationProvider()

    def run_triage(self, dataset_path: str) -> Dict:
        """Process a real dataset and return evidence plus selected best views."""
        results = self.triage_engine.process_dataset(dataset_path)
        best = self.triage_engine.select_best_by_category(results)

        triage = [self._serialize_result(result) for result in results]
        selected_views = {
            category.value: self._serialize_result(best[category])
            for category in self.ESSENTIAL_VIEWS
            if category in best
        }
        missing_views = [
            category.value for category in self.ESSENTIAL_VIEWS if category not in best
        ]

        return {
            "dataset_path": dataset_path,
            "processed_images": len(results),
            "triage": triage,
            "selected_views": selected_views,
            "missing_views": missing_views,
            "evidence_source": "ImageTriageEngine",
            "limitations": self._limitations(results, missing_views),
        }

    def run_measurements(self, image_path: str) -> Dict:
        """Measure a selected face using real MediaPipe FaceLandmarker evidence."""
        return self.measurement_engine.analyze_image(image_path)

    def run_hair_analysis(self, image_path: str, triage_output: Dict) -> Dict:
        """Run real hair-only grooming analysis and normalize its evidence."""
        try:
            with open(image_path, "rb") as image_file:
                grooming = self.grooming_analyzer.analyze(image_file.read())
        except OSError as exc:
            return {
                "observed": {},
                "estimated": {},
                "not_determinable": {},
                "evidence_sources": [],
                "limitations": [f"image_read_error:{exc}"],
            }
        return self.hair_engine.analyze(grooming, triage_output)

    def recommend_cuts(
        self,
        measurements: Dict,
        hair_analysis: Dict,
        limit: int = 5,
    ) -> Dict:
        """Rank cuts from measured face shape and structured hair evidence."""
        face_shape = measurements.get("face_shape", {})
        shape_value = (
            face_shape.get("value", "mixed")
            if isinstance(face_shape, dict)
            else "mixed"
        )
        return self.cut_engine.recommend(shape_value, hair_analysis, limit=limit)

    def generate_card(
        self,
        evidence_image: str,
        recommendations: Dict,
        output_path: str,
    ) -> Optional[Dict]:
        """Generate the technical PNG card from the primary recommendation."""
        primary = recommendations.get("primary")
        if not isinstance(primary, dict):
            return None
        return self.card_generator.generate(
            evidence_image,
            primary,
            output_path,
        )

    def run_simulation(
        self,
        evidence_image: str,
        recommendations: Dict,
        output_path: Optional[str] = None,
    ) -> Dict:
        """Run an optional simulation provider without affecting real evidence."""
        primary = recommendations.get("primary")
        if not isinstance(primary, dict):
            return {
                "available": False,
                "provider": self.simulation_provider.name,
                "reason": "no_primary_recommendation",
            }
        return self.simulation_provider.simulate(
            evidence_image,
            primary,
            output_path,
        )

    def run(
        self,
        dataset_path: str,
        cut_limit: int = 5,
        card_output_path: Optional[str] = None,
        simulation_output_path: Optional[str] = None,
    ) -> Dict:
        """Execute the implemented real pipeline end to end."""
        triage = self.run_triage(dataset_path)
        evidence_image = self._select_facial_evidence_image(dataset_path, triage)
        limitations = list(triage.get("limitations", []))

        if not evidence_image:
            limitations.append("no_suitable_facial_evidence_image")
            return {
                "triage": triage,
                "measurements": {},
                "hair_analysis": {},
                "cut_recommendations": {"options": [], "primary": None},
                "simulation": {
                    "available": False,
                    "provider": self.simulation_provider.name,
                    "reason": "no_suitable_facial_evidence_image",
                },
                "card": None,
                "limitations": limitations,
            }

        measurements = self.run_measurements(evidence_image)
        hair_analysis = self.run_hair_analysis(evidence_image, triage)
        recommendations = self.recommend_cuts(
            measurements,
            hair_analysis,
            limit=cut_limit,
        )
        simulation = self.run_simulation(
            evidence_image,
            recommendations,
            simulation_output_path,
        )
        card = None
        if card_output_path:
            card = self.generate_card(
                evidence_image,
                recommendations,
                card_output_path,
            )

        limitations.extend(measurements.get("limitations", []))
        limitations.extend(hair_analysis.get("limitations", []))

        return {
            "triage": triage,
            "evidence_image": evidence_image,
            "measurements": measurements,
            "hair_analysis": hair_analysis,
            "cut_recommendations": recommendations,
            "simulation": simulation,
            "card": card,
            "limitations": list(dict.fromkeys(limitations)),
        }

    def _select_facial_evidence_image(
        self,
        dataset_path: str,
        triage_output: Dict,
    ) -> Optional[str]:
        selected = triage_output.get("selected_views", {})
        if not isinstance(selected, dict):
            return None
        for category in self.FACIAL_EVIDENCE_ORDER:
            result = selected.get(category)
            if not isinstance(result, dict):
                continue
            filename = result.get("filename")
            if filename:
                return os.path.join(dataset_path, filename)
        return None

    @staticmethod
    def _serialize_result(result: TriageResult) -> Dict:
        return {
            "filename": result.filename,
            "category": result.category.value,
            "confidence": float(result.confidence),
            "selected": bool(result.selected),
            "scores": dict(result.scores),
            "rejection_reasons": list(result.rejection_reasons),
        }

    @staticmethod
    def _limitations(results: List[TriageResult], missing_views: List[str]) -> List[str]:
        limitations: List[str] = []
        if not results:
            limitations.append("no_images_processed")
        if missing_views:
            limitations.append("missing_required_views")
        if any(result.category == TriageCategory.REJECTED for result in results):
            limitations.append("dataset_contains_rejected_images")
        return limitations
