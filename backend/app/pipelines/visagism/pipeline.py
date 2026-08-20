"""Minimal reproducible visagism pipeline.

This first stage deliberately reuses the existing ImageTriageEngine and keeps
all outputs traceable to real triage evidence. Later stages can add facial
measurements, hair analysis, recommendations and card generation without
changing the contract established here.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.ai.image_triage.engine import ImageTriageEngine, TriageCategory, TriageResult


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

    def __init__(self, triage_engine: Optional[ImageTriageEngine] = None) -> None:
        self.triage_engine = triage_engine or ImageTriageEngine()

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
