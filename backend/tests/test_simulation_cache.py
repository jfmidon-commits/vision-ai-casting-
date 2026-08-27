from app.ai.visagism.simulation_cache import (
    CACHE_FIELD,
    cache_key,
    find_ready,
    object_key,
    ready_for_source,
    with_ready_entry,
)


def test_cache_key_is_stable_for_same_generation_identity():
    first = cache_key(
        haircut_name="Quiff texturizado",
        source_photo_id="photo-1",
        provider="fal",
        model="model-v1",
    )
    second = cache_key(
        haircut_name="Quiff texturizado",
        source_photo_id="photo-1",
        provider="fal",
        model="model-v1",
    )
    other = cache_key(
        haircut_name="Side Part",
        source_photo_id="photo-1",
        provider="fal",
        model="model-v1",
    )

    assert first == second
    assert first != other


def test_ready_entry_round_trips_without_image_bytes_in_jsonb():
    key = "abc123"
    visagism = with_ready_entry(
        {"recommended_hairstyles": ["Quiff texturizado"]},
        key=key,
        haircut_name="Quiff texturizado",
        source_photo_id="photo-1",
        provider="fal",
        model="model-v1",
        stored_object_key="visagism-simulations/t/a/abc123.png",
        identity_score_min=0.91,
        mask_kind="hair-v2",
    )

    cached = find_ready(
        visagism,
        haircut_name="Quiff texturizado",
        source_photo_id="photo-1",
        provider="fal",
        model="model-v1",
    )

    assert cached is not None
    assert cached["object_key"].endswith("abc123.png")
    assert cached["identity_score_min"] == 0.91
    assert "image" not in cached
    assert "base64" not in str(visagism[CACHE_FIELD]).lower()


def test_cache_is_scoped_to_source_photo_and_generation_version():
    visagism = with_ready_entry(
        {},
        key="one",
        haircut_name="Quiff",
        source_photo_id="photo-1",
        provider="fal",
        model="v1",
        stored_object_key="one.png",
        identity_score_min=0.9,
    )

    assert find_ready(
        visagism,
        haircut_name="Quiff",
        source_photo_id="photo-2",
    ) is None
    assert find_ready(
        visagism,
        haircut_name="Quiff",
        source_photo_id="photo-1",
        provider="fal",
        model="v2",
    ) is None


def test_ready_for_source_returns_only_matching_ready_simulations():
    visagism = with_ready_entry(
        {},
        key="one",
        haircut_name="Quiff",
        source_photo_id="photo-1",
        provider="fal",
        model="v1",
        stored_object_key="one.png",
        identity_score_min=0.9,
    )
    visagism = with_ready_entry(
        visagism,
        key="two",
        haircut_name="Side Part",
        source_photo_id="photo-2",
        provider="fal",
        model="v1",
        stored_object_key="two.png",
        identity_score_min=0.91,
    )

    items = list(ready_for_source(visagism, source_photo_id="photo-1"))
    assert len(items) == 1
    assert items[0]["haircut_name"] == "Quiff"


def test_s3_object_key_is_tenant_and_analysis_scoped():
    key = object_key(tenant_id="tenant-1", analysis_id="analysis-1", key="hash")
    assert key == "visagism-simulations/tenant-1/analysis-1/hash.png"
