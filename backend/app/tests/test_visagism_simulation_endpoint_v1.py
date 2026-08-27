from uuid import uuid4

from app.routers.analyses import _public_simulation_contract


ORIGINAL = "https://example.test/original.jpg"
GENERATED = "https://example.test/generated.jpg"


def test_public_contract_keeps_provider_absent_blocked_and_original_visible():
    analysis_id = uuid4()
    result = _public_simulation_contract(
        analysis_id=analysis_id,
        haircut_name="short textured crop",
        original_url=ORIGINAL,
        reference_count=3,
        reason="inpaint_provider_not_configured",
        provider_configured=False,
    )

    assert result["analysis_id"] == str(analysis_id)
    assert result["selected_haircut"] == "short textured crop"
    assert result["simulation_status"] == "blocked"
    assert result["reason"] == "inpaint_provider_not_configured"
    assert result["provider_configured"] is False
    assert result["ready_enabled"] is False
    assert result["card_media"]["personPhoto"] == ORIGINAL
    assert result["card_media"]["displayImage"] == ORIGINAL
    assert result["card_media"]["simulationApplied"] is False
    assert result["card_media"]["identityVerified"] is False


def test_public_contract_exposes_ready_only_with_explicit_approved_display_url():
    result = _public_simulation_contract(
        analysis_id=uuid4(),
        haircut_name="side part",
        original_url=ORIGINAL,
        display_url=GENERATED,
        simulation_status="ready",
        provider_configured=True,
        ready_enabled=True,
        reference_count=4,
        cached=True,
    )

    assert result["simulation_status"] == "ready"
    assert result["reason"] is None
    assert result["provider_configured"] is True
    assert result["ready_enabled"] is True
    assert result["cached"] is True
    assert result["card_media"]["personPhoto"] == ORIGINAL
    assert result["card_media"]["displayImage"] == GENERATED
    assert result["card_media"]["displayMode"] == "validated_hair_overlay"
    assert result["card_media"]["simulationApplied"] is True
    assert result["card_media"]["identityVerified"] is True


def test_public_contract_never_marks_ready_without_approved_display_url():
    result = _public_simulation_contract(
        analysis_id=uuid4(),
        haircut_name="side part",
        original_url=ORIGINAL,
        simulation_status="ready",
        provider_configured=True,
        ready_enabled=True,
        reference_count=4,
    )

    assert result["simulation_status"] != "ready"
    assert result["card_media"]["displayImage"] == ORIGINAL
    assert result["card_media"]["simulationApplied"] is False
    assert result["card_media"]["identityVerified"] is False


def test_public_contract_does_not_expose_internal_diagnostics_or_candidate():
    result = _public_simulation_contract(
        analysis_id=uuid4(),
        haircut_name="crew cut",
        original_url=ORIGINAL,
        reference_count=2,
        reason="invalid_reference_count",
        provider_configured=True,
    )

    assert result["reason"] == "invalid_reference_count"
    assert "diagnostics" not in result
    assert "candidate" not in result
    assert "identity_scores" not in result
    assert result["card_media"]["displayImage"] == ORIGINAL
