from app.ai.facial_analysis.analyzer import FacialAnalyzer


def test_aggregate_results_tolerates_empty_facial_thirds():
    analyzer = FacialAnalyzer.__new__(FacialAnalyzer)

    results = [
        {
            "face_shape": "oval",
            "symmetry_score": 0.9,
            "golden_ratio_score": 0.8,
            "facial_thirds": {},
            "emotions": {},
        },
        {
            "face_shape": "oval",
            "symmetry_score": 0.8,
            "golden_ratio_score": 0.7,
            "facial_thirds": {
                "upper_third": 0.31,
                "middle_third": 0.34,
                "lower_third": 0.35,
            },
            "emotions": {},
        },
    ]

    aggregated = analyzer._aggregate_results(results)

    assert aggregated["facial_thirds"] == {
        "upper_third": 0.31,
        "middle_third": 0.34,
        "lower_third": 0.35,
    }
    assert aggregated["photos_analyzed"] == 2


def test_aggregate_results_tolerates_partial_facial_thirds():
    analyzer = FacialAnalyzer.__new__(FacialAnalyzer)

    results = [
        {
            "face_shape": "mixed",
            "symmetry_score": 0.75,
            "golden_ratio_score": 0.72,
            "facial_thirds": {"upper_third": 0.3},
            "emotions": {},
        },
        {
            "face_shape": "mixed",
            "symmetry_score": 0.77,
            "golden_ratio_score": 0.74,
            "facial_thirds": {"middle_third": 0.33, "lower_third": 0.37},
            "emotions": {},
        },
    ]

    aggregated = analyzer._aggregate_results(results)

    assert aggregated["facial_thirds"] == {
        "upper_third": 0.3,
        "middle_third": 0.33,
        "lower_third": 0.37,
    }
