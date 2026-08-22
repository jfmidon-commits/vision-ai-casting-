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
    assert result["barber_brief"]["top"] == "comprimento não medido nesta sessão"


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
    assert result["barber_brief"]["texture"] == "não determinada"


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
