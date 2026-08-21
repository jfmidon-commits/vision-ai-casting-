"""Structured hair analysis for the reproducible visagism pipeline.

This module does not re-run computer vision. It normalizes evidence already
produced by Vision's real GroomingAnalyzer and ImageTriageEngine, explicitly
separating observed metrics, estimates and facts that cannot be determined
from the available evidence.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


class HairAnalysisEngine:
    """Normalize real grooming evidence into a non-hallucinatory hair profile."""

    SOURCE = "GroomingAnalyzer"

    def analyze(
        self,
        grooming_result: Mapping[str, Any],
        triage_result: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        dimensions = grooming_result.get("dimensions", {}) if grooming_result else {}
        hair = dimensions.get("hair", {}) if isinstance(dimensions, Mapping) else {}
        triage = triage_result or {}

        observations: Dict[str, Dict[str, Any]] = {}
        estimates: Dict[str, Dict[str, Any]] = {}
        not_determinable: Dict[str, Dict[str, str]] = {}
        limitations = []

        self._copy_observed_metric(
            observations,
            hair,
            "coverage_score",
            "visual_coverage",
            "normalized_score",
        )
        self._copy_observed_metric(
            observations,
            hair,
            "volume_score",
            "visual_volume",
            "normalized_score",
        )
        self._copy_observed_metric(
            observations,
            hair,
            "texture_score",
            "texture_activity",
            "normalized_score",
        )
        self._copy_observed_metric(
            observations,
            hair,
            "shine_score",
            "shine",
            "normalized_score",
        )
        self._copy_observed_metric(
            observations,
            hair,
            "neatness_score",
            "neatness",
            "normalized_score",
        )

        coverage = self._score(hair, "coverage_score")
        if coverage is not None:
            estimates["visual_density"] = {
                "value": self._density_label(coverage),
                "confidence": self._estimate_confidence(grooming_result),
                "source": "derived_from_visual_coverage",
                "status": "estimated",
            }
        else:
            not_determinable["visual_density"] = self._reason(
                "coverage_score unavailable"
            )

        selected_views = triage.get("selected_views", {}) if isinstance(triage, Mapping) else {}
        hairline_view = (
            selected_views.get("hairline")
            if isinstance(selected_views, Mapping)
            else None
        )
        observations["hairline_view_available"] = {
            "value": bool(hairline_view),
            "confidence": float(hairline_view.get("confidence", 0.0))
            if isinstance(hairline_view, Mapping)
            else 0.0,
            "source": "ImageTriageEngine",
            "status": "observed",
        }

        unsupported = {
            "current_length": "no calibrated physical scale or strand-length estimator",
            "temple_recession": "current analyzers do not quantify temple recession",
            "gray_distribution": "current grooming metrics do not segment gray hair",
            "growth_direction": "single-image grooming metrics do not estimate hair-growth vectors",
            "curl_pattern": "texture_score is image activity, not a calibrated curl classifier",
        }
        for field, reason in unsupported.items():
            not_determinable[field] = self._reason(reason)

        if not hair:
            limitations.append("hair_metrics_unavailable")
        if not grooming_result.get("landmarks_detected", False):
            limitations.append("facemesh_landmarks_unavailable")
        if not hairline_view:
            limitations.append("hairline_view_missing")

        return {
            "observed": observations,
            "estimated": estimates,
            "not_determinable": not_determinable,
            "evidence_sources": [self.SOURCE, "ImageTriageEngine"],
            "limitations": limitations,
        }

    @staticmethod
    def _score(hair: Mapping[str, Any], key: str) -> Optional[float]:
        value = hair.get(key)
        if isinstance(value, (int, float)):
            return float(max(0.0, min(1.0, value)))
        return None

    def _copy_observed_metric(
        self,
        output: Dict[str, Dict[str, Any]],
        hair: Mapping[str, Any],
        source_key: str,
        output_key: str,
        unit: str,
    ) -> None:
        score = self._score(hair, source_key)
        if score is None:
            return
        output[output_key] = {
            "value": score,
            "unit": unit,
            "confidence": 1.0,
            "source": f"{self.SOURCE}.dimensions.hair.{source_key}",
            "status": "observed",
        }

    @staticmethod
    def _density_label(coverage: float) -> str:
        if coverage >= 0.75:
            return "high_visual_density"
        if coverage >= 0.45:
            return "medium_visual_density"
        return "low_visual_density"

    @staticmethod
    def _estimate_confidence(grooming_result: Mapping[str, Any]) -> float:
        confidence = grooming_result.get("confidence", 0.5)
        if isinstance(confidence, (int, float)):
            return float(max(0.0, min(1.0, confidence)))
        return 0.5

    @staticmethod
    def _reason(reason: str) -> Dict[str, str]:
        return {"status": "not_determinable", "reason": reason}
