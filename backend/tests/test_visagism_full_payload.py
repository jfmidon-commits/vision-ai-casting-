from app.services.ai_service import AIService


def test_build_full_visagism_payload_flattens_report_contract():
    pipeline_result = {
        "report": {
            "schema_version": "1.0",
            "evidence": {
                "processed_images": 10,
                "selected_views": {"frontal": {"filename": "front.jpg"}},
                "sources": ["ImageTriageEngine", "MediaPipe FaceLandmarker"],
            },
            "facial_analysis": {
                "face_shape": {"value": "oval", "status": "estimated"},
                "measurements": {"face_width": {"value": 0.42}},
            },
            "hair_analysis": {
                "observed": {"visual_coverage": {"value": 0.8}},
                "estimated": {},
                "not_determinable": {},
            },
            "recommendations": {
                "options": [
                    {
                        "key": "ivy_league",
                        "name": "Ivy League",
                        "compatibility_score": 0.91,
                        "top_cm": [4.0, 6.0],
                        "sides_mm": [6, 12],
                        "fade": "low taper",
                        "connection": "soft",
                        "direction": "side swept",
                        "finish": "natural",
                        "maintenance": "medium",
                        "avoid": "excessive height",
                        "reasons": ["Balances facial proportions"],
                        "risks": [],
                        "evidence": {},
                    },
                    {
                        "key": "crew_cut",
                        "name": "Crew Cut",
                        "compatibility_score": 0.82,
                        "top_cm": [2.0, 4.0],
                        "sides_mm": [3, 9],
                        "fade": "low fade",
                        "connection": "clean",
                        "direction": "forward",
                        "finish": "matte",
                        "maintenance": "low",
                        "avoid": "skin-high fade",
                        "reasons": ["Clean silhouette"],
                        "risks": [],
                        "evidence": {},
                    },
                ]
            },
            "limitations": ["measurements_are_normalized_not_physical"],
            "integrity": {
                "physical_measurements_claimed": False,
                "synthetic_simulation_presented_as_real": False,
            },
        }
    }

    payload = AIService._build_full_visagism_payload(
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
        pipeline_result,
        "https://example.test/card.png",
        "https://example.test/artifacts.json",
    )

    assert payload["processed_images"] == 10
    assert payload["recommendations"][0]["rank"] == 1
    assert payload["recommendations"][1]["rank"] == 2
    assert payload["top_recommendation"]["name"] == "Ivy League"
    assert payload["top_recommendation"]["rank"] == 1
    assert payload["card_url"].endswith("card.png")
    assert payload["manifest_url"].endswith("artifacts.json")
    assert payload["analysis_sources"] == [
        "ImageTriageEngine",
        "MediaPipe FaceLandmarker",
    ]
    assert payload["integrity"]["physical_measurements_claimed"] is False


def test_visagism_confidence_uses_primary_score_and_clamps():
    assert AIService._visagism_confidence(
        {"top_recommendation": {"compatibility_score": 0.91}}
    ) == 0.91
    assert AIService._visagism_confidence(
        {"top_recommendation": {"compatibility_score": 2.0}}
    ) == 1.0
    assert AIService._visagism_confidence(
        {"top_recommendation": {"compatibility_score": -1}}
    ) == 0.0
