from app.ai.visagism.recommendation_presenter import present_recommendation, present_recommendations


def test_presenter_translates_primary_technical_id():
    result = present_recommendation(
        {
            "rank": 1,
            "name": "volume_on_top",
            "justification": "Formato triangular. Textura unknown, espessura unknown.",
            "confidence": 0.55,
            "volume_distribution": "Volume no topo e regiao frontal",
            "forehead_exposure": "full",
            "side_treatment": "tapered",
        }
    )

    assert result["technical_id"] == "volume_on_top"
    assert result["display_name"] == "Topo texturizado com volume e taper suave"
    assert "6-9 cm" in result["barber_instructions"]
    assert result["hair_data_complete"] is False
    assert result["hair_data_note"]


def test_presenter_keeps_five_unique_ranked_recommendations():
    items = [
        {"rank": 1, "name": "volume_on_top", "justification": "ok"},
        {"rank": 2, "name": "layered_top", "justification": "ok"},
        {"rank": 3, "name": "side_swept", "justification": "ok"},
        {"rank": 4, "name": "asymmetrical", "justification": "ok"},
        {"rank": 5, "name": "height_at_crown", "justification": "ok"},
    ]

    presented = present_recommendations(items)

    assert len(presented) == 5
    assert [item["rank"] for item in presented] == [1, 2, 3, 4, 5]
    assert len({item["display_name"] for item in presented}) == 5
    assert all(item["barber_instructions"] for item in presented)
