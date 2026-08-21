from app.pipelines.visagism.report import VisagismReportBuilder


def test_report_preserves_evidence_and_integrity_contract():
    result = {
        "triage": {
            "processed_images": 12,
            "selected_views": {"frontal": {"filename": "front.jpg"}},
            "evidence_source": "ImageTriageEngine",
        },
        "evidence_image": "/tmp/front.jpg",
        "measurements": {
            "face_detected": True,
            "face_shape": {
                "value": "oval",
                "status": "estimated",
                "source": "FaceMesh proportions heuristic",
            },
            "measurements": {
                "face_width": {
                    "value": 0.42,
                    "unit": "normalized_image_ratio",
                    "status": "observed",
                }
            },
            "evidence_source": "MediaPipe FaceLandmarker",
        },
        "hair_analysis": {
            "observed": {"visual_coverage": {"value": 0.8, "status": "observed"}},
            "estimated": {
                "visual_density": {"value": "high_visual_density", "status": "estimated"}
            },
            "not_determinable": {
                "current_length": {
                    "status": "not_determinable",
                    "reason": "no physical scale",
                }
            },
            "evidence_sources": ["GroomingAnalyzer", "ImageTriageEngine"],
        },
        "cut_recommendations": {
            "primary": {"name": "Ivy League"},
            "options": [{"name": "Ivy League"}],
            "ranking_method": "deterministic_face_shape_and_visual_density_rules",
        },
        "simulation": {"available": False, "provider": "none"},
        "card": {"path": "/tmp/card.png", "synthetic_simulation_used": False},
        "limitations": ["measurements_are_normalized_not_physical"],
    }

    report = VisagismReportBuilder().build(result)

    assert report["schema_version"] == "1.0"
    assert report["evidence"]["processed_images"] == 12
    assert report["facial_analysis"]["measurements"]["face_width"]["unit"] == "normalized_image_ratio"
    assert report["hair_analysis"]["not_determinable"]["current_length"]["status"] == "not_determinable"
    assert report["recommendations"]["primary"]["name"] == "Ivy League"
    assert report["integrity"]["physical_measurements_claimed"] is False
    assert report["integrity"]["synthetic_simulation_presented_as_real"] is False
    assert report["integrity"]["unknown_fields_preserved_as_not_determinable"] is True
