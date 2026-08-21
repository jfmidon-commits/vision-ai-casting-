from app.ai.visagism.identity_lock import IdentityLockPolicy


def test_identity_lock_defaults_are_strict():
    policy = IdentityLockPolicy()
    constraints = policy.generation_constraints()
    assert constraints["base_image_immutable"] is True
    assert constraints["editable_regions"] == ["hair", "beard"]
    assert constraints["identity_weight_min"] >= 0.85
    assert constraints["identity_threshold"] >= 0.80


def test_blocks_simulation_when_identity_score_is_low():
    result = IdentityLockPolicy().decide_publication(
        original_photo="original.jpg",
        simulated_photo="simulation.jpg",
        identity_similarity=0.79,
        mask_valid=True,
        protected_regions_unchanged=True,
    )
    assert result["mode"] == "original"
    assert result["photo"] == "original.jpg"
    assert result["simulation_blocked"] is True


def test_blocks_when_identity_validation_is_missing():
    result = IdentityLockPolicy().decide_publication(
        original_photo="original.jpg",
        simulated_photo="simulation.jpg",
        mask_valid=True,
        protected_regions_unchanged=True,
    )
    assert result["mode"] == "original"


def test_blocks_when_mask_or_protected_regions_fail():
    policy = IdentityLockPolicy()
    assert policy.decide_publication(
        original_photo="original.jpg",
        simulated_photo="simulation.jpg",
        identity_similarity=0.95,
        mask_valid=False,
        protected_regions_unchanged=True,
    )["mode"] == "original"
    assert policy.decide_publication(
        original_photo="original.jpg",
        simulated_photo="simulation.jpg",
        identity_similarity=0.95,
        mask_valid=True,
        protected_regions_unchanged=False,
    )["mode"] == "original"


def test_allows_only_fully_validated_simulation():
    result = IdentityLockPolicy().decide_publication(
        original_photo="original.jpg",
        simulated_photo="simulation.jpg",
        identity_similarity=0.91,
        mask_valid=True,
        protected_regions_unchanged=True,
    )
    assert result["mode"] == "simulated"
    assert result["photo"] == "simulation.jpg"
    assert result["identity_verified"] is True
