"""Serializable report builder for the reproducible visagism pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Mapping


class VisagismReportBuilder:
    """Build a stable, machine-readable report without inventing evidence."""

    SCHEMA_VERSION = "1.0"

    def build(self, pipeline_result: Mapping[str, Any]) -> Dict[str, Any]:
        triage = pipeline_result.get("triage", {})
        measurements = pipeline_result.get("measurements", {})
        hair = pipeline_result.get("hair_analysis", {})
        cuts = pipeline_result.get("cut_recommendations", {})
        simulation = pipeline_result.get("simulation", {})
        card = pipeline_result.get("card")

        selected_views = triage.get("selected_views", {}) if isinstance(triage, Mapping) else {}
        primary = cuts.get("primary") if isinstance(cuts, Mapping) else None

        return {
            "schema_version": self.SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline": "RealVisagismPipeline",
            "evidence": {
                "processed_images": triage.get("processed_images", 0),
                "selected_views": selected_views,
                "evidence_image": pipeline_result.get("evidence_image"),
                "sources": self._sources(triage, measurements, hair),
            },
            "facial_analysis": {
                "face_detected": measurements.get("face_detected", False),
                "face_shape": measurements.get("face_shape"),
                "measurements": measurements.get("measurements", {}),
            },
            "hair_analysis": {
                "observed": hair.get("observed", {}),
                "estimated": hair.get("estimated", {}),
                "not_determinable": hair.get("not_determinable", {}),
            },
            "recommendations": {
                "primary": primary,
                "options": cuts.get("options", []),
                "ranking_method": cuts.get("ranking_method"),
            },
            "simulation": simulation,
            "card": card,
            "limitations": list(pipeline_result.get("limitations", [])),
            "integrity": {
                "physical_measurements_claimed": False,
                "synthetic_simulation_presented_as_real": False,
                "unknown_fields_preserved_as_not_determinable": True,
            },
        }

    @staticmethod
    def _sources(
        triage: Mapping[str, Any],
        measurements: Mapping[str, Any],
        hair: Mapping[str, Any],
    ) -> list[str]:
        sources = []
        for source in (
            triage.get("evidence_source"),
            measurements.get("evidence_source"),
        ):
            if isinstance(source, str) and source:
                sources.append(source)
        hair_sources = hair.get("evidence_sources", [])
        if isinstance(hair_sources, list):
            sources.extend(source for source in hair_sources if isinstance(source, str))
        return list(dict.fromkeys(sources))
