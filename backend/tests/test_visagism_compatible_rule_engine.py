from app.ai.visagism.compatible_rule_engine import CompatibleVisagismRuleEngine


def test_current_proportion_schema_generates_adjustments():
    engine = CompatibleVisagismRuleEngine()
    proportions = {
        "height_to_width_ratio": {
            "value": 1.2146,
            "classification": "below_ideal",
        },
        "jaw_to_face_ratio": {
            "value": 0.8793,
            "classification": "within_ideal",
        },
        "forehead_to_face_ratio": {
            "value": 0.6272,
            "classification": "below_ideal",
        },
    }

    adjustments = engine._analyze_proportions(proportions)
    descriptions = [item["description"] for item in adjustments]

    assert len(adjustments) == 2
    assert any("altura visual" in item for item in descriptions)
    assert any("volume frontal" in item for item in descriptions)


def test_legacy_proportion_schema_remains_supported():
    engine = CompatibleVisagismRuleEngine()
    proportions = {
        "forehead_height_ratio": {"value": 0.3, "classification": "low"},
        "face_width_ratio": {"value": 0.8, "classification": "wide"},
        "jaw_width_ratio": {"value": 0.5, "classification": "strong"},
    }

    adjustments = engine._analyze_proportions(proportions)

    assert len(adjustments) == 3
