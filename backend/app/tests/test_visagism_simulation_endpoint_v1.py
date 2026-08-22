from uuid import uuid4

from app.routers.analyses import _public_simulation_contract


def test_public_contract_keeps_provider_absent_blocked_and_original_visible():
    analysis_id = uuid4()
    result = _public_simulation_contract(
        analysis_id=analysis_id,
        haircut_name="short textured crop",
        original_url="https://example.test/original.jpg",
        reference_count=3,
        service_result={
            "simulation_status": "blocked",
            "reason": "inpaint_provider_not_configured",
        },
    )

    assert result["analysis_id"] == str(analysis_id)
    assert result["selected_haircut"] == "short textured crop"
    assert result["simulation_status"] == "blocked"
    assert result["reason"] == "inpaint_provider_not_configured"
    assert result["provider_configured"] is False
    assert result["ready_enabled"] is False
    assert result["card_media"]["personPhoto"] == "https://example.test/original.jpg"
    assert result["card_media"]["displayImage"] == "https://example.test/original.jpg"
    assert result["card_media"]["simulationApplied"] is False
    assert result["card_media"]["identityVerified"] is False


def test_public_contract_collapses_unexpected_ready_to_blocked():
    result = _public_simulation_contract(
        analysis_id=uuid4(),
        haircut_name="side part",
        original_url="https://example.test/original.jpg",
        reference_count=4,
        service_result={
            "simulation_status": "ready",
            "reason": None,
            "card_media": {
                "displayImage": "https://example.test/generated.jpg",
                "simulationApplied": True,
                "identityVerified": True,
            },
        },
    )

    assert result["simulation_status"] == "blocked"
    assert result["reason"] == "simulation_ready_not_enabled"
    assert result["card_media"]["displayImage"] == "https://example.test/original.jpg"
    assert result["card_media"]["simulationApplied"] is False
    assert result["card_media"]["identityVerified"] is False


def test_public_contract_does_not_expose_internal_diagnostics_or_candidate():
    result = _public_simulation_contract(
        analysis_id=uuid4(),
        haircut_name="crew cut",
        original_url="https://example.test/original.jpg",
        reference_count=2,
        service_result={
            "simulation_status": "blocked",
            "reason": "invalid_reference_count",
            "diagnostics": {
                "mask": "internal-mask",
                "identity_scores": [0.2, 0.3],
            },
            "candidate": "https://example.test/unapproved.jpg",
        },
    )

    assert result["reason"] == "invalid_reference_count"
    assert "diagnostics" not in result
    assert "candidate" not in result
    assert result["card_media"]["displayImage"] == "https://example.test/original.jpg"
