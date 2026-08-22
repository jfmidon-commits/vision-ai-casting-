from uuid import uuid4

from app.ai.image_triage.engine import TriageCategory, TriageResult
from app.routers.photos import _public_triage_contract


def test_public_triage_contract_accepts_selected_grounded_category():
    photo_id = uuid4()
    result = TriageResult(
        filename="front.jpg",
        category=TriageCategory.FRONTAL,
        confidence=0.91,
        rejection_reasons=[],
        selected=True,
    )

    payload = _public_triage_contract(photo_id, result)

    assert payload["photo_id"] == str(photo_id)
    assert payload["accepted"] is True
    assert payload["category"] == "frontal"
    assert payload["selected"] is True
    assert payload["confidence"] == 0.91
    assert payload["rejection_reasons"] == []


def test_public_triage_contract_rejects_unknown_even_when_selected():
    result = TriageResult(
        filename="unknown.jpg",
        category=TriageCategory.UNKNOWN,
        confidence=0.4,
        rejection_reasons=["angle_uncertain"],
        selected=True,
    )

    payload = _public_triage_contract(uuid4(), result)

    assert payload["accepted"] is False
    assert payload["category"] == "unknown"
    assert payload["rejection_reasons"] == ["angle_uncertain"]


def test_public_triage_contract_rejects_explicit_rejected_category():
    result = TriageResult(
        filename="bad.jpg",
        category=TriageCategory.REJECTED,
        confidence=0.2,
        rejection_reasons=["no_face_detected"],
        selected=False,
    )

    payload = _public_triage_contract(uuid4(), result)

    assert payload["accepted"] is False
    assert payload["selected"] is False
    assert payload["category"] == "rejected"


def test_public_triage_contract_fails_closed_without_engine_result():
    payload = _public_triage_contract(uuid4(), reason="triage_error")

    assert payload["accepted"] is False
    assert payload["selected"] is False
    assert payload["category"] == "rejected"
    assert payload["confidence"] == 0.0
    assert payload["rejection_reasons"] == ["triage_error"]


def test_public_triage_contract_does_not_expose_raw_scores_or_metadata():
    result = TriageResult(
        filename="front.jpg",
        category=TriageCategory.FRONTAL_CLOSE,
        confidence=0.88,
        scores={"yaw": 0.12, "face": 0.99},
        metadata={"landmarks": [1, 2, 3]},
        selected=True,
    )

    payload = _public_triage_contract(uuid4(), result)

    assert "scores" not in payload
    assert "metadata" not in payload
    assert "landmarks" not in payload
