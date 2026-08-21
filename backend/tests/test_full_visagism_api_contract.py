from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import FullVisagismAnalysis, FullVisagismRequest
from app.services.ai_service import AIService


def test_full_visagism_request_requires_at_least_five_ranked_cuts():
    photoshoot_id = uuid4()
    request = FullVisagismRequest(photoshoot_id=photoshoot_id, cut_limit=5)
    assert request.cut_limit == 5

    with pytest.raises(ValidationError):
        FullVisagismRequest(photoshoot_id=photoshoot_id, cut_limit=4)


def test_photo_extension_prefers_supported_url_suffix_then_content_type():
    assert AIService._photo_extension("https://example.test/photo.webp", None) == ".webp"
    assert AIService._photo_extension("https://example.test/object", "image/png") == ".png"
    assert AIService._photo_extension("https://example.test/object", None) == ".jpg"


def test_build_full_visagism_payload_adds_ranks_and_public_artifacts():
    analysis_id = str(uuid4())
    photoshoot_id = str(uuid4())
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
            "hair_analysis": {"observed": {}, "estimated": {}, "not_determinable": {}},
            "recommendations": {
                "options": [
                    {
                        "key": "ivy_league",
                        "name": "Ivy League",
                        "compatibility_score": 0.95,
                        "top_cm": [4.0, 6.0],
                        "sides_mm": [6, 16],
                        "fade": "low taper",
                        "connection": "graduated",
                        "direction": "side-swept",
                        "finish": "matte",
                        "maintenance": "3-4 weeks",
                        "avoid": "high temple fade",
                        "reasons": ["face geometry"],
                        "risks": [],
                        "evidence": {"face_shape": "oval"},
                    }
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
        analysis_id,
        photoshoot_id,
        pipeline_result,
        "https://cdn.test/card.png",
        "https://cdn.test/artifacts.json",
    )

    assert payload["recommendations"][0]["rank"] == 1
    assert payload["top_recommendation"]["name"] == "Ivy League"
    assert payload["card_url"].endswith("card.png")
    assert payload["manifest_url"].endswith("artifacts.json")

    validated = FullVisagismAnalysis.model_validate(payload)
    assert validated.processed_images == 10
    assert validated.top_recommendation is not None
    assert validated.top_recommendation.rank == 1
