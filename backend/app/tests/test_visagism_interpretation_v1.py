from app.ai.visagism.interpretation import build_visagism_interpretation


def test_interpretation_keeps_grounded_haircut_names_only():
    raw = {
        "recommended_hairstyles": ["Textured crop", "Side part"],
        "primary_hairstyle": "Textured crop",
        "primary_justification": "Formato oval e densidade alta favorecem o corte.",
        "measured_data_used": {
            "face_shape": "oval",
            "hair_density": "alta",
            "hairline": "detectado",
        },
        "current_hair": {
            "summary": "Cobertura alta",
            "density": "alta",
            "hairline": "detectado",
        },
        "confidence": 0.86,
        "limitations": [],
    }

    result = build_visagism_interpretation(raw)

    assert result["status"] == "ready"
    assert result["primary_recommendation"]["name"] == "Textured crop"
    assert [item["name"] for item in result["alternative_hairstyles"]] == ["Side part"]
    assert "cm" not in result["barber_brief"]["top"]
    assert "cabelo real" in result["barber_brief"]["top"]


def test_interpretation_never_fills_missing_measurements():
    raw = {
        "recommended_hairstyles": ["Crew cut"],
        "primary_hairstyle": "Crew cut",
        "measured_data_used": {
            "face_shape": None,
            "hair_density": None,
            "hairline": None,
        },
        "current_hair": {
            "summary": "não medido",
            "density": "não medido",
            "hairline": "não medido",
        },
        "confidence": 0.4,
        "limitations": ["grooming_analyzer_not_available"],
    }

    result = build_visagism_interpretation(raw)

    assert result["primary_recommendation"]["name"] == "Crew cut"
    points = " ".join(result["current_hair_assessment"]["attention_points"])
    assert "densidade" in points.lower()
    assert "linha frontal" in points.lower()
    assert "formato facial" in points.lower()
    assert "avaliar" in result["barber_brief"]["texture"].lower()


def test_interpretation_insufficient_data_has_no_primary():
    result = build_visagism_interpretation({
        "recommended_hairstyles": [],
        "primary_hairstyle": None,
        "confidence": 0.0,
        "limitations": ["no_grounded_hairstyles"],
    })

    assert result["status"] == "insufficient_grounded_data"
    assert result["primary_recommendation"] is None
    assert result["alternative_hairstyles"] == []
    assert result["barber_brief"]["recommendation_name"] is None


def test_primary_not_in_grounded_list_is_not_preserved():
    result = build_visagism_interpretation({
        "recommended_hairstyles": ["A", "B"],
        "primary_hairstyle": "Inventado",
        "confidence": 0.8,
        "measured_data_used": {"face_shape": "oval"},
    })

    assert result["primary_recommendation"]["name"] == "A"
    assert result["primary_recommendation"]["name"] != "Inventado"


def test_limitations_are_human_readable_not_raw_codes():
    result = build_visagism_interpretation({
        "recommended_hairstyles": [],
        "limitations": ["facial_result_is_mock", "fewer_than_5_grounded_hairstyles:2"],
    })

    combined = " ".join(result["limitations"])
    assert "facial_result_is_mock" not in combined
    assert "fewer_than_5_grounded_hairstyles" not in combined
    assert len(result["limitations"]) == 2


def test_rule_based_result_translates_round_and_marks_partial_fallback():
    raw = {
        "recommended_hairstyles": [
            "Quiff texturizado",
            "Side Part com volume no topo",
            "Pompadour moderado",
            "Undercut com topo alongado",
            "Crew Cut com laterais mais baixas",
        ],
        "primary_hairstyle": "Quiff texturizado",
        "primary_justification": "Fallback determinístico baseado no formato facial round medido nesta sessão.",
        "measured_data_used": {
            "face_shape": "round",
            "hair_density": "média",
            "hairline": None,
        },
        "current_hair": {
            "summary": "Cabelo atual com densidade média.",
            "density": "média",
            "hairline": "não medido",
        },
        "confidence": 0.55,
        "limitations": ["hairline_not_measured", "llm_unavailable_rule_based_recommendations"],
        "data_source": {
            "measured": True,
            "llm_interpretation": False,
            "rule_based_interpretation": True,
        },
    }

    result = build_visagism_interpretation(raw)

    assert result["status"] == "partial_grounded"
    assert "formato facial: redondo" in result["executive_summary"]
    assert "round" not in result["executive_summary"]
    assert "Fallback" not in result["primary_recommendation"]["why_it_works"]
    assert "alongar visualmente" in result["primary_recommendation"]["why_it_works"]
    assert result["alternative_hairstyles"][0]["name"] == "Side Part com volume no topo"
    assert "assimetria visual" in result["alternative_hairstyles"][0]["why_it_works"]


def test_rule_based_barber_brief_is_actionable_without_inventing_measurements():
    result = build_visagism_interpretation({
        "recommended_hairstyles": ["Quiff texturizado"],
        "primary_hairstyle": "Quiff texturizado",
        "measured_data_used": {"face_shape": "round", "hair_density": "média"},
        "current_hair": {"density": "média"},
        "confidence": 0.55,
        "data_source": {"rule_based_interpretation": True},
    })

    brief = result["barber_brief"]
    assert "volume" in brief["top"].lower()
    assert "controladas" in brief["sides"].lower()
    assert "cm" not in brief["top"]
    assert "mm" not in brief["top"]
    assert "cm/mm" in brief["note"]