from app.pipelines.visagism import CutRecommendationEngine


def _hair_analysis(density="medium_visual_density", limitations=None):
    return {
        "observed": {},
        "estimated": {
            "visual_density": {
                "value": density,
                "status": "estimated",
                "confidence": 0.8,
            }
        },
        "limitations": limitations or [],
    }


def test_recommender_returns_at_least_five_ranked_options():
    engine = CutRecommendationEngine()
    result = engine.recommend("oval", _hair_analysis(), limit=5)

    assert len(result["options"]) == 5
    assert result["primary"] == result["options"][0]
    scores = [item["compatibility_score"] for item in result["options"]]
    assert scores == sorted(scores, reverse=True)


def test_each_cut_contains_technical_barber_specification():
    engine = CutRecommendationEngine()
    result = engine.recommend("square", _hair_analysis(), limit=5)

    for cut in result["options"]:
        assert len(cut["top_cm"]) == 2
        assert len(cut["sides_mm"]) == 2
        assert cut["fade"]
        assert cut["connection"]
        assert cut["direction"]
        assert cut["finish"]
        assert cut["maintenance"]
        assert cut["avoid"]


def test_ranking_uses_traceable_face_and_density_evidence():
    engine = CutRecommendationEngine()
    result = engine.recommend("round", _hair_analysis("high_visual_density"), limit=5)

    for cut in result["options"]:
        assert cut["evidence"]["face_shape"] == "round"
        assert cut["evidence"]["visual_density"] == "high_visual_density"
    assert result["ranking_method"] == (
        "deterministic_face_shape_and_visual_density_rules"
    )


def test_missing_hairline_makes_recommendations_more_conservative():
    engine = CutRecommendationEngine()
    normal = engine.recommend("oval", _hair_analysis(), limit=5)
    limited = engine.recommend(
        "oval",
        _hair_analysis(limitations=["hairline_view_missing"]),
        limit=5,
    )

    assert limited["primary"]["compatibility_score"] <= normal["primary"][
        "compatibility_score"
    ]
    assert any("hairline" in risk for risk in limited["primary"]["risks"])
