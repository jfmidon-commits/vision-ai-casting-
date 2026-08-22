from app.ai.visagism.identity_lock import IdentityLockPolicy


def test_identity_lock_defaults_are_strict():
    constraints = IdentityLockPolicy().generation_constraints()
    assert constraints["never_generate_person_from_scratch"] is True
    assert constraints["base_image_immutable"] is True
    assert constraints["editable_regions"] == ["hair", "beard"]
    assert constraints["mask_scope"] == "hair_and_beard_only"
    assert constraints["identity_weight_min"] >= 0.85
    assert constraints["identity_threshold"] >= 0.80
    assert constraints["all_reference_validations_must_pass"] is True
    assert constraints["publish_similar_face_forbidden"] is True
    assert "body" in constraints["forbidden_regions"]


def test_explicit_fallback_when_any_identity_score_is_low():
    result = IdentityLockPolicy().decide_publication(
        original_photo="original.jpg",
        simulated_photo="simulation.jpg",
        identity_scores=[0.94, 0.91, 0.79],
        mask_valid=True,
        protected_regions_unchanged=True,
        body_unchanged=True,
    )
    assert result["image"] == "original.jpg"
    assert result["mode"] == "original_plus_spec"
    assert result["simulationApplied"] is False
    assert result["reason"] == "identity_lock_failed"
    assert result["layers"]["base"] == "original.jpg"
    assert result["layers"]["overlay"] is None


def test_blocks_when_identity_validation_is_missing():
    result = IdentityLockPolicy().decide_publication(
        original_photo="original.jpg",
        simulated_photo="simulation.jpg",
        mask_valid=True,
        protected_regions_unchanged=True,
        body_unchanged=True,
    )
    assert result["mode"] == "original_plus_spec"
    assert result["simulationBlocked"] is True


def test_requires_three_to_five_real_reference_validations():
    policy = IdentityLockPolicy()
    for scores in ([0.95, 0.96], [0.95] * 6):
        result = policy.decide_publication(
            original_photo="original.jpg",
            simulated_photo="simulation.jpg",
            identity_scores=scores,
            mask_valid=True,
            protected_regions_unchanged=True,
            body_unchanged=True,
        )
        assert result["mode"] == "original_plus_spec"


def test_blocks_when_mask_face_or_body_protection_fails():
    policy = IdentityLockPolicy()
    scores = [0.95, 0.94, 0.93]
    cases = [
        dict(mask_valid=False, protected_regions_unchanged=True, body_unchanged=True),
        dict(mask_valid=True, protected_regions_unchanged=False, body_unchanged=True),
        dict(mask_valid=True, protected_regions_unchanged=True, body_unchanged=False),
    ]
    for case in cases:
        result = policy.decide_publication(
            original_photo="original.jpg",
            simulated_photo="simulation.jpg",
            identity_scores=scores,
            **case,
        )
        assert result["mode"] == "original_plus_spec"
        assert result["image"] == "original.jpg"


def test_allows_only_hair_beard_overlay_after_every_validation_passes():
    result = IdentityLockPolicy().decide_publication(
        original_photo="original.jpg",
        simulated_photo="hair-beard-overlay.png",
        identity_scores=[0.91, 0.93, 0.90, 0.92, 0.94],
        mask_valid=True,
        protected_regions_unchanged=True,
        body_unchanged=True,
    )
    assert result["mode"] == "hair_beard_overlay"
    assert result["simulationApplied"] is True
    assert result["identityVerified"] is True
    assert result["layers"]["base"] == "original.jpg"
    assert result["layers"]["overlay"] == "hair-beard-overlay.png"
    assert result["audit"]["simulation_allowed"] is True
