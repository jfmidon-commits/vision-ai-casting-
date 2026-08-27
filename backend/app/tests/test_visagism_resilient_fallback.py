from app.ai.visagism.analyzer import VisagismAnalyzer
from app.ai.visagism.interpretation import build_visagism_interpretation


def _analyzer():
    # Private helpers under test do not need an OpenAI client.
    return VisagismAnalyzer.__new__(VisagismAnalyzer)


def _round_measured(*, coverage, volume, texture, neatness):
    return {
        "face_shape": "round",
        "hair_density": "média",
        "hairline": None,
        "hair_current": {
            "coverage_score": coverage,
            "volume_score": volume,
            "texture_score": texture,
            "neatness_score": neatness,
        },
        "skin_undertone": "warm",
        "skin_depth": "medium",
        "season": "Autumn",
        "symmetry": 0.936,
        "photogenic_score": 0.82,
        "triage_categories": ["frontal"],
    }


def test_extract_measured_data_accepts_grooming_coverage_alias():
    analyzer = _analyzer()
    measured = analyzer._extract_measured_data(
        {
            "facial_structure": {
                "face_shape": "round",
                "sources": {"combined": "aggregated"},
            },
            "grooming": {
                "dimensions": {
                    "hair": {
                        "coverage": 0.531,
                        "volume": 0.516,
                        "texture": 1.0,
                        "neatness": 0.625,
                        "overall_score": 0.638,
                    }
                }
            },
        },
        [{"selected": True, "category": "frontal", "filename": "photo-1"}],
    )

    assert measured["hair_density"] == "média"
    assert measured["hair_current"]["coverage_score"] == 0.531
    assert measured["hair_current"]["volume_score"] == 0.516
    assert "hair_density_not_measured" not in measured["_limitations"]


def test_fallback_personalizes_same_face_shape_from_hair_metrics():
    analyzer = _analyzer()
    textured = analyzer._fallback_response(
        "Error code: 429 insufficient_quota",
        _round_measured(coverage=0.85, volume=0.85, texture=0.90, neatness=0.45),
        ["hairline_not_measured"],
    )
    controlled = analyzer._fallback_response(
        "Error code: 429 insufficient_quota",
        _round_measured(coverage=0.45, volume=0.25, texture=0.25, neatness=0.90),
        ["hairline_not_measured"],
    )

    assert len(textured["recommended_hairstyles"]) == 5
    assert len(controlled["recommended_hairstyles"]) == 5
    assert textured["recommended_hairstyles"] != controlled["recommended_hairstyles"]
    assert textured["primary_hairstyle"] != controlled["primary_hairstyle"]
    assert textured["data_source"]["personalized_fallback"] is True
    assert controlled["data_source"]["personalized_fallback"] is True
    assert textured["data_source"]["fallback_metric_count"] == 4
    assert (
        "llm_unavailable_personalized_rule_based_recommendations"
        in textured["limitations"]
    )


def test_fallback_refuses_generic_face_shape_only_recommendations():
    analyzer = _analyzer()
    result = analyzer._fallback_response(
        "Error code: 429 insufficient_quota",
        {
            "face_shape": "round",
            "hair_density": "média",
            "hairline": None,
            "skin_undertone": "warm",
            "symmetry": 0.936,
        },
        ["hairline_not_measured"],
    )

    assert result["recommended_hairstyles"] == []
    assert result["primary_hairstyle"] is None
    assert result["data_source"]["personalized_fallback"] is False
    assert "fallback_insufficient_personalization" in result["limitations"]

    interpretation = build_visagism_interpretation(result)
    assert interpretation["status"] == "service_limited"


def test_fallback_remains_fail_closed_without_measured_face_shape():
    analyzer = _analyzer()
    result = analyzer._fallback_response(
        "quota",
        {"face_shape": None, "hair_density": None, "hairline": None},
        ["face_shape_not_measured"],
    )

    assert result["recommended_hairstyles"] == []
    assert result["primary_hairstyle"] is None
    assert result["data_source"]["rule_based_interpretation"] is False
    assert "fallback_no_grounded_face_shape" in result["limitations"]


def test_interpretation_marks_personalized_service_fallback_as_partial():
    analyzer = _analyzer()
    raw = analyzer._fallback_response(
        "Error code: 429 insufficient_quota",
        _round_measured(coverage=0.72, volume=0.64, texture=0.81, neatness=0.58),
        ["hairline_not_measured"],
    )

    interpretation = build_visagism_interpretation(raw)

    assert interpretation["status"] == "partial_grounded"
    assert interpretation["primary_recommendation"]["name"] == raw["primary_hairstyle"]
    assert "densidade do cabelo: média" in interpretation["executive_summary"]
    attention = interpretation["current_hair_assessment"]["attention_points"]
    assert any(
        "interpretação avançada" in item.lower() and "medições" in item.lower()
        for item in attention
    )
    assert (
        "A linha frontal do cabelo não pôde ser confirmada com confiança suficiente."
        in attention
    )
    assert (
        "Uma parte da análise não pôde ser confirmada com segurança." not in attention
    )
