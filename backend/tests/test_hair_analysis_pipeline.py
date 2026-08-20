from app.pipelines.visagism import HairAnalysisEngine


def _grooming_result():
    return {
        "confidence": 0.87,
        "landmarks_detected": True,
        "dimensions": {
            "hair": {
                "coverage_score": 0.81,
                "volume_score": 0.63,
                "texture_score": 0.52,
                "shine_score": 0.44,
                "neatness_score": 0.71,
                "overall_score": 0.66,
            }
        },
    }


def test_hair_analysis_preserves_real_grooming_evidence():
    engine = HairAnalysisEngine()
    result = engine.analyze(_grooming_result())

    coverage = result["observed"]["visual_coverage"]
    assert coverage["value"] == 0.81
    assert coverage["status"] == "observed"
    assert "GroomingAnalyzer" in coverage["source"]


def test_hair_density_is_explicitly_an_estimate():
    engine = HairAnalysisEngine()
    result = engine.analyze(_grooming_result())

    density = result["estimated"]["visual_density"]
    assert density["value"] == "high_visual_density"
    assert density["status"] == "estimated"
    assert density["confidence"] == 0.87


def test_unsupported_hair_facts_are_not_invented():
    engine = HairAnalysisEngine()
    result = engine.analyze(_grooming_result())

    for key in (
        "current_length",
        "temple_recession",
        "gray_distribution",
        "growth_direction",
        "curl_pattern",
    ):
        assert result["not_determinable"][key]["status"] == "not_determinable"


def test_hairline_view_is_traceable_to_triage():
    engine = HairAnalysisEngine()
    triage = {
        "selected_views": {
            "hairline": {
                "filename": "hairline.jpg",
                "category": "hairline",
                "confidence": 0.91,
            }
        }
    }
    result = engine.analyze(_grooming_result(), triage)

    hairline = result["observed"]["hairline_view_available"]
    assert hairline["value"] is True
    assert hairline["confidence"] == 0.91
    assert hairline["source"] == "ImageTriageEngine"


def test_missing_hair_metrics_report_limitations():
    engine = HairAnalysisEngine()
    result = engine.analyze({"dimensions": {}, "landmarks_detected": False})

    assert "hair_metrics_unavailable" in result["limitations"]
    assert "facemesh_landmarks_unavailable" in result["limitations"]
    assert "hairline_view_missing" in result["limitations"]
    assert "visual_density" in result["not_determinable"]
