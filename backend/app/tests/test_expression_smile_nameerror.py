from app.ai.expressions import ExpressionAnalyzer


def test_combine_results_does_not_raise_when_scoring_angry_and_disgust():
    analyzer = object.__new__(ExpressionAnalyzer)

    eyes = {"detected": True, "arched_score": 0.1}
    smile = {"detected": False, "score": 0.0}
    eyebrows = {
        "elevation_score": 0.1,
        "furrow_score": 0.6,
        "symmetry": 0.8,
    }
    mouth = {
        "openness": 0.1,
        "corners_up": 0.0,
        "corners_down": 0.4,
    }

    result = analyzer._combine_results(None, eyes, smile, eyebrows, mouth)

    assert result["angry"] == 1.0
    assert result["disgust"] == 1.0
    assert result["happy"] == 0.0
