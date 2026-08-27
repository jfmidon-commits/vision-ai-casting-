from app.ai.visagism.analyzer import VisagismAnalyzer
from app.ai.visagism.interpretation import build_visagism_interpretation


def _analyzer():
    # Private helpers under test do not need an OpenAI client.
    return VisagismAnalyzer.__new__(VisagismAnalyzer)


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


def test_fallback_returns_five_rule_based_cuts_for_measured_round_face():
    analyzer = _analyzer()
    result = analyzer._fallback_response(
        "Error code: 429 insufficient_quota",
        {
            "face_shape": "round",
            "hair_density": "média",
            "hairline": None,
            "skin_undertone": "warm",
            "skin_depth": "medium",
            "season": "Autumn",
            "symmetry": 0.936,
            "photogenic_score": 0.82,
            "triage_categories": ["frontal"],
        },
        ["hairline_not_measured"],
    )

    assert len(result["recommended_hairstyles"]) == 5
    assert result["primary_hairstyle"] == result["recommended_hairstyles"][0]
    assert result["current_hair"]["density"] == "média"
    assert result["confidence"] == 0.55
    assert result["data_source"]["measured"] is True
    assert result["data_source"]["llm_interpretation"] is False
    assert result["data_source"]["rule_based_interpretation"] is True
    assert "llm_unavailable_rule_based_recommendations" in result["limitations"]
    assert all(not item.lower().startswith("error:") for item in result["limitations"])
    assert "429" in result["error"]


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


def test_interpretation_explains_service_fallback_without_blame_on_photo():
    analyzer = _analyzer()
    raw = analyzer._fallback_response(
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

    interpretation = build_visagism_interpretation(raw)

    assert interpretation["status"] == "ready"
    assert interpretation["primary_recommendation"]["name"] == raw["primary_hairstyle"]
    assert "densidade do cabelo: média" in interpretation["executive_summary"]
    attention = interpretation["current_hair_assessment"]["attention_points"]
    assert "A interpretação avançada estava indisponível; as opções abaixo foram geradas por regras conservadoras usando apenas medições confirmadas." in attention
    assert "A linha frontal do cabelo não pôde ser confirmada com confiança suficiente." in attention
    assert "Uma parte da análise não pôde ser confirmada com segurança." not in attention
